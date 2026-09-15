# Policy Q&A RAG Agent

## Product Overview

PolicySearch is a retrieval-augmented generation (RAG) agent that answers employee questions about internal HR and compliance policies. Users submit natural-language questions; the agent embeds the query into a vector representation, retrieves the top-k most similar policy document chunks from a shared vector store (pgvector), and synthesizes a final answer using an LLM.

## Data Flow

User questions enter the agent. The query is embedded and sent to the vector store. Retrieved document chunks (policy texts) are injected into the LLM context window alongside the original question. The LLM generates a synthesized answer referencing the retrieved content. Answers are returned to the user; no result is written to external systems.

## Infrastructure

The vector store is a shared pgvector database pre-populated by a separate ingestion pipeline. The agent has read-only access to the vector store. No write path exists. The agent is a single process — no sub-agents, no inter-agent messages. Retrieval is over a closed corpus (internal HR policies only); no user-supplied documents enter the index.

## Risk Surface

Retrieval introduces LLM08 risks: the vector store could be poisoned via the ingestion pipeline (embedding weakness, data poisoning at ingest), or the retrieved chunks could be manipulated to confuse the synthesizer. The LLM may also hallucinate facts not present in retrieved chunks (misinformation). The query embedding pipeline is a supply-chain dependency. User queries may contain adversarial text aimed at overriding instructions (prompt injection). Because answers reference policy documents, incorrect outputs could lead users to take incorrect compliance actions (misinformation risk LLM09). No code execution or tool calls beyond the vector store read are permitted.
