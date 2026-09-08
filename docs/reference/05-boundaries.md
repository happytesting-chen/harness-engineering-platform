# Boundaries: where the guarantee stops

Stated plainly, because a security control you misunderstand is worse than none. Each line
links to the full statement.

- **Runtime routing is opt-in.** Anything that bypasses the host bypasses its controls.
  Verified by architecture review, not by the library —
  [`SEC-RUNTIME-GAP-001`](../../template/Security-kit/control-matrix.md).
- **Semantic classification is not proof of benign intent.** On the committed benchmark,
  rules plus the classifier caught **14 of 16** attacks and withheld **3 of 8** legitimate
  cases; two workflow-impersonation attacks were confidently misclassified. The action and
  output gates are the compensating layers —
  [`classifier-selection.md`](../../template/evaluation/runtime-security/classifier-selection.md).
- **The review queue is unbounded in code.** Fail-closed screening queues false positives
  for a human; the deployment sets the bound — [`limitations.md`](../../template/evaluation/runtime-security/limitations.md).
- **Text-only, single-agent.** Memory, delegation, binary ingress, remote classifiers and
  streaming refuse to start. Multi-host is out of scope.
- **Not an OS sandbox or a network firewall.** It governs sources and sinks routed through
  the host; it does not confine a compromised process.
- **Build-time gates cover write/exec tools only.** `Read`, `Grep`, `WebFetch` and `Task`
  are unmatched — a `Task` spawn reaches no gate. The runtime host has no such hole.
- **Egress is policy matching, not network enforcement.** Hosts match exactly and structured
  destinations are checked on every tool, but the shell half is a five-token blocklist and
  field matching is by *name* — [`template/README.md` § Gate 3](../../template/README.md#how-enforcement-works).
- **The agent cannot edit its own gate — except through a scripting runtime.** 28 files are
  hard-denied by identity; `python3 -c` opening one for write is a measured, pinned residual
  — [`SECURITY.md` S2.4](../../template/Security-kit/SECURITY.md).
- **Core is standard library; the semantic classifier is not.** It runs as a separate,
  digest-pinned local process with its own venv
  ([`requirements.lock.txt`](../../template/evaluation/runtime-security/requirements.lock.txt)).
  `pytest` is needed only for the full suite.

---

For the specific case of prompt injection — what the two detection layers catch, what they
demonstrably miss, and why the action gate rather than detection is the guarantee — see
[Prompt injection](06-prompt-injection.md).
