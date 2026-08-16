# Build A Scorecard

**State:** Initialized; scoring is **not yet authorized**.  
**Readiness:** **BLOCKED** by `readiness-review.md`.  
**Build A score:** **Not scored (0–4 evaluation has not begun).**

The four dimensions apply only after approved Claims implementation and complete Build A verification. Initialization does not award points, claim a pass, or record human approval.

| Dimension | Point | Review criterion | Required evidence | Current state |
|---|---:|---|---|---|
| Correctness | — | Complete deterministic Claims contract and exactly one successful minimal local result per reviewed fixture. | Claims tests and attributable fixture/result evidence. | Not available; Claims behavior intentionally absent. |
| Local reproducibility | — | Unchanged input/configuration produces equivalent terminal outcome and result on repeated complete runs. | Two unchanged complete verification runs with equivalent results. | Not evaluated. |
| Traceability | — | Every result, conclusion, and score links to reviewed input/configuration and non-sensitive evidence. | Filled `evidence-index.md` with artifact hashes/locations. | Packet initialized only. |
| Reviewed verification | — | Retained core and Claims tests pass with no unresolved blockers, and human review is recorded. | Exact commands/results plus explicit human decision. | Retained core passes; readiness blockers and human gate remain. |

**Snapshot rule:** any failed or unsupported dimension blocks snapshot eligibility regardless of total. See `snapshot-decision.md`.
