# Contributing

This repository ships a security harness, so the contribution rules are stricter than a typical
template repository. They exist to keep every documented claim provable.

## Ground rules

- **Everything lands through a merge request.** No direct pushes to `main`, including from agents.
- **Protected paths are never edited by an agent.** The set is defined in code, not here:
  `BUILTIN_PROTECTED_PATHS` in `template/governance/permission.py` and the path entries in
  `template/governance/deny-list.json` — the governance policy files and dispatcher, the Security-kit
  screening modules, and everything under `template/Security-kit/runtime/`. They change only by a
  human applying a reviewed patch from `template/docs/superpowers/patches/`. Applying the patch is
  the signing act.
- **Humans own the claims register.** `template/Security-kit/mechanisms.json` and
  `requirements.json` are edited by people; agents propose patches.
- **Mechanism code is standard library only.** Tests must run without `pytest`; every test file
  keeps its stdlib `__main__` runner. `pytest` is a CI tool, not a dependency.
- **Numbers come from a run, not from memory.** Any figure in a document names the command that
  produced it. If a number moves, the document that quotes it moves in the same change.

## Before you open a merge request

```bash
cd template
./init.sh                       # must exit 1 with exactly the documented 5-error baseline
python3 -m pytest tests -q      # or: run each tests/**/test_*.py directly
python3 Security-kit/check_coverage.py
```

CI asserts the baseline's exact error set and runs the full suite. The pipeline of record is
`.gitlab-ci.yml` on GitLab Dedicated; `.github/workflows/harness-baseline.yml` is the same two jobs
and is kept only while a GitHub copy of the repository exists — change both or delete the GitHub one. A merge request that changes
the baseline must change `docs/superpowers/specs/2026-08-13-security-kit-build-design.md` §7.4.1
in the same change.

## What voids the signed verdict

Any change under `template/Security-kit/runtime/`, to the policy digest, to the classifier lock, or
to the benchmark corpus lapses `template/evaluation/runtime-security/VERDICT.md` under its own
terms. Bundle such changes and re-run the evidence once; see the verdict's amendments for the
form a re-scope takes.

## Session record

Every working session appends to `template/progress.md`: what changed, what was measured, and the
decisions taken with their rationale. That file, not the commit log, is the project's memory.
