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

PROJECT_ROOT = Path(__file__).parent.parent
COVERAGE_PATH = Path(__file__).parent / "coverage.json"
MATRIX_PATH = Path(__file__).parent / "control-matrix.md"
ACTIVE_CONTROLS_PATH = Path(__file__).parent / "active-controls.md"
CONTEXT_DIR = PROJECT_ROOT / "Context"

PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|TODO|TBD|NEEDS-CONFIRMATION")


def context_hash(context_dir: Path) -> str:
    """sha256 over sorted non-.template *.md under context_dir (see Global Constraints)."""
    parts = []
    if context_dir.is_dir():
        for p in sorted(context_dir.rglob("*.md")):
            if p.name.endswith(".template"):
                continue
            parts.append(p.read_text())
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def parse_matrix(md_text: str) -> dict:
    """Map Control ID (col 1, backtick-stripped) -> verification cell text (col 4)."""
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
        rows[cid] = cells[3]
    return rows


def _fail(msgs, text):
    msgs.append(text)


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
        for c in applies:
            if c["id"] not in text:
                _fail(msgs, f"active-controls.md does not mention applies control {c['id']}")
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
    for m in messages:
        print(f"  ✗ {m}")
    if n == 0:
        print("  ✓ coverage complete (all applicable controls mapped)")
    sys.exit(1 if n else 0)
