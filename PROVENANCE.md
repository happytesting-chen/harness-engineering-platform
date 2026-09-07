# Provenance

This repository lives on GitLab Dedicated as a **single-commit import**. Its development history
is not here, by decision, and this file says where it is and how to check that nothing changed
on the way.

## Why one commit

The GitLab instance requires a GPG signature on every commit it receives. The platform's history
was 145 commits, none signed, built through pull requests on GitHub. Re-signing history was
possible but would have changed every commit identifier a third time; the operator chose instead
to import the current tree as one signed commit and keep the history where it was written.

## Where the history is

| Where | What |
|---|---|
| `https://github.com/YuanSingapore/harness-engineering-platform` | The development history: 145 commits, every pull request, the CI runs |
| `harness-engineering-platform-github-history-2026-09-07.bundle` (operator archive, not in either repository) | A `git bundle` of every ref on the day of import, verifiable with `git bundle verify` |

## What was imported

| Fact | Value |
|---|---|
| Content baseline on GitHub | commit `ed85cc9f3e8a53a018b09bbab9094b02a75258cb` ("Merge pull request #19"), 2026-09-07 |
| Tree hash of that baseline | `3178d0f41abcc870feca7b5eb59c57dbccffde89` |
| Tree hash of `template/Security-kit/runtime/` (the verdict's C-5 artifacts) | `b1cd95d49288af391b45f3b9ccf8793ee0ea093e` |
| Import date | 2026-09-07 |

To verify the import against the baseline, in either repository:

```bash
git rev-parse HEAD:template/Security-kit/runtime      # must print b1cd95d4… for the C-5 tree
git rev-parse HEAD^{tree}                              # differs from 3178d0f4… only by this file and the CHANGELOG line that names it
```

## What this means for the signed verdict

`template/evaluation/runtime-security/VERDICT.md` and its amendments name commits (`0dc618e`,
`1e5d499`, and their predecessors). Those commits exist in the GitHub history and in the bundle,
not in this repository. The verdict judges a **tree**, and the C-5 tree hash above is the same
object in both places, so the decision, its conditions and its expiry carry over unchanged. A
reviewer who needs the commits themselves uses the GitHub history or the bundle.

## Commit references in the documents

`template/progress.md`, the design record under `template/docs/superpowers/`, and the evaluation
documents cite short commit identifiers. Every one of them resolves in the GitHub history and in
the bundle. None resolves here. They are kept as written because they are the record of how the
work was done, and rewriting them would make the record less true, not more.
