#!/usr/bin/env python3
"""Protocol-v1 classifier process: DeBERTa-v3 prompt-injection ONNX, local only.

Invoked by runtime/classifier.py as: wrapper.py <model_path>
Reads ONE JSON request on stdin, writes ONE JSON response on stdout, exits.

Security posture:
- No network: the tokenizer and model load from local files beside <model_path>;
  nothing here imports an HTTP client or resolves a hostname.
- The request's text is DATA: it is tokenized and classified, never executed,
  never formatted into anything, never echoed to stdout.
- Output is exactly the closed contract {schema_version, label, confidence} —
  the adapter rejects anything else, so this process prints nothing else.
- Any internal failure exits non-zero with NO stdout, which the adapter maps to
  UNRESOLVED (fail closed).
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

LABEL_MAP = {0: "data", 1: "instruction"}  # config.json id2label: 0=SAFE, 1=INJECTION
MAX_TOKENS = 512


def main() -> int:
    model_path = Path(sys.argv[1]).resolve()
    raw = sys.stdin.buffer.read()
    request = json.loads(raw.decode("utf-8"))
    if request.get("schema_version") != 1 or not isinstance(request.get("text"), str):
        return 2

    tokenizer = Tokenizer.from_file(str(model_path.parent / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=MAX_TOKENS)
    encoding = tokenizer.encode(request["text"])

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    input_names = {i.name for i in session.get_inputs()}
    feeds = {}
    if "input_ids" in input_names:
        feeds["input_ids"] = np.array([encoding.ids], dtype=np.int64)
    if "attention_mask" in input_names:
        feeds["attention_mask"] = np.array([encoding.attention_mask], dtype=np.int64)
    if "token_type_ids" in input_names:
        feeds["token_type_ids"] = np.array([encoding.type_ids], dtype=np.int64)

    logits = session.run(None, feeds)[0][0].astype(np.float64)
    exps = np.exp(logits - logits.max())
    probs = exps / exps.sum()
    idx = int(probs.argmax())

    sys.stdout.write(json.dumps({
        "schema_version": 1,
        "label": LABEL_MAP[idx],
        "confidence": round(float(probs[idx]), 6),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # no stdout on failure — the adapter reads silence + non-zero exit as UNRESOLVED
        raise SystemExit(3)
