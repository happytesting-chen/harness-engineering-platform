# Code Review Orchestrator (Multi-Agent)

## Product Overview

CodeSentinel is a multi-agent system that performs automated security and quality review of pull requests. An orchestrator agent receives a PR diff, decomposes the review into subtasks (dependency scan, SAST analysis, secret detection), and dispatches those subtasks to three specialized worker agents over an internal message bus. Workers return structured findings; the orchestrator synthesizes a final review report posted to the PR.

## Data Flow

Incoming PR diffs (untrusted developer-authored code) arrive at the orchestrator agent. The orchestrator serializes subtask payloads and posts them to a message queue (RabbitMQ). Worker agents consume from the queue, run their analysis, and post result messages back. The orchestrator reads worker results, merges findings, and calls the GitHub API to post the review comment. No retrieval augmentation — workers use static analysis tools only.

## Infrastructure

Four agent processes: one orchestrator + three workers (dependency-scanner, sast-runner, secret-detector). All communicate over an internal RabbitMQ message bus. The orchestrator holds the GitHub API credential; workers hold only local tool credentials. Workers are sandboxed — they cannot directly call external APIs. The orchestrator enforces a timeout on worker responses; if a worker exceeds the timeout, the orchestrator marks that subtask as inconclusive and continues.

## Risk Surface

Inter-agent communication over the message bus is the dominant risk: a compromised or hijacked worker could inject malicious content into the orchestrator context (ASI07 — insecure inter-agent communication). The orchestrator trusts worker result payloads; if those payloads are manipulated, the synthesized review may be incorrect or misleading. The PR diff itself is untrusted user content and may contain prompt injection attempts targeting the orchestrator's LLM reasoning step. Supply-chain risk exists in the worker tool dependencies (SAST tool, dependency scanner). Cascading failures are possible if a worker crash causes the orchestrator to stall or skip findings (ASI08). The orchestrator holds a privileged GitHub credential that workers must not access.
