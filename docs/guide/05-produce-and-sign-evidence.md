# Produce and sign evidence

The operator's sequence for a release decision. Every step is a command whose output is a file
in the repository; nothing is asserted that a re-run cannot reproduce. The method behind each
artefact is in [Claims and evidence](../reference/04-claims-and-evidence.md).

## 1. Run the gate

```bash
cd template
python3 -m pytest tests -q
./init.sh                                  # exit 1, the documented 5-error baseline
python3 Security-kit/check_coverage.py     # I1–I6
```

## 2. Drive the attack matrix and confirm replay

```bash
python3 Security-kit/runtime/attack_driver.py --output /tmp/traces.jsonl
cmp /tmp/traces.jsonl evaluation/runtime-security/attack-traces.jsonl   # byte-identical, or explain why
python3 -m pytest tests/runtime/test_replay.py -q
```

Every case must be RESISTANT on its side-effect oracle. A VULNERABLE case is a release blocker,
not a finding to disposition.

## 3. Benchmark the classifier and verify the lock

```bash
python3 Security-kit/eval/eval_runtime_injection.py \
  --candidate-manifest evaluation/runtime-security/candidate-manifests/<candidate>.json \
  --output /tmp/bench                        # add --chunk-size/--chunk-overlap to measure a window
python3 Security-kit/eval/eval_runtime_injection.py \
  --lock Security-kit/runtime/semantic-model.lock.json --verify
```

Results are immutable: commit a new result file beside the old one, never overwrite. On a machine
without the classifier, [Bring your own classifier](03-bring-your-own-classifier.md) first; its
`sign` step is a human action.

## 4. Work the reviewer checklist

`evaluation/runtime-security/verification-summary.md`, section *What a reviewer must check*.
Run each item as a live attempt, not a reading. Record every finding, including the ones judged
acceptable — a finding omitted is a finding unmanaged. Any open P0 or P1 means `DEPLOY_BLOCKED`.

## 5. Sign, or amend

The decision, its conditions and its expiry go in `evaluation/runtime-security/VERDICT.md`,
signed by a named person. A verdict is never edited in place: a change of revision label is an
**amendment** (see A-1 and A-2 there); a change of decision, conditions or acceptances is a new
verdict with a new signature. Anything that alters a scoped artefact — the runtime modules, the
policy digest, the lock, the corpus — lapses the verdict under its own terms and returns you to
step 1.
