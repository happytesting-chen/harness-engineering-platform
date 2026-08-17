# Claims Processing Agent

## Product Overview

ClaimsAssist is a single-agent system that reads insurance claim submissions (PDFs, structured forms, and free-text narratives) from untrusted claimants and produces a deterministic routing decision: APPROVED, REJECTED, or PENDING_REVIEW. The agent uses an LLM to extract structured fields from unstructured claim text, then applies a deterministic rule engine to decide the outcome.

## Data Flow

Untrusted claimant-supplied text (narratives, doctor notes, receipts) enters the agent context directly. The LLM reads and interprets this content. Extracted fields (claim amount, diagnosis code, date of loss) feed a rule engine. The rule engine emits exactly one terminal outcome to a local result boundary.

## Infrastructure

Deployed locally on-premises. No external API calls, no network egress beyond the local result write. No retrieval augmentation — all domain rules are compiled into the deterministic rule engine, not retrieved at runtime. Single agent; no inter-agent communication. The agent does not spawn sub-agents or delegate to external services.

## Risk Surface

The primary risk is that malicious claimants embed instruction-shaped text in claim narratives to redirect agent behavior (prompt injection). A secondary risk is that the LLM may hallucinate claim values (misinformation) or leak claim data in intermediate reasoning steps (sensitive information disclosure). The system runs under a least-privilege harness: tools are phase-gated and a deny-list blocks destructive commands. Human sign-off is required before any phase transition.
