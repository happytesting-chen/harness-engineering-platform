# Changelog

Human-readable history. The detailed record, with measurements and decisions, is
`template/progress.md`; this file indexes it.

## 2026-09-07 — GitLab move

- `PROVENANCE.md` added: the GitLab repository is a single signed import of GitHub `main` at `ed85cc9`;
  history and the verdict's named commits stay on GitHub and in an archived bundle.

- `.gitlab-ci.yml` added: the baseline-shape assertion and the fatal full-suite run, as on GitHub.
- Clone URLs point at `sgts.gitlab-dedicated.com/wog/csa/csacentral/ai-team/security-by-design_harness`.
- The GitHub workflow is retained while a GitHub copy exists.

## 2026-09-07 — documentation restructure

- Root README rewritten as an entry point; platform documentation moved to `docs/`: a guide cut by task
  (five pages) and a reference cut by question (five pages plus a directory-map appendix).
- `template/README.md` and `template/Security-kit/README.md` trimmed to what a copied project needs.
- Legacy examples `claims-agent` and `red-team-harness` removed; the template A/B evaluation
  evidence kept at `docs/evaluations/2026-08-template-ab/`.
- CONTRIBUTING, CHANGELOG and SECURITY added.
- Onboarding: prerequisites and the project-root rule up front, an audience router in the README, the
  real GitLab clone URL, and an integrator's page that starts from the worked example.

## Sessions recorded in `template/progress.md`

- Session 1 — 2026-08-04
- Sessions 2–8 — 2026-08-05 → 08-14 (reconstructed from git, not from a log)
- Session 9 — 2026-08-15
- Session 10 — 2026-08-16 (unattended run, plan tasks 5–10)
- Session 11 — 2026-08-16 (`SEC-XXX-001` removed from the shipped matrix)
- Session 12 — 2026-08-17 (the READMEs were the broken link in the setup chain)
- Session 12b — 2026-08-17 (the four review gaps: end state, code location, demo, example README)
- Session 13 — 2026-08-17 (pre-model screening at ① and ④) — `f3e019a`
- Session 14 — 2026-08-22 (the four gates in a deployed application) — `099a536`
- Session 15 — 2026-08-31 (audit of the semantic-enforcement plan) — `3027eb8`, `e77b809`
- Session 16 — 2026-08-31 → 09-01 (the twelve-task build) — `bce2253` … `f73230a`
- Session 17 — 2026-09-01 → 09-02 (review, claims batch, verdict)
- Session 18 — 2026-09-02 (history rewrite)
- Session 19 — 2026-09-02 (bring your own classifier)
- Session 20 — 2026-09-03 (corpus expansion: what the classifier actually sees)
- Session 21 — 2026-09-03 (CI runs the whole suite; relock merged)
