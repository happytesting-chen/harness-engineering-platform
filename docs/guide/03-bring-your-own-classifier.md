# Bring your own classifier

The classifier is deliberately not shipped: 700 MB, and a hosted one is a startup error.
The signed lock in `Security-kit/runtime/` names artifacts by **absolute path on the
operator's machine**, so on any other machine `production=True` refuses to start until
you pin your own. That is fail-closed behaviour, not a defect. Rebuild the same
classifier, proven the same way:

```bash
python3 Security-kit/eval/bootstrap_classifier.py bootstrap        # venv · verified download · benchmark · UNSIGNED lock
python3 Security-kit/eval/bootstrap_classifier.py sign --approved-by you@example.org
```

`bootstrap` stops at the first thing it cannot prove: a venv from the ==pinned
`requirements.lock.txt`; the model and tokenizer fetched from the source in
`Security-kit/eval/classifier-source.json` and checked by SHA-256 **and** size before
anything runs (a mismatch deletes the file); the tracked wrapper installed only if its body
hashes to the digest recorded beside the benchmark; the committed benchmark re-run locally
and compared with the committed result on every summary figure **and every per-case
verdict**. Only then does it write `semantic-model.lock.unsigned.json` under
`.classifier-candidates/` at the repo root (git-ignored — it refuses a root git would track).
`sign` is a separate, deliberate step: it re-hashes the artifacts, fills the approval fields,
and runs `--verify` on the result. Point `classifier_lock_path` at **your** signed lock; the
shipped lock stays as the verdict's evidence. TLS verification is never disabled: on a
network that inspects TLS, pass `--ca-bundle your-ca.pem` or set `SSL_CERT_FILE`
(on macOS the keychain's roots are added automatically).

Your lock is yours. The signed verdict in `evaluation/runtime-security/` covers the
operator's deployment; a second deployment gets the same evidence path and the same
measured behaviour, and signs its own lock — and, if it wants one, its own verdict.
