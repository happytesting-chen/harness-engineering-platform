#!/usr/bin/env python3
"""
Interactive gate viewer — a browser UI over the REAL permission gate.

WHAT THIS IS
    A local, zero-dependency web UI that pipes a tool-call envelope into an
    unmodified copy of `governance/permission.py` and shows you its exit code and
    stderr verbatim. Every verdict on screen came out of the mechanism. Nothing
    here decides in advance what the mechanism would say.

WHAT THIS IS NOT
    - Not the enforcement path. Production enforcement is `.claude/settings.json`
      PreToolUse hooks -> `governance/permission.py`. This is a viewer for the same
      CLI those hooks invoke, so it can only ever be as good as that CLI.
    - It NEVER executes the command you type. It asks the gate for a verdict and
      stops. "Gate off" does not execute either -- it reports that the verdict was
      produced and then ignored, which is what removing the hook actually does
      (see tests/test_e2e.py::test_removing_enforcement_allows_dangerous_call).
    - It never writes to your project's policy files. `demo/demo.py` overwrites
      them and restores in a `finally`; this server copies instead, so an
      interrupted demo cannot leave your policy modified.

HOW THE SCRATCH SCENARIO STAYS HONEST
    `permission.py` resolves policy relative to its own `__file__`, so a copy of
    the gate in a scratch tree reads the scratch tree's policy. That gives the demo
    a phase-transition beat without touching your project. Two of the three inputs
    are copied byte-for-byte and the UI displays a SHA-256 of each so you can prove
    it: the gate itself and `deny-list.json`. Only `mcp-allowlist.json` and
    `feature_list.json` are substituted, because the shipped template leaves
    `{{GATED_TOOL}}` and the phase names as placeholders -- there is no gated tool
    to demonstrate until something fills them. Every substitution is reported by
    /api/context.

Usage:
    python3 demo/ui/server.py                 # serves http://127.0.0.1:8765
    python3 demo/ui/server.py --port 9000
    python3 demo/ui/server.py --no-browser

Requirements: zero. Python 3.11+ standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- Layout -----------------------------------------------------------------
# demo/ui/server.py -> demo/ui -> demo -> <project root>
UI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = UI_DIR.parent.parent

REAL_GATE = PROJECT_ROOT / "governance" / "permission.py"
REAL_DENY_LIST = PROJECT_ROOT / "governance" / "deny-list.json"
REAL_ALLOWLIST = PROJECT_ROOT / "governance" / "mcp-allowlist.json"
REAL_FEATURES = PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json"
REAL_AUDIT = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.py"

# The data plane. permission.py gates tool CALLS (loop position 2); these two are for
# the other end of the loop, where a tool RESULT re-enters the context (position 4).
REAL_CONTENT_TRUST = PROJECT_ROOT / "Security-kit" / "content_trust.py"
REAL_HARNESS = PROJECT_ROOT / "demo" / "harness.py"

# The allowlist ships a `{{GATED_TOOL}}` placeholder. A demo needs a real name for
# the phase-gate beat to mean anything, so we fill it with something a leadership
# audience recognises rather than inventing a plausible-looking security tool.
GATED_TOOL = "deploy_release"

# Two pages, deliberately. `/` is the one-story walkthrough -- an injection lands, the
# model believes it, the gate refuses the exfil. `/detail` is the instrument panel for
# whoever wants to argue with the mechanism afterwards.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/story.css": ("story.css", "text/css; charset=utf-8"),
    "/story.js": ("story.js", "text/javascript; charset=utf-8"),
    "/detail": ("detail.html", "text/html; charset=utf-8"),
    "/detail.html": ("detail.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


# --- Scenario construction --------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _demo_allowlist() -> tuple[dict, list[str]]:
    """The project's real allowlist with the shipped placeholder filled in.

    Returns the data plus a list of the substitutions made, so the UI can show
    exactly how the demo policy differs from what the template ships.
    """
    data = json.loads(REAL_ALLOWLIST.read_text())
    notes: list[str] = []
    for tool in data.get("tools", []):
        if "{{" in str(tool.get("name", "")):
            notes.append(f"mcp-allowlist.json: tool name {tool['name']} -> {GATED_TOOL!r}")
            tool["name"] = GATED_TOOL
            tool["description"] = "Ship a build to production (locked until phase-01 passes)"
            tool["version"] = "1.0"
    return data, notes


def _demo_features() -> tuple[dict, list[str]]:
    """The project's real feature list with phase names filled in.

    Statuses are left exactly as shipped -- phase-01 `active`, the rest
    `not-started` -- because that is what makes Gate 2 answerable. Only the
    human-readable placeholder strings are replaced.
    """
    data = json.loads(REAL_FEATURES.read_text())
    names = {
        "phase-01": ("Build and test the change", "Test suite passes on the change"),
        "phase-02": ("Security review sign-off", "Control matrix updated and reviewed"),
        "phase-03": ("Release to production", "Build is live and verified"),
    }
    notes: list[str] = []
    data["project"] = "gate-viewer-demo"
    for feature in data.get("features", []):
        name, behavior = names.get(feature.get("id"), ("Unnamed phase", ""))
        if "{{" in str(feature.get("name", "")):
            notes.append(f"feature_list.json: {feature['id']} name -> {name!r}")
            feature["name"] = name
            feature["behavior"] = behavior
            feature["verification"] = "true"
    return data, notes


def build_scenario() -> tuple[Path, dict]:
    """Assemble a scratch project tree and return it with a provenance record."""
    root = Path(tempfile.mkdtemp(prefix="harness-gate-viewer-"))
    (root / "governance").mkdir()
    observability = root / "Harness-Best-Practice" / "observability"
    observability.mkdir(parents=True)

    # Verbatim: the mechanism and the hard-deny policy.
    shutil.copy2(REAL_GATE, root / "governance" / "permission.py")
    shutil.copy2(REAL_DENY_LIST, root / "governance" / "deny-list.json")
    # Copied so a denial writes a real audit line. permission.py's CLI wraps this
    # import in try/except, so the gate still works without it -- but then the
    # audit panel would have nothing true to show.
    shutil.copy2(REAL_AUDIT, observability / "audit.py")

    allowlist, allowlist_notes = _demo_allowlist()
    features, feature_notes = _demo_features()
    (root / "governance" / "mcp-allowlist.json").write_text(json.dumps(allowlist, indent=2))
    (root / "Harness-Best-Practice" / "feature_list.json").write_text(json.dumps(features, indent=2))

    # Gate 1a compares file identity and falls back to string comparison for a
    # target that does not exist yet. Creating these two means the symlink and
    # hard-link branches of `_same_file` are exercised for real rather than
    # degrading to the string path.
    security_kit = root / "Security-kit"
    security_kit.mkdir()
    (security_kit / "secret_scan.py").write_text("# scratch stand-in\n")
    (security_kit / "content_trust.py").write_text("# scratch stand-in\n")

    provenance = {
        "scenario_dir": str(root),
        "verbatim": [
            {
                "file": "governance/permission.py",
                "sha256": _sha256(REAL_GATE),
                "matches_project": _sha256(REAL_GATE) == _sha256(root / "governance" / "permission.py"),
            },
            {
                "file": "governance/deny-list.json",
                "sha256": _sha256(REAL_DENY_LIST),
                "matches_project": _sha256(REAL_DENY_LIST)
                == _sha256(root / "governance" / "deny-list.json"),
            },
        ],
        "substituted": allowlist_notes + feature_notes,
        "egress_hosts": allowlist.get("egress_hosts", []),
        "deny_pattern_count": len(json.loads(REAL_DENY_LIST.read_text()).get("patterns", [])),
        "gated_tool": GATED_TOOL,
    }
    return root, provenance


# --- Invoking the gate ------------------------------------------------------

# Maps a verdict string back to the gate that produced it. This is *derived from*
# the reason text the gate returned, not predicted before the call -- the reason
# strings are the ones in permission.py's four check_* functions. `permission gate:`
# is tested first because a PolicyError message carries that prefix and would
# otherwise be misattributed.
GATE_SIGNATURES: tuple[tuple[str, str, str, str], ...] = (
    ("permission gate:", "fail-closed", "SEC-POLICY-001", "Policy unreadable or payload malformed"),
    ("protected path (S2.4)", "1a", "SEC-SELF-001", "Protected write target"),
    ("deny-list hit:", "1b", "SEC-CMD-001", "Deny-listed command pattern"),
    ("gated until", "2", "SEC-PHASE-001", "Phase gate"),
    ("not in allowlist", "2", "SEC-PHASE-001", "Tool not on the allowlist"),
    ("no active phase", "2", "SEC-PHASE-001", "No active phase"),
    ("default-deny egress", "3", "SEC-EGRESS-001", "Egress control"),
)

GATE_ORDER = ("1a", "1b", "2", "3")

# Gate 3 is behind `if tool == "bash"` in permission.py:337, and the tool name is
# normalised through TOOL_NAME_MAP first. For anything else the egress check is
# never reached, which the UI shows as "n/a" rather than as a pass it did not earn.
BASH_TOOL_NAMES = frozenset({"Bash", "bash"})


def attribute_gate(reason: str) -> dict:
    for needle, gate, control, label in GATE_SIGNATURES:
        if needle in reason:
            return {"gate": gate, "control": control, "label": label}
    return {"gate": "unknown", "control": "", "label": "Unrecognised verdict string"}


def run_gate(scenario: Path, tool_name: str, tool_input: dict) -> dict:
    """Pipe one envelope into the scratch gate. Returns its verbatim result.

    The proposed command is never executed -- it is JSON on another process's
    stdin and nothing here shells out to it.
    """
    envelope = {"tool_name": tool_name, "tool_input": tool_input}
    payload = json.dumps(envelope)
    try:
        proc = subprocess.run(
            [sys.executable, str(scenario / "governance" / "permission.py")],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": "the gate did not answer within 10s",
            "envelope": envelope,
            "envelope_json": payload,
        }

    reason = proc.stderr.strip()
    blocked = proc.returncode == 2
    result = {
        "envelope": envelope,
        "envelope_json": payload,
        "exit_code": proc.returncode,
        "stderr": reason,
        "stdout": proc.stdout.strip(),
        "blocked": blocked,
        # Only exit 2 blocks in Claude Code. Any other non-zero is a hook error
        # and the tool RUNS -- so "not blocked" is not the same as "exit 0".
        "fails_open": proc.returncode not in (0, 2),
    }
    not_applicable = [] if tool_name in BASH_TOOL_NAMES else ["3"]
    result["gates_not_applicable"] = not_applicable

    if blocked:
        result.update(attribute_gate(reason))
        gate = result["gate"]
        reached = list(GATE_ORDER[: GATE_ORDER.index(gate) + 1]) if gate in GATE_ORDER else []
        result["gates_passed"] = [g for g in reached[:-1] if g not in not_applicable]
        result["gate_denied"] = gate
        result["gates_unevaluated"] = [
            g for g in GATE_ORDER if g not in reached and g not in not_applicable
        ]
    else:
        result.update({"gate": "", "control": "", "label": "No gate returned a verdict"})
        result["gates_passed"] = [g for g in GATE_ORDER if g not in not_applicable]
        result["gate_denied"] = ""
        result["gates_unevaluated"] = []
    return result


# --- The data plane: position 4, where a tool result re-enters context -----------
#
# There is no hook here. PostToolUse fires after the side effect and cannot block, and
# no event exists for "a tool result is about to enter the context window"
# (`SEC-RESULT-GAP-001` in control-matrix.md). Screening therefore has to live INSIDE
# the code that builds the tool_result message -- which is why content_trust.py is a
# library you call rather than a hook you install. Today nothing calls it
# (`SEC-CONTENT-001`, LIBRARY). This endpoint pair shows both halves of that: the real
# ingestion site as it stands, and the real screening function run on the same record.

# Runs the project's OWN content_trust.py, not the scratch stand-in that exists in the
# scenario tree purely so gate 1a's file-identity branch has a file to compare against.
SCREEN_RUNNER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from content_trust import screen_record
payload = json.load(sys.stdin)
r = screen_record(
    payload["record"],
    payload.get("allowed_keys", []),
    tuple(payload.get("text_fields", ())),
)
print(json.dumps({
    "clean_fields": r.clean_fields,
    "dropped_keys": r.dropped_keys,
    "injection_markers": r.injection_markers,
    "oversize_fields": r.oversize_fields,
    "is_suspicious": r.is_suspicious,
}))
"""


def run_screen(record, allowed_keys, text_fields) -> dict:
    """Screen one untrusted record with the real `screen_record`. Verbatim result."""
    payload = json.dumps({
        "record": record,
        "allowed_keys": list(allowed_keys),
        "text_fields": list(text_fields),
    })
    proc = subprocess.run(
        [sys.executable, "-c", SCREEN_RUNNER, str(REAL_CONTENT_TRUST.parent)],
        input=payload, capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or f"screen_record exited {proc.returncode}"}
    return json.loads(proc.stdout)


def ingest_site() -> dict:
    """The real ingestion site in demo/harness.py, read fresh on every request.

    Anchored on the line that calls the tool handler rather than on a fixed line
    number, so this panel keeps telling the truth if the file moves -- and reports
    `screening_present` if somebody actually wires the screen in.
    """
    if not REAL_HARNESS.exists():
        return {"available": False}
    source = REAL_HARNESS.read_text()
    lines = source.splitlines()
    anchor = next(
        (i for i, line in enumerate(lines) if "output = handler(" in line),
        None,
    )
    if anchor is None:
        return {"available": False}
    start = max(0, anchor - 4)
    end = min(len(lines), anchor + 6)
    return {
        "available": True,
        "file": str(REAL_HARNESS.relative_to(PROJECT_ROOT)),
        "anchor_line": anchor + 1,
        "lines": [{"n": i + 1, "text": lines[i]} for i in range(start, end)],
        "screening_present": "content_trust" in source,
        "content_trust": {
            "file": str(REAL_CONTENT_TRUST.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(REAL_CONTENT_TRUST) if REAL_CONTENT_TRUST.exists() else "",
            "available": REAL_CONTENT_TRUST.exists(),
        },
    }


def read_audit(scenario: Path, limit: int = 40) -> list[dict]:
    """Real audit lines, written by the gate's own denial path.

    Allowed calls produce nothing here. That is not an omission in this viewer:
    `permission.py` writes an audit line only from `_deny`, and allowed calls are
    logged by the PostToolUse hook, which is not running.
    """
    log = scenario / "Harness-Best-Practice" / "observability" / "audit.log"
    if not log.exists():
        return []
    lines = []
    for raw in log.read_text().splitlines()[-limit:]:
        try:
            lines.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            lines.append({"raw": raw, "decision": "UNPARSEABLE"})
    return lines


def sign_off_phase_01(scenario: Path) -> dict:
    """Flip phase-01 to `passing` in the SCRATCH feature list, unlocking the gated tool.

    This is the demo's honest weak point and worth saying out loud: nothing
    verifies that a human did this. `feature_list.json` is not a protected path,
    so an agent can write it too -- `SEC-PHASE-GAP-001` in control-matrix.md.
    """
    path = scenario / "Harness-Best-Practice" / "feature_list.json"
    data = json.loads(path.read_text())
    for feature in data.get("features", []):
        if feature["id"] == "phase-01":
            feature["status"] = "passing"
            feature["evidence"] = "demo: human sign-off recorded in the viewer"
        elif feature["id"] == "phase-02":
            feature["status"] = "active"
    path.write_text(json.dumps(data, indent=2))
    return phase_state(scenario)


def reset_phases(scenario: Path) -> dict:
    features, _ = _demo_features()
    path = scenario / "Harness-Best-Practice" / "feature_list.json"
    path.write_text(json.dumps(features, indent=2))
    log = scenario / "Harness-Best-Practice" / "observability" / "audit.log"
    log.unlink(missing_ok=True)
    return phase_state(scenario)


def phase_state(scenario: Path) -> dict:
    path = scenario / "Harness-Best-Practice" / "feature_list.json"
    data = json.loads(path.read_text())
    return {
        "phases": [
            {"id": f["id"], "name": f.get("name", ""), "status": f.get("status", "")}
            for f in data.get("features", [])
        ]
    }


# --- HTTP -------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "HarnessGateViewer/1.0"
    scenario: Path
    provenance: dict

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Local-only viewer; no framing, no sniffing, no caching of a live demo.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict | list, code: int = 200) -> None:
        self._send(code, json.dumps(data).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        route = self.path.split("?")[0]
        if route in STATIC_FILES:
            name, content_type = STATIC_FILES[route]
            path = UI_DIR / name
            if not path.exists():
                self._send_json({"error": f"{name} is missing from demo/ui/"}, 500)
                return
            self._send(200, path.read_bytes(), content_type)
            return
        if route == "/api/context":
            self._send_json({**self.provenance, **phase_state(self.scenario)})
            return
        if route == "/api/audit":
            self._send_json({"lines": read_audit(self.scenario)})
            return
        if route == "/api/ingest":
            self._send_json(ingest_site())
            return
        self._send_json({"error": f"no route {route}"}, 404)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        route = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""
        try:
            body = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            self._send_json({"error": "malformed request body"}, 400)
            return

        if route == "/api/check":
            tool_name = body.get("tool_name") or ""
            tool_input = body.get("tool_input")
            if not isinstance(tool_input, dict):
                tool_input = {}
            result = run_gate(self.scenario, tool_name, tool_input)
            # `enforce: false` mirrors the hook being absent: the gate still
            # produces a verdict, nothing consumes it. The command is not run in
            # either mode.
            result["enforced"] = bool(body.get("enforce", True))
            result["audit"] = read_audit(self.scenario)
            self._send_json(result)
            return
        if route == "/api/screen":
            record = body.get("record")
            if not isinstance(record, (dict, str)):
                self._send_json({"error": "record must be an object"}, 400)
                return
            try:
                self._send_json(run_screen(
                    record,
                    body.get("allowed_keys") or [],
                    body.get("text_fields") or [],
                ))
            except subprocess.TimeoutExpired:
                self._send_json({"error": "screen_record did not answer within 10s"}, 504)
            return
        if route == "/api/signoff":
            self._send_json(sign_off_phase_01(self.scenario))
            return
        if route == "/api/reset":
            self._send_json(reset_phases(self.scenario))
            return
        self._send_json({"error": f"no route {route}"}, 404)

    def log_message(self, fmt: str, *args) -> None:
        # One quiet line per request; the default writes a banner per asset.
        sys.stderr.write(f"  {self.command} {self.path}\n")


def preflight() -> None:
    """Refuse to pretend. If the mechanism is not here, say why and stop."""
    missing = [p for p in (REAL_GATE, REAL_DENY_LIST, REAL_ALLOWLIST, REAL_FEATURES) if not p.exists()]
    if not missing:
        return
    print("This viewer needs the security kit, and it is not here:\n")
    for path in missing:
        print(f"  missing  {path.relative_to(PROJECT_ROOT)}")
    print(
        "\nA project installed with `install.sh --no-security` has no governance/ "
        "directory,\nso there is no gate to demonstrate. Re-install without that flag."
    )
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive viewer for the permission gate.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    args = parser.parse_args()

    preflight()
    scenario, provenance = build_scenario()
    Handler.scenario = scenario
    Handler.provenance = provenance

    url = f"http://127.0.0.1:{args.port}/"
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print(f"Cannot bind port {args.port}: {exc.strerror}. Try --port {args.port + 1}.")
        sys.exit(1)

    print("\n  Permission gate viewer")
    print(f"  Gate      {REAL_GATE.relative_to(PROJECT_ROOT)} (sha256 {provenance['verbatim'][0]['sha256'][:12]})")
    print(f"  Scenario  {scenario}")
    print(f"  Serving   {url}")
    print("  The proposed command is never executed. Ctrl-C to stop.\n")

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
    finally:
        httpd.server_close()
        shutil.rmtree(scenario, ignore_errors=True)


if __name__ == "__main__":
    main()
