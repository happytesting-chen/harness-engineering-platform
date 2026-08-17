"""
Coverage test for the injection marker list — the DETECTION half of ASI01.

`tests/test_prompt_screen.py` and `tests/test_result_screen.py` prove the two
mechanisms *enforce*: a match at position ① erases the prompt, a match at ④ replaces
the tool output before the model reads it. Neither says anything about what those
mechanisms can SEE. This file does, and it pins the answer as a PAIR:

    attacks caught          10 of 12
    legitimate withheld      2 of 12

Both numbers are load-bearing. A marker list tuned only against attacks converges on
matching everything, and at ④ a false positive discards a real tool result while at ①
it erases the operator's own prompt. So "improving detection" is only an improvement
when the second number holds still. Any change to `_INJECTION_MARKERS` that moves
either count fails here and has to be argued for rather than merged quietly.

The two known misses are recorded, not hidden: a base64-encoded payload and a
suppression delivered as reported speech. They are the measured ceiling of the pattern
approach, and moving one of them into `caught` is the unit of progress.

Measured 2026-08-17 against Security-kit/eval/corpus/injection/.

Run:
    python3 tests/test_injection_corpus.py
    python3 -m pytest tests/test_injection_corpus.py -v
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS = PROJECT_ROOT / "Security-kit" / "eval" / "corpus" / "injection"
sys.path.insert(0, str(PROJECT_ROOT / "Security-kit"))

from content_trust import scan_text  # noqa: E402

# The measured pair. Change these only alongside the marker list, and only with the
# corpus run that produced the new numbers.
EXPECT_CAUGHT = 10
EXPECT_KNOWN_MISS = 2
EXPECT_FALSE_POSITIVE = 2
EXPECT_CLEAN = 10

ATTACKS = json.loads((CORPUS / "attacks.json").read_text())["cases"]
LEGITIMATE = json.loads((CORPUS / "legitimate.json").read_text())["cases"]

# expect value -> whether scan_text must return at least one marker
_MUST_MATCH = {"caught": True, "known-miss": False,
               "false-positive": True, "clean": False}


def _mismatches(cases):
    """Every case whose measured behaviour disagrees with its recorded expectation."""
    out = []
    for case in cases:
        want = _MUST_MATCH[case["expect"]]
        markers = scan_text(case["text"])
        if bool(markers) != want:
            out.append(f"{case['id']} expect={case['expect']} "
                       f"got={'match' if markers else 'no match'}")
    return out


# --- per-case expectations ------------------------------------------------------

def test_every_attack_behaves_as_recorded():
    """A caught case must match; a known-miss must not.

    A known-miss that starts matching is good news and still fails here — the corpus
    is the record of what we can see, so the record moves first.
    """
    bad = _mismatches(ATTACKS)
    assert not bad, "attack corpus drift: " + "; ".join(bad)


def test_every_legitimate_case_behaves_as_recorded():
    """A clean case must not match. A recorded false positive must still match.

    The second half is not a typo. Those two cases are the priced cost of the
    check-suppression and authority-claim families; if a rewrite silently stops
    flagging them the price changed, and that is a fact about coverage worth a review.
    """
    bad = _mismatches(LEGITIMATE)
    assert not bad, "legitimate corpus drift: " + "; ".join(bad)


# --- the pinned pair ------------------------------------------------------------

def test_the_measured_pair_is_pinned():
    caught = sum(1 for c in ATTACKS if scan_text(c["text"]))
    flagged = sum(1 for c in LEGITIMATE if scan_text(c["text"]))
    assert caught == EXPECT_CAUGHT, (
        f"attack detection moved: {caught} caught, pinned at {EXPECT_CAUGHT}")
    assert flagged == EXPECT_FALSE_POSITIVE, (
        f"false positives moved: {flagged} flagged, pinned at "
        f"{EXPECT_FALSE_POSITIVE} — a detection gain paid for in outages is not a gain")


def test_the_corpus_itself_cannot_shrink():
    """Deleting an inconvenient case is the cheapest way to make this file green."""
    by = lambda cases, kind: sum(1 for c in cases if c["expect"] == kind)  # noqa: E731
    assert by(ATTACKS, "caught") == EXPECT_CAUGHT
    assert by(ATTACKS, "known-miss") == EXPECT_KNOWN_MISS
    assert by(LEGITIMATE, "false-positive") == EXPECT_FALSE_POSITIVE
    assert by(LEGITIMATE, "clean") == EXPECT_CLEAN
    ids = [c["id"] for c in ATTACKS] + [c["id"] for c in LEGITIMATE]
    assert len(ids) == len(set(ids)), "duplicate case id"


def test_every_accepted_imperfection_carries_its_reasoning():
    """A known miss or a priced false positive without a `why` is just a failing case."""
    for case in ATTACKS + LEGITIMATE:
        if case["expect"] in ("known-miss", "false-positive"):
            assert case.get("why"), f"{case['id']} records no reason"


# --- the single-list claim ------------------------------------------------------

def test_both_pre_model_positions_share_one_marker_list():
    """① and ④ must import the same list, or a tuning change upgrades only one of them.

    This is the reason the marker list lives in content_trust.py and neither screen
    defines its own.
    """
    for name in ("prompt_screen.py", "result_screen.py"):
        src = (PROJECT_ROOT / "Security-kit" / name).read_text()
        assert "from content_trust import scan_text" in src, \
            f"{name} does not share the marker list"
        assert "re.compile" not in src, \
            f"{name} defines patterns of its own — the two positions will drift"


def test_every_attack_catch_is_attributable_to_a_marker():
    """scan_text must name what fired. An unexplained block is unreviewable."""
    for case in ATTACKS:
        if case["expect"] != "caught":
            continue
        markers = scan_text(case["text"])
        assert markers and all(isinstance(m, str) and m for m in markers), \
            f"{case['id']} caught but named no marker"


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
        passed = failed = 0
        for t in tests:
            try:
                t(); print(f"  \033[32m✓ PASS\033[0m  {t.__name__}"); passed += 1
            except AssertionError as e:
                print(f"  \033[31m✗ FAIL\033[0m  {t.__name__}: {e}"); failed += 1
        print(f"\nResults: {passed} passed, {failed} failed")
        sys.exit(1 if failed else 0)
