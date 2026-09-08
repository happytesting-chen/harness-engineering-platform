# Provenance

This repository's development history lives on GitHub. On GitLab Dedicated it is a
**single-commit import**: one signed commit carrying the whole tree, no history. This file records
what was imported and how to verify nothing changed on the way.

## Why one commit

The GitLab instance requires a GPG signature on every commit it receives. The platform's history
was 145 commits, none signed, built through pull requests on GitHub. Re-signing history was
possible but would have changed every commit identifier a third time; the operator chose instead
to import the current tree as one signed commit and keep the history where it was written.

## Where the history is

| Where | What |
|---|---|
| `https://github.com/YuanSingapore/harness-engineering-platform` | The development history: 145 commits, every pull request, the CI runs |
| `harness-engineering-platform-github-history-2026-09-07.bundle` (operator archive, `_local/archive/`, not in either repository) | A `git bundle` of every ref, made in advance of the import; verifiable with `git bundle verify`. Refresh it at import time if `main` has moved since |

## What the import will use

| Fact | Value |
|---|---|
| Content baseline on GitHub | commit `a71354fca66e4561e874d1117f594ae60fd19d1d` ("Merge pull request #22"), plus the commit adding this record |
| Tree hash of `template/Security-kit/runtime/` (the verdict's C-5 artifacts) | `b1cd95d49288af391b45f3b9ccf8793ee0ea093e` |
| Import date | 2026-09-08 |

The C-5 tree hash is the anchor, deliberately: it is stable across the commit that writes this
file, whereas a root-tree hash would not be. It is also the only hash the signed verdict depends
on. It has not changed since 2026-09-07 despite substantial work either side of it — the runtime
modules the verdict scopes were never touched.

Verify the import against the baseline, in either repository:

```bash
git rev-parse HEAD:template/Security-kit/runtime      # must print b1cd95d4… in both
```

If that matches, the artefacts the verdict judges are byte-identical in both places, whatever the
commit identifiers say.

## What this means for the signed verdict

`template/evaluation/runtime-security/VERDICT.md` and its amendments name commits (`0dc618e`,
`1e5d499`, and their predecessors). Those commits exist in the GitHub history and in the 2026-09-07 bundle. After the import, they will not exist in the GitLab copy. The
verdict judges a **tree**, so as long as the imported tree's C-5 hash matches the value recorded
here at import time, the decision, its conditions and its expiry carry over unchanged. A reviewer
who needs the commits themselves uses the GitHub history or the bundle.

## Commit references in the documents

`template/progress.md`, the design record under `template/docs/superpowers/`, and the evaluation
documents cite short commit identifiers. Every one of them resolves in the GitHub history and in
the 2026-09-07 bundle above. After the import they will not resolve in the GitLab copy. They are
kept as written because they are the record of how the work was done, and rewriting them would
make the record less true, not more.
