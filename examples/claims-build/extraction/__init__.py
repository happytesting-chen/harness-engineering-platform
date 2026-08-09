"""Build C — LLM extraction front-end for the deterministic claims core.

The LLM (or, here, a FakeExtractor) turns raw email text into a *proposed* claim
record. That proposal is UNTRUSTED: it flows through the unchanged
``claims.validate -> normalize -> route`` pipeline, and the coverage amount is
overridden from a trusted policy lookup — never taken from the email. The
extractor proposes; ``claims.router`` disposes.

Stub build: no boto3, no network, no credentials, no egress. The real
BedrockExtractor is declared but intentionally not wired (see extraction.model).
"""
