"""
Generic permission gate — the foundation layer.
Sits OUTSIDE the model. The model cannot see, edit, or route around this.

Four gates, evaluated in order (fail-closed):
  1a. Hard deny — write targets (BUILTIN_PROTECTED_PATHS, plus any additions in
      deny-list.json `protected_paths`). Enforces S2.4: the agent may not edit
      the mechanism or policy that constrains it. Runs first because it is the
      only gate with a built-in floor, so it still returns a specific verdict
      when the policy file is unreadable.
  1b. Hard deny — command patterns (deny-list.json `patterns`).
  2.  Phase gate (feature_list.json says which phase is active; mcp-allowlist.json
      `signed_off_phases` says which phases are human-signed-off, and that is what
      unlocks a `gated_until` tool — never the agent-writable worklog).
  3.  Egress control (default-deny outbound to unlisted hosts), for a destination
      written as a shell command OR carried in a structured field.

An unreadable or unparseable policy file raises PolicyError, which CLI mode turns
into exit 2. That is load-bearing, not defensive habit: Claude Code blocks only on
exit 2, and treats every other non-zero as a non-blocking hook error that lets the
tool RUN. A gate that crashed on a corrupt JSON file would therefore fail OPEN.

To customise: edit deny-list.json and governance/mcp-allowlist.json.
Do NOT modify this file per project — it's the mechanism, not the policy.
"""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

# Layout: <project_root>/governance/permission.py
#   deny-list.json + mcp-allowlist.json are siblings (in governance/)
#   feature_list.json lives in <project_root>/Harness-Best-Practice/
PROJECT_ROOT = Path(__file__).parent.parent
DENY_LIST_PATH = Path(__file__).parent / "deny-list.json"
ALLOWLIST_PATH = Path(__file__).parent / "mcp-allowlist.json"
FEATURE_LIST_PATH = PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json"


def _probe_case_insensitive() -> bool:
    try:
        this = Path(__file__)
        swapped = this.with_name(this.name.upper())
        return swapped != this and swapped.exists()
    except OSError:
        return False


_FS_CASE_INSENSITIVE = _probe_case_insensitive()


class PolicyError(RuntimeError):
    """Policy exists but cannot be trusted -> no verdict -> caller must DENY."""


def _same_file(a: Path, b: Path) -> bool:
    """Do two paths name the same file? Compares IDENTITY, not spelling.

    Three cases defeat a pure string comparison, and each is a real bypass:
      - a symlink is a second name for the same file (handled by `_resolve`);
      - a HARD link is the same inode under another name, with nothing to resolve
        through — only a stat comparison sees it;
      - on a case-insensitive filesystem, GOVERNANCE/PERMISSION.PY *is* permission.py.

    `os.path.samefile` compares (st_dev, st_ino), which covers the first two. It
    requires both paths to exist, so the string comparison remains the fallback for
    a target that a Write is about to create.
    """
    if a == b:
        return True
    try:
        if os.path.samefile(a, b):
            return True
    except OSError:
        pass  # a target being created does not exist yet; fall through
    return _FS_CASE_INSENSITIVE and str(a).casefold() == str(b).casefold()


def _load_json(path, *, required=False):
    try:
        text = path.read_text()
    except FileNotFoundError:
        if required:
            raise PolicyError(f"policy file missing: {path.name} (fail closed)")
        return {}
    except OSError as exc:
        raise PolicyError(f"policy file unreadable: {path.name} ({exc.strerror})")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raise PolicyError(f"policy file is not valid JSON: {path.name} (fail closed)")
    if not isinstance(data, dict):
        raise PolicyError(f"policy file is not a JSON object: {path.name}")
    return data


def _shell_lines(command: str) -> list[str]:
    r"""Split a shell command string into individual COMMAND lines.

    A raw newline separates two commands exactly as `;` and `|` do. The negated
    classes in deny-list.json's regex patterns exclude `|;&` but NOT `\n`, so one
    search over the whole blob lets a token from one command compose with a token
    from another into a match neither command earns alone -- e.g. `sed` on line 1
    plus `-i` and a protected path on line 2, where line 1 is a read-only `sed -n`.

    Two cases where a newline does NOT end a command. Both must survive, or the
    fix trades a false positive for a bypass:
      - line continuation (backslash then newline) -- unfolded to a space first;
      - a newline inside quotes -- tracked, so `sed -i '<newline>s/x/y/' <path>`
        stays one line and stays denied.
    An unterminated quote yields a single unsplit line: fail closed.
    """
    unfolded = command.replace("\\\n", " ")
    lines: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in unfolded:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == "\n":
            lines.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    lines.append("".join(buf))
    return [ln for ln in lines if ln.strip()] or [unfolded]


def check_deny_list(command: str) -> str | None:
    """Gate 1b: hard deny on command patterns. Reason if denied, None if allowed.

    Raises PolicyError if deny-list.json is missing or unparseable: unlike Gate 1a
    there is no built-in floor for `patterns`, so an absent policy would mean
    "nothing is denied". The caller converts that to a denial.

    Each entry in `patterns` is either:
      - a string  → substring match (backward-compatible default), or
      - an object  {"pattern": "...", "mode": "substring"|"word"|"regex"}
          * "word"  → matches the literal only on word boundaries, so "curl" does not
                       fire on "curly"; the fix for the naive-substring problem.
          * "regex" → full regex match, applied PER SHELL COMMAND (see
                       _shell_lines). substring and word stay whole-string, which
                       can only deny more, never less, so no bypass is opened.
    A malformed regex falls back to substring match rather than crashing the gate.
    """
    data = _load_json(DENY_LIST_PATH, required=True)
    for entry in data.get("patterns", []):
        if isinstance(entry, dict):
            pat = entry.get("pattern", "")
            mode = entry.get("mode", "substring")
        else:
            pat, mode = entry, "substring"
        if not pat:
            continue
        try:
            if mode == "word":
                hit = re.search(rf"\b{re.escape(pat)}\b", command) is not None
            elif mode == "regex":
                hit = any(re.search(pat, ln) for ln in _shell_lines(command))
            else:
                hit = pat in command
        except re.error:
            hit = pat in command  # bad regex → safe fallback, never crash the gate
        if hit:
            return f"deny-list hit: '{pat}'"
    return None


# Write-target fields used by Claude Code's file-editing tools. A Write/Edit call
# carries no "command", so the command-pattern loop above cannot see it — these are
# where the *target* of a write lives.
WRITE_TARGET_FIELDS = ("file_path", "notebook_path", "path")

# Enforced even if deny-list.json omits `protected_paths` or is missing entirely.
# S2.4 is a mechanism guarantee, so it must not be silently removable by editing
# policy — that would be the very bypass this gate exists to prevent.
BUILTIN_PROTECTED_PATHS = (
    "governance/permission.py",
    "governance/deny-list.json",
    "governance/mcp-allowlist.json",
    ".claude/settings.json",
    "Security-kit/secret_scan.py",
    "Security-kit/content_trust.py",
    # The two pre-model screens. They are hook ENTRY POINTS, not library code, so
    # unlike content_trust.py (their shared marker list, already above) each is
    # independently sufficient to disable a control: blank result_screen.py and it
    # exits 0 with empty stdout, which the runtime reads as "no replacement" and
    # forwards the original tool output to the model. Measured 2026-08-17 — before
    # these two lines, `Edit Security-kit/result_screen.py` was ALLOW.
    "Security-kit/prompt_screen.py",
    "Security-kit/result_screen.py",
    # The runtime pair, added 2026-08-22 with the mechanism itself. The dispatcher is
    # the single chokepoint that holds a deployed app's only call to the permission
    # gate, so editing it disables gate ② for the whole application in one line —
    # strictly more damaging than editing any hook adapter, which only affects a
    # developer's IDE session. `runtime_screen.py` is its ①/④ counterpart.
    # Measured on dev_fengmin 2026-08-21: without this line
    # `Edit governance/runtime_dispatcher.py` returned exit 0 (ALLOW).
    "governance/runtime_dispatcher.py",
    "Security-kit/runtime_screen.py",
    # The runtime-mvp semantic profile, added with the 2026-09-01 claims batch. Same
    # reasoning as the runtime pair above: each is an in-process enforcement module for
    # a DEPLOYED application, so one edit disables a control for the whole app, and the
    # app has no hook layer to catch it. The signed classifier lock is here too — it is
    # the artifact a human approved by digest, and rewriting it swaps the model silently.
    # NOT listed, deliberately: runtime/attack_driver.py and runtime/semantic-model.
    # schema.json — evaluation tooling and inert documentation, matching how
    # Security-kit/eval/ is left unprotected. The shell patterns use a
    # Security-kit/runtime/ PREFIX, so those two still get shell coverage.
    "Security-kit/runtime/__init__.py",
    "Security-kit/runtime/adapters.py",
    "Security-kit/runtime/audit.py",
    "Security-kit/runtime/classifier.py",
    "Security-kit/runtime/contracts.py",
    "Security-kit/runtime/guarded.py",
    "Security-kit/runtime/host.py",
    "Security-kit/runtime/ingress.py",
    "Security-kit/runtime/normalization.py",
    "Security-kit/runtime/output.py",
    "Security-kit/runtime/review.py",
    "Security-kit/runtime/review_cli.py",
    "Security-kit/runtime/rules.py",
    "Security-kit/runtime/session.py",
    "Security-kit/runtime/startup.py",
    "Security-kit/runtime/semantic-model.lock.json",
    "Harness-Best-Practice/observability/audit_hook.py",
    "Harness-Best-Practice/observability/audit.log",
)


def _resolve(path_str: str) -> Path:
    """Reduce a path to one comparable absolute form.

    Two steps, because each catches a different evasion. `os.path.normpath`
    collapses "../", "./" and "//" as a pure string operation, so
    "claims/../governance/permission.py" cannot smuggle a write past the check.
    `Path.resolve()` then follows symlinks, so a link pointing at the mechanism is
    recognised as the mechanism — normpath deliberately does not do this.

    `resolve()` tolerates a non-existent target (we are judging a file that a Write
    may be about to create); on OSError we keep the normalized form rather than
    give up, so the gate degrades to string comparison instead of abstaining.
    """
    raw = os.path.expanduser(path_str.strip())
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    normalised = Path(os.path.normpath(str(p)))
    try:
        return normalised.resolve()
    except OSError:
        return normalised


def check_protected_paths(tool_input: dict) -> str | None:
    """Gate 1a: block writes that target the harness's own mechanism or policy.

    Implements S2.4. `check_deny_list` only inspects shell command strings, so a
    Write/Edit/MultiEdit/NotebookEdit call — whose payload carries `file_path`
    rather than `command` — was previously invisible to every gate. That let the
    agent rewrite `permission.py` or `deny-list.json`, i.e. edit its own
    constraints. This closes that path.

    Matching is on the *identity* of the target, not its spelling: `_resolve`
    collapses `../`, `./` and absolute forms and follows symlinks, and `_same_file`
    additionally treats case variants as equal on a case-insensitive filesystem
    (macOS/Windows), where `GOVERNANCE/PERMISSION.PY` really is `permission.py`.
    A pure string comparison misses both of those.

    Never raises: the built-in list is enforced even when `deny-list.json` is
    missing, so this gate can always answer. That is why it runs before Gate 1b —
    a deleted policy file must not cost S2.4 its specific verdict. Nothing is
    swallowed, because Gate 1b reads the same file and denies on it.

    Returns a reason string if denied, None if allowed.
    """
    if not isinstance(tool_input, dict):
        return None

    targets = [tool_input.get(f) for f in WRITE_TARGET_FIELDS]
    targets = [t for t in targets if isinstance(t, str) and t.strip()]
    if not targets:
        return None

    data = _load_json(DENY_LIST_PATH)
    configured = data.get("protected_paths", [])
    if not isinstance(configured, list):
        configured = []
    # Union, never override: policy may ADD protected paths but cannot remove the
    # built-ins. Mechanism guarantees are not up for negotiation by policy.
    patterns = list(BUILTIN_PROTECTED_PATHS) + [
        p for p in configured if isinstance(p, str) and p.strip()
    ]

    for target in targets:
        resolved = _resolve(target)
        for rel in patterns:
            if _same_file(resolved, _resolve(rel)):
                return f"protected path (S2.4): refusing to write '{rel}'"
    return None


def check_phase_gate(tool_name: str) -> str | None:
    """Gate 2: is this tool allowed in the current active phase?

    Two questions, deliberately answered from two DIFFERENT files:

        "which phase is active?"          -> feature_list.json  `status`
        "is a gated tool unlocked?"       -> mcp-allowlist.json `signed_off_phases`

    The split is the whole point. feature_list.json is the agent's own worklog and
    must stay editable during development — that is where it records progress. A
    tool unlock is a privilege decision, so it lives in mcp-allowlist.json, which is
    a protected path (`BUILTIN_PROTECTED_PATHS`) and therefore human-only.

    Before the split, the unlock was read from feature_list.json `status`, so an
    agent could grant itself a gated tool by editing its own worklog. Measured
    2026-08-17 on the shipped tree — three distinct edits reached ALLOW:

        phase-01 -> "passing" and phase-02 -> "active"   ALLOW  (ordinary-looking)
        every phase -> "passing"                         ALLOW  (steady-state path)
        delete the phase-01 entry, phase-02 -> "active"  ALLOW  (id match found none)

    The third is worth its own line: the old loop denied only on finding a matching
    id with a non-passing status, so a MISSING prerequisite was indistinguishable
    from a satisfied one. `signed_off_phases` inverts that — a phase absent from the
    list is not signed off, so all three now DENY, and the default (key absent, or
    absent value) is an empty list. Fails closed.
    """
    features = _load_json(FEATURE_LIST_PATH).get("features", [])
    active = [f for f in features if f.get("status") == "active"]
    if not active:
        # No active phase. Distinguish two cases:
        #   (a) STEADY-STATE — every phase is "passing". Feature work is complete
        #       and human-signed-off; the harness should keep operating, not brick.
        #       Deny-list and egress remain enforced by their own gates, and a
        #       phase-gated tool is now decided by `signed_off_phases` below, so
        #       falling through here grants nothing that was not human-signed.
        #       (It used to: "all passing" reached a gate that read the same
        #       statuses, which is why this carve-out was an escalation path.)
        #   (b) UNDEFINED — some phase is not-started/other. State is genuinely
        #       ambiguous; fail closed.
        if features and all(f.get("status") == "passing" for f in features):
            pass  # steady-state; continue to allowlist/gate check below
        else:
            return "no active phase — cannot determine tool permissions"

    allowlist = _load_json(ALLOWLIST_PATH)
    for tool in allowlist.get("tools", []):
        if tool["name"] == tool_name:
            if "gated_until" in tool:
                required_phase = tool["gated_until"]
                signed_off = allowlist.get("signed_off_phases", [])
                # isinstance is load-bearing, not defensive habit: `in` over a bare
                # string is a SUBSTRING test, so a human who writes
                # "signed_off_phases": "phase-01" would unlock "phase-0" too.
                if not isinstance(signed_off, list) or required_phase not in signed_off:
                    return f"{tool_name} gated until {required_phase} is signed off"
            return None  # tool found and not gated (or gate satisfied)
    return f"{tool_name} not in allowlist"


# --- Gate 3: egress ---------------------------------------------------------------
#
# A destination reaches the agent in two shapes, and until 2026-08-22 this gate saw
# only the first:
#   - a shell command string   -- `curl https://x`         (Bash)
#   - a structured field       -- {"url": "https://x"}     (WebFetch, MCP tools, and
#     every in-process tool a deployed app registers through RuntimeDispatcher)
# The second was invisible for two independent reasons: `check_egress` read only
# `command`, and the caller ran it only when `tool == "bash"`. Both are fixed here.

# Field names that carry an outbound destination. Matched case-insensitively.
EGRESS_TARGET_FIELDS = frozenset({
    "url", "uri", "endpoint", "base_url", "target_url",
    "webhook_url", "callback_url", "host", "hostname",
})

# Ceiling on how deep a payload is walked looking for those fields. Hitting it is
# reported, never shrugged off — see `_collect_egress_targets`.
_MAX_EGRESS_SCAN_DEPTH = 8

NETWORK_TOKENS = ("curl ", "wget ", "nc ", "ssh ", "nmap ")
_URL_IN_TEXT = re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s'\"`;|&<>]+")


def _normalise_host(value) -> str | None:
    """Reduce a destination to a bare lowercase hostname, or None if it has none.

    `urlparse` does the work so that every shape a destination is written in collapses
    to one comparable string: `https://api.github.com/x?y`, `api.github.com:8443`,
    `user@api.github.com` and a bare `api.github.com` all yield `api.github.com`. The
    trailing dot goes because `example.com.` is the same host to a resolver and a
    different string to `==`.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        parsed = urlparse(raw if "://" in raw else f"//{raw}")
        host = parsed.hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.lower().rstrip(".")


def _host_allowed(host: str, allowed_hosts) -> bool:
    """Is `host` on the allowlist? EXACT match, unless the entry opts into a wildcard.

        "api.github.com"  -> api.github.com and nothing else
        "*.github.com"    -> github.com and any subdomain of it

    Exact-by-default is the deliberate half. Implicit suffix matching — reading one
    entry for `api.github.com` as also permitting `anything.api.github.com` — looks
    harmless until the allowlist names a domain where third parties can create names:
    a single entry for `s3.amazonaws.com` would then permit
    `attacker-bucket.s3.amazonaws.com`, an exfil destination anyone can register. So a
    subdomain has to be asked for in the policy file, where a human can see it.
    """
    for configured in allowed_hosts:
        if not isinstance(configured, str) or not configured.strip():
            continue
        entry = configured.strip()
        wildcard = entry.startswith("*.")
        allowed = _normalise_host(entry[2:] if wildcard else entry)
        if not allowed:
            continue
        if host == allowed or (wildcard and host.endswith(f".{allowed}")):
            return True
    return False


def _collect_egress_targets(node, out: list, depth: int = 0) -> bool:
    """Append every destination string in a tool payload. Returns True if the walk hit
    the depth ceiling — i.e. the answer is INCOMPLETE, not empty.

    That return value is the whole reason this is not a generator. A bare `return` at
    the ceiling makes an unverifiable payload indistinguishable from a clean one, and
    the caller reads "no destinations" as ALLOW. Nesting depth is attacker-controlled,
    so that is a one-line bypass: bury the URL nine levels down and the gate waves it
    through. Measured on dev_fengmin 2026-08-21, where the generator form did exactly
    that — same destination nested 9 deep ALLOW, flat DENY.
    """
    if depth > _MAX_EGRESS_SCAN_DEPTH:
        return True
    truncated = False
    if isinstance(node, dict):
        for key, val in node.items():
            is_target = isinstance(key, str) and key.lower() in EGRESS_TARGET_FIELDS
            if is_target and isinstance(val, str):
                out.append(val)
            elif is_target and isinstance(val, (list, tuple)):
                out.extend(v for v in val if isinstance(v, str))
            elif isinstance(val, (dict, list, tuple)):
                truncated = _collect_egress_targets(val, out, depth + 1) or truncated
    elif isinstance(node, (list, tuple)):
        for val in node:
            truncated = _collect_egress_targets(val, out, depth + 1) or truncated
    return truncated


def _reject_lookalike_hosts(command: str, allowed_hosts) -> str | None:
    """Deny a command that only LOOKS like it targets an allowed host.

    The base allow at the end of `check_egress` is a substring test, and that is what
    makes `curl https://localhost.evil.com` read as permitted: the allowed name really
    is in the string, just not as the host. Measured on both main and dev_fengmin
    2026-08-21 — `curl https://api.github.com.evil.com` was ALLOW.

    Rather than delete the substring test — every real-world command relies on its
    tolerance for flags, quoting and pipes — this examines only the words that contain
    an allowed name, and requires each one to actually RESOLVE to an allowed host. A
    word with no allowed name in it is never looked at, so an ordinary `-o report.txt`
    cannot be mistaken for a destination. The residue is a filename that embeds an
    allowed host name (`-o report.localhost.txt`), which denies; fail-closed and rare.
    """
    names = [
        n for n in (
            _normalise_host(h[2:] if h.strip().startswith("*.") else h)
            for h in allowed_hosts if isinstance(h, str) and h.strip()
        ) if n
    ]
    if not names:
        return None
    for line in _shell_lines(command):
        # `=` is split as a separator so `--url=https://localhost.evil.com` is judged
        # on its destination rather than on the whole flag.
        for word in line.replace("=", " ").split():
            token = word.strip("'\"`,()")
            if not any(name in token.lower() for name in names):
                continue
            host = _normalise_host(token)
            if host is None or not _host_allowed(host, allowed_hosts):
                return (f"default-deny egress: '{token}' contains an allowed host name "
                        f"but does not resolve to an allowed host")
    return None


def check_egress(command: str, tool_input: dict | None = None) -> str | None:
    """Gate 3: default-deny outbound network access. Reason if denied, None if allowed."""
    allowed_hosts = _load_json(ALLOWLIST_PATH).get("egress_hosts", [])
    if not isinstance(allowed_hosts, list):
        allowed_hosts = []  # a malformed value denies everything, it does not allow

    # Path A — structured destination fields, for every tool including non-bash ones.
    targets: list = []
    if _collect_egress_targets(tool_input or {}, targets):
        return (f"default-deny egress: tool input nests deeper than "
                f"{_MAX_EGRESS_SCAN_DEPTH} levels — destination not verifiable")
    for target in targets:
        host = _normalise_host(target)
        if host is None:
            return "default-deny egress: destination field carries no readable host"
        if not _host_allowed(host, allowed_hosts):
            return f"default-deny egress: host '{host}' not on egress_hosts"

    # Path B — a destination written into a shell command string.
    if not any(tok in command for tok in NETWORK_TOKENS):
        return None
    for match in _URL_IN_TEXT.finditer(command):
        host = _normalise_host(match.group(0))
        if host and not _host_allowed(host, allowed_hosts):
            return f"default-deny egress: host '{host}' not on egress_hosts"
    reason = _reject_lookalike_hosts(command, allowed_hosts)
    if reason:
        return reason
    if any(host in command for host in allowed_hosts if isinstance(host, str)):
        return None
    return "default-deny egress: target host not on allowlist"


def make_permission_check(auto_deny_on_ask=True):
    """Returns a permission_check(block) -> (allowed: bool, reason: str)."""
    def permission_check(block):
        tool_input = block.input if isinstance(block.input, dict) else {}
        cmd = tool_input.get("command", "")
        tool = block.name

        # Gate 1a: hard deny — write targets (S2.4). Runs FIRST and for every
        # tool: a write can arrive as Write/Edit/MultiEdit/NotebookEdit or as an
        # MCP tool carrying a path, and none of those carry a "command".
        # Ordered before the command patterns deliberately: this gate has a
        # built-in floor (BUILTIN_PROTECTED_PATHS) and so still answers when the
        # policy file is missing, whereas check_deny_list must raise. Keeping it
        # first means a deleted policy file cannot cost us S2.4's specific verdict.
        reason = check_protected_paths(tool_input)
        if reason:
            return False, reason

        # Gate 1b: hard deny — command patterns (raises if policy unreadable)
        reason = check_deny_list(cmd)
        if reason:
            return False, reason

        # Gate 2: phase gate
        reason = check_phase_gate(tool)
        if reason:
            return False, reason

        # Gate 3: egress. Runs for EVERY tool, not just bash. The old `if tool ==
        # "bash"` guard was written when a shell command was the only way to reach the
        # network; it meant a WebFetch, an MCP tool or an in-process tool carrying
        # {"url": ...} was never egress-checked at all. `check_egress` returns None
        # for a payload with no destination in it, so the guard bought nothing.
        reason = check_egress(cmd, tool_input)
        if reason:
            return False, reason

        return True, ""
    return permission_check


# --- CLI mode (for .claude/settings.json hooks) ---
#
# Claude Code delivers the tool call as a JSON envelope on stdin, e.g.
#   {"tool_name": "Bash", "tool_input": {"command": "..."}, ...extra keys...}
# and blocks the action ONLY on exit code 2. Any other non-zero is treated as a
# non-blocking hook error and the tool proceeds — so this path must FAIL CLOSED
# (exit 2) on malformed or empty input, never crash out with exit 1.
#
# Claude's tool names are PascalCase (Bash, Write, Edit); the allowlist and egress
# check use internal lowercase names (bash, write_file). Normalize before checking.

# Maps Claude Code tool names to the internal names used in mcp-allowlist.json.
TOOL_NAME_MAP = {
    "Bash": "bash",
    "Write": "write_file",
    "Edit": "write_file",
    "MultiEdit": "write_file",
    "NotebookEdit": "write_file",
}


def normalize_tool_name(name: str) -> str:
    """Map a Claude Code tool name to its internal allowlist name.
    Unmapped names pass through unchanged (already-internal or MCP tools)."""
    return TOOL_NAME_MAP.get(name, name)


if __name__ == "__main__":
    import sys

    # Context for the audit line a denial writes. Populated once the envelope is
    # parsed; the fail-closed denials before that point record tool "unknown".
    _DENY_CTX = {"tool": "unknown"}

    def _deny(reason: str):
        # Claude Code feeds STDERR back to the model on exit 2; stdout is
        # discarded for a blocked call. The reason must go to stderr or the
        # agent is told "no" with no explanation.
        print(reason, file=sys.stderr)
        # Refusal coverage: give the denial an audit line too. Best-effort —
        # an audit failure must never change the verdict, so exit 2 regardless.
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
            from audit import record
            record("PreToolUse", _DENY_CTX["tool"], {}, "DENIED", reason)
        except Exception:
            pass
        sys.exit(2)

    # Read tool call from stdin. Empty or unparseable input FAILS CLOSED.
    raw = sys.stdin.read().strip()
    if not raw:
        _deny("permission gate: empty stdin (fail closed)")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _deny("permission gate: malformed hook payload (fail closed)")
    if not isinstance(data, dict):
        _deny("permission gate: unexpected hook payload shape (fail closed)")

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    # Build a minimal Block-like object for the check
    class _Block:
        def __init__(self, name, input):
            self.name = name
            self.input = input

    _DENY_CTX["tool"] = data.get("tool_name", "") or "unknown"
    block = _Block(normalize_tool_name(data.get("tool_name", "")), tool_input)
    check = make_permission_check()
    try:
        allowed, reason = check(block)
    except PolicyError as exc:
        _deny(f"permission gate: {exc}")
    except Exception as exc:  # noqa: BLE001
        _deny(f"permission gate: internal error ({type(exc).__name__}) (fail closed)")
    if not allowed:
        _deny(reason)
    sys.exit(0)
