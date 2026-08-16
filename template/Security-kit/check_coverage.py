"""
Coverage checker — the mechanical gate for security-tailor (Phase 1).

Fails CLOSED: a missing, malformed, or stale coverage.json is an ERROR, and every
`applies` control must map to a control-matrix row with a non-empty verification.
Enforces COMPLETENESS of coverage, NOT adequacy of each verification (that stays human).

Idioms mirror governance/permission.py (path constants + json.loads(read_text())).
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).parent.parent
COVERAGE_PATH = Path(__file__).parent / "coverage.json"
MATRIX_PATH = Path(__file__).parent / "control-matrix.md"
ACTIVE_CONTROLS_PATH = Path(__file__).parent / "active-controls.md"
KIRO_MIRROR_PATH = PROJECT_ROOT / "kiro" / "steering" / "active-controls.md"
CONTEXT_DIR = PROJECT_ROOT / "Context"

PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|TODO|TBD|NEEDS-CONFIRMATION")
STATUS_RE = re.compile(r"\*\*(MECHANICAL|OBSERVE|LIBRARY|GAP)\b")

MECHANISMS_PATH = Path(__file__).parent / "mechanisms.json"
INIT_SH_PATH = PROJECT_ROOT / "init.sh"

# `[MECH]`/`[OBS]`/`[LIB]` are the register's vocabulary; the matrix's is the long
# form. Written years apart, so the join needs a map rather than an assumption.
# `[GAP]` maps to NO register row, and `[GUIDE]`/`[APP]` are deliberately ignored:
# they are advice to a human or an application, not mechanism statuses, and
# treating them as statuses would force fake register rows (spec §1.8.7).
STATUS_SYNONYM = {
    "MECHANICAL": "MECHANICAL", "MECH": "MECHANICAL",
    "OBSERVE": "OBSERVE", "OBS": "OBSERVE",
    "LIBRARY": "LIBRARY", "LIB": "LIBRARY",
}

LEGAL = {
    "GATE":    {"can_deny": {True},    "decides": "required", "attaches_at": "required"},
    "RECORD":  {"can_deny": {False},   "decides": "required", "attaches_at": "required"},
    "SCREEN":  {"can_deny": {False},   "decides": "required", "attaches_at": None},
    "DOORWAY": {"can_deny": {"n/a"},   "decides": None,       "attaches_at": "required"},
    "CHECKER": {"can_deny": {"n/a"},   "decides": "required", "attaches_at": "required"},
    "DRAFTER": {"can_deny": {"n/a"},   "decides": "required", "attaches_at": "required"},
    "CLAIMS":  {"can_deny": {"n/a"},   "decides": None,       "attaches_at": None},
}


def _load_register(path: Path) -> dict:
    """Fail closed: a missing or malformed register is an ERROR, never an empty pass.

    An empty register would make I1 and I2 report zero errors over zero rows —
    §1.6's vacuous check, arrived at by deleting a file.
    """
    reg = json.loads(path.read_text())
    mechanisms = reg.get("mechanisms")
    if not isinstance(mechanisms, list):
        raise ValueError("mechanisms.json has no 'mechanisms' list")
    if not all(isinstance(m, dict) for m in mechanisms):
        raise ValueError("mechanisms.json: every entry in 'mechanisms' must be an object")
    return reg


def _derive_status(m: dict):
    """Spec §4.5.4's table. Returns None when no row of the table applies.

    `is True` / `is False`, not `==`: in Python `True == 1`, and can_deny is
    tri-valued with a string third value.
    """
    d, a, c = m.get("decides"), m.get("attaches_at"), m.get("can_deny")
    if d is None and a is None:
        return "GAP"                       # not permitted in this file (§4.5.5)
    if d is None:
        return "MECHANICAL" if c == "n/a" else None      # DOORWAY
    if a is None:
        return "LIBRARY" if c is False else None
    if c is True:
        return "MECHANICAL"
    if c is False:
        return "OBSERVE"
    if c == "n/a":
        return "MECHANICAL"                # CHECKER / DRAFTER
    return None


def check_i2(register: dict) -> tuple:
    """I2 — internal coherence. A pure function of one row, so it CANNOT skip.

    Returns (errors, messages, skips) with skips always 0. The third element is
    kept so every invariant has one shape.
    """
    errors, msgs = 0, []
    for m in register["mechanisms"]:
        mid = m.get("id", "<no id>")
        for key in ("id", "category", "decides", "attaches_at", "can_deny",
                    "proof", "status", "portable_to_runtime"):
            if key not in m:
                errors += 1
                msgs.append(f"{mid}: required key '{key}' is missing")
        if "category" not in m:
            continue
        cat = m.get("category")
        rule = LEGAL.get(cat)
        if rule is None:
            errors += 1
            msgs.append(f"{mid}: category {cat!r} is not one of {sorted(LEGAL)}")
            continue
        if m.get("can_deny") not in rule["can_deny"]:
            errors += 1
            msgs.append(f"{mid}: {cat} requires can_deny in "
                        f"{sorted(rule['can_deny'], key=str)}, got {m.get('can_deny')!r}")
        for field in ("decides", "attaches_at"):
            want = rule[field]
            got = m.get(field)
            if want == "required" and got is None:
                errors += 1
                msgs.append(f"{mid}: {cat} requires a non-null {field}")
            if want is None and got is not None:
                errors += 1
                msgs.append(f"{mid}: {cat} requires {field} to be null, got {got!r}")
        derived = _derive_status(m)
        if derived is None:
            errors += 1
            msgs.append(f"{mid}: (decides, attaches_at, can_deny) matches no row of "
                        f"§4.5.4's derivation table")
        elif derived == "GAP":
            errors += 1
            msgs.append(f"{mid}: derives to GAP — a gap has no mechanism row (§4.5.5)")
        elif derived != m.get("status"):
            errors += 1
            msgs.append(f"{mid}: status says {m.get('status')}, derives to {derived}")
        if cat == "DOORWAY" and m.get("portable_to_runtime") is not False:
            errors += 1
            msgs.append(f"{mid}: every DOORWAY is portable_to_runtime false — the "
                        f"pre-tool event is a property of the host, not of the control")
    return errors, msgs, 0


def check_status(path: Path = MECHANISMS_PATH) -> tuple:
    """Run the claims invariants. Returns (error_count, messages).

    Prints one line per invariant INCLUDING its skip count, because a check that
    silently skipped everything and a check that passed everything are otherwise
    the same output (spec §1.6; precedent f16525a).

    Each invariant prints its OWN population, not one shared figure: I1-I3
    range over the register (len(register)), I4 and I6 range over the matrix
    (len(matrix)), and I5 ranges over ZONE3_DRAFTERS. A single shared number
    would make an invariant that measured nothing look identical to one that
    measured everything — exactly the vacuous-check failure mode this file
    exists to prevent (precedent f16525a: a sampling test reported 100% while
    57% of the matrix went unmeasured).

    `path` defaults to MECHANISMS_PATH but is a real parameter (not a hardcoded
    global) so the fail-closed branch below is reachable from a test without
    mutating module state (fix round 1, finding 1).
    """
    try:
        register = _load_register(path)
    except Exception as e:
        return 1, [f"mechanisms.json unreadable: {e} (fail-closed)"]

    register_n = len(register["mechanisms"])
    results = [("I2 coherence", register_n, check_i2(register))]

    errors, msgs = 0, []
    for label, population, (e, m, s) in results:
        errors += e
        # Labelled, not flat: once I1-I6 all run, an unlabelled message list
        # can't say which invariant produced which id-prefixed line, and
        # several invariants emit messages about the same ids (fix round 1,
        # finding 2).
        msgs.extend(f"{label}: {x}" for x in m)
        mark = "✗" if e else "✓"
        print(f"  {mark} {label}: {e} error(s), {population - s}/{population} checked, skipped {s}")
    return errors, msgs


def context_hash(context_dir: Path) -> str:
    """sha256 over sorted non-.template *.md under context_dir (see Global Constraints)."""
    parts = []
    if context_dir.is_dir():
        for p in sorted(context_dir.rglob("*.md")):
            if p.name.endswith(".template"):
                continue
            parts.append(p.read_text())
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


class MatrixRow(NamedTuple):
    """One control-matrix row, by column. The status token lives in `objective`
    (cell 2) and the paths and function names in `location` (cell 3)."""
    id: str
    objective: str
    location: str
    verification: str
    evidence: str
    status_token: str | None  # None when the row states no strength — an I4 error


def parse_matrix_rows(md_text: str) -> dict:
    """Map Control ID (col 1, backtick-stripped) -> MatrixRow.

    The status regex is `**WORD\\b`, not `**WORD**`: two rows write
    `**GAP, and …**`, and matching on the closing `**` reports them as
    unlabelled. Measured 2026-08-15 — the loose form finds 5 unlabelled rows
    where the tree has 3.
    """
    rows = {}
    for line in md_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        cid = cells[0].strip("`").strip()
        if cid in ("Control ID", "") or set(cells[0]) <= {"-", " "}:
            continue
        m = STATUS_RE.search(cells[1])
        rows[cid] = MatrixRow(cid, cells[1], cells[2], cells[3], cells[4],
                              m.group(1) if m else None)
    return rows


def parse_matrix(md_text: str) -> dict:
    """Map Control ID (col 1, backtick-stripped) -> verification cell text (col 4).

    Kept as the narrow view the coverage rules use; `parse_matrix_rows` is the
    same parse with every column. One parser, two projections.
    """
    return {k: r.verification for k, r in parse_matrix_rows(md_text).items()}


def _fail(msgs, text):
    msgs.append(text)


def check_kiro_mirror(project_root: Path) -> tuple:
    """Layer-D exists for every host that has one. Returns (errors, messages).

    Conditional on purpose: a Claude-only copy has no Kiro host, and demanding a
    mirror there would be an over-block. But the skip is PRINTED — a silent skip
    is the failure mode of a vacuous check (spec §1.6).

    Runs OUTSIDE check()'s applies-loop deliberately: rule 1 returns early when
    coverage.json is missing, which is the shipped state, so a mirror check
    living in that loop would never execute in the template.
    """
    steering = project_root / "kiro" / "steering"
    mirror = project_root / "kiro" / "steering" / "active-controls.md"
    if not steering.is_dir():
        return 0, ["layer-D Kiro mirror: skipped — no kiro/steering directory"]
    if not mirror.is_file():
        return 1, ["kiro/steering/active-controls.md missing — layer-D unwired for the Kiro host"]
    return 0, []


def check(project_root: Path) -> tuple:
    """Return (error_count, messages). 0 errors == pass. Fails closed."""
    msgs = []
    # Rule 1: present
    if not COVERAGE_PATH.is_file():
        _fail(msgs, "coverage.json missing — run /security-tailor (fail-closed)")
        return 1, msgs
    # Rule 4: parseable / shape
    try:
        cov = json.loads(COVERAGE_PATH.read_text())
        controls = cov["controls"]
        assert isinstance(controls, list)
    except Exception as e:  # malformed
        _fail(msgs, f"coverage.json malformed: {e}")
        return 1, msgs
    errors = 0
    # Rule 2: freshness
    expected = f"Context/ @ {context_hash(CONTEXT_DIR)}"
    if cov.get("generated_from") != expected:
        _fail(msgs, "coverage.json stale — Context/ changed; re-run /security-tailor")
        errors += 1
    # Rule 3: every applies mapped to a non-empty, non-placeholder verification
    matrix = parse_matrix(MATRIX_PATH.read_text()) if MATRIX_PATH.is_file() else {}
    applies = [c for c in controls if c.get("verdict") == "applies"]
    for c in applies:
        row = c.get("matrix_row")
        if not row or row not in matrix:
            _fail(msgs, f"{c.get('id')}: applies but no matrix row '{row}'")
            errors += 1
            continue
        cell = matrix[row]
        if not cell or PLACEHOLDER_RE.search(cell):
            _fail(msgs, f"{c.get('id')}: matrix row '{row}' has no real verification ('{cell}')")
            errors += 1
    # Layer-D consistency: active-controls.md exists and covers exactly the applies set
    if not ACTIVE_CONTROLS_PATH.is_file():
        _fail(msgs, "active-controls.md missing — layer-D steering unwired")
        errors += 1
    else:
        text = ACTIVE_CONTROLS_PATH.read_text()
        mirror_text = KIRO_MIRROR_PATH.read_text() if KIRO_MIRROR_PATH.is_file() else None
        for c in applies:
            if c["id"] not in text:
                _fail(msgs, f"active-controls.md does not mention applies control {c['id']}")
                errors += 1
            if mirror_text is not None and c["id"] not in mirror_text:
                _fail(msgs, f"kiro/steering/active-controls.md does not mention applies control {c['id']}")
                errors += 1
    return errors, msgs


def stamp() -> str:
    """Write the freshness hash into coverage.json. The skill (an LLM) CANNOT compute a
    sha256 by hand, so it calls `check_coverage.py --stamp` as its final write action.
    Returns the stamped value. Idempotent."""
    cov = json.loads(COVERAGE_PATH.read_text())
    cov["generated_from"] = f"Context/ @ {context_hash(CONTEXT_DIR)}"
    COVERAGE_PATH.write_text(json.dumps(cov, indent=2) + "\n")
    return cov["generated_from"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stamp":
        print(f"  ✓ stamped {stamp()}")
        sys.exit(0)
    n, messages = check(PROJECT_ROOT)
    kn, kmessages = check_kiro_mirror(PROJECT_ROOT)
    for m in messages + [m for m in kmessages if "skipped" not in m]:
        print(f"  ✗ {m}")
    for m in [m for m in kmessages if "skipped" in m]:
        print(f"  – {m}")
    if n == 0:
        print("  ✓ coverage complete (all applicable controls mapped)")
    # The claims invariants run REGARDLESS of the coverage verdict: rule 1 returns
    # early on a missing coverage.json — the shipped state — and I1-I6 are about the
    # register and the matrix, neither of which waits on a tailored product.
    sn, smessages = check_status()
    for m in smessages:
        print(f"  ✗ {m}")
    sys.exit(1 if (n or kn or sn) else 0)
