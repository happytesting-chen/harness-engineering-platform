"""
Selection benchmark scorer (Phase 1, Q1). Deterministic — no LLM.

Positive class = "the control applies". A verdict of `applies` OR `gap` is a positive
prediction (both assert the surface exists); `n_a` is negative. Ground-truth labels use
`applies`/`n_a` only. Headline metric = recall: a false `n_a` (predicting n_a when the
label is applies) is a FALSE NEGATIVE — the missed-control failure that matters.
"""
import json
import sys
from pathlib import Path

POSITIVE_PRED = {"applies", "gap"}


def _is_pos_pred(v: str) -> bool:
    return v in POSITIVE_PRED


def _is_pos_label(v: str) -> bool:
    return v == "applies"


def confusion(pred: dict, labels: dict) -> dict:
    tp = fp = fn = tn = 0
    for cid, label in labels.items():
        p = _is_pos_pred(pred.get(cid, "n_a"))
        y = _is_pos_label(label)
        if p and y:
            tp += 1
        elif p and not y:
            fp += 1
        elif not p and y:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def score(cases: list) -> dict:
    tot = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for pred, labels in cases:
        for k, v in confusion(pred, labels).items():
            tot[k] += v
    tp, fp, fn = tot["tp"], tot["fp"], tot["fn"]
    tot["recall"] = tp / (tp + fn) if (tp + fn) else 1.0
    tot["precision"] = tp / (tp + fp) if (tp + fp) else 1.0
    return tot


def _load_case(case_dir: Path) -> tuple:
    """A recorded case dir holds coverage.json (prediction) + labels.json (ground truth)."""
    pred_raw = json.loads((case_dir / "coverage.json").read_text())
    pred = {c["id"]: c["verdict"] for c in pred_raw["controls"]}
    labels = json.loads((case_dir / "labels.json").read_text())
    return pred, labels


if __name__ == "__main__":
    recorded = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "recorded"
    cases = ([_load_case(d) for d in sorted(recorded.iterdir()) if (d / "coverage.json").is_file()]
             if recorded.is_dir() else [])
    if not cases:
        print(f"no recorded cases in {recorded} — run the skill and record outputs first")
        sys.exit(2)
    s = score(cases)
    print(f"cases={len(cases)}  TP={s['tp']} FP={s['fp']} FN={s['fn']} TN={s['tn']}")
    print(f"recall={s['recall']:.3f}  precision={s['precision']:.3f}")
