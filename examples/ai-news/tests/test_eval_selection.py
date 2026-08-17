# tests/test_eval_selection.py  (stdlib dual-mode, same shape as tests/test_coverage.py)
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent.parent / "Security-kit" / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
import eval_selection as es  # noqa: E402


def case_confusion_counts_applies_as_positive():
    pred = {"LLM01": "applies", "LLM08": "n_a", "ASI03": "applies", "LLM02": "n_a"}
    labels = {"LLM01": "applies", "LLM08": "n_a", "ASI03": "n_a", "LLM02": "applies"}
    m = es.confusion(pred, labels)
    assert m == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}, m  # LLM01 TP, ASI03 FP, LLM02 FN, LLM08 TN


def case_false_n_a_is_a_false_negative():
    m = es.confusion({"LLM01": "n_a"}, {"LLM01": "applies"})
    assert m["fn"] == 1 and m["tp"] == 0, m


def case_gap_counts_as_positive_prediction():
    assert es.confusion({"ASI03": "gap"}, {"ASI03": "applies"})["tp"] == 1


def case_score_aggregates_recall_precision():
    cases = [({"LLM01": "applies"}, {"LLM01": "applies"}),
             ({"LLM02": "n_a"}, {"LLM02": "applies"})]
    s = es.score(cases)
    assert s["tp"] == 1 and s["fn"] == 1, s
    assert s["recall"] == 0.5, s


CASES = [case_confusion_counts_applies_as_positive, case_false_n_a_is_a_false_negative,
         case_gap_counts_as_positive_prediction, case_score_aggregates_recall_precision]


def run_eval_selection_tests():
    passed, failed, failures = 0, 0, []
    for c in CASES:
        try:
            c(); passed += 1
        except Exception as e:
            failed += 1; failures.append(f"{c.__name__}: {e}")
    return passed, failed, failures


def test_all_eval_selection_cases():  # pytest-discoverable wrapper
    passed, failed, failures = run_eval_selection_tests()
    assert failed == 0, "\n".join(failures)


if __name__ == "__main__":
    p, f, fails = run_eval_selection_tests()
    for line in fails:
        print(f"  ✗ {line}")
    print(f"  {p} passed, {f} failed")
    sys.exit(1 if f else 0)
