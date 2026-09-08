# Provenance

This repository lives on GitHub today, with full development history. A **single-commit import**
to GitLab Dedicated is planned but not yet performed. This file records the plan and, once the
import happens, becomes the record of what was imported and how to check that nothing changed
on the way — a note at that point will mark it done.

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
| Content baseline the import will use | commit `ed85cc9f3e8a53a018b09bbab9094b02a75258cb` ("Merge pull request #19"), 2026-09-07 — **superseded by whatever `main` is at import time**; re-derive the two hashes below before importing |
| Tree hash of that baseline | `3178d0f41abcc870feca7b5eb59c57dbccffde89` |
| Tree hash of `template/Security-kit/runtime/` (the verdict's C-5 artifacts) | `b1cd95d49288af391b45f3b9ccf8793ee0ea093e` |
| Import date | not yet performed |

Once the import is done, verify it against the baseline above, in either repository:

```bash
git rev-parse HEAD:template/Security-kit/runtime      # must print b1cd95d4… for the C-5 tree
git rev-parse HEAD^{tree}                              # differs from 3178d0f4… only by this file and the CHANGELOG line that names it
```

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
