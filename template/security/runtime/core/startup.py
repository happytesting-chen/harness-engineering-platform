"""Startup isolation: an unsupported capability refuses to start (Task 9, AD-6).

Every check answers one question: *could this deployment silently be weaker than the
profile claims?* If yes, startup fails — there is no warning-only mode, because a
warning at startup is a log line nobody reads while the weaker system runs anyway.

All violations are collected and reported in ONE `StartupError`, so an operator fixes
the list rather than discovering one violation per restart. `validate_startup` is pure
inspection: it opens files read-only and never mutates anything.
"""
from dataclasses import dataclass
from pathlib import Path

from .classifier import LockError, SubprocessSemanticClassifier, load_lock

_MIN_KEY_BYTES = 16
_AUDIT_POLICIES = frozenset({"deny", "degrade-and-count"})


class StartupError(Exception):
    def __init__(self, violations: tuple):
        self.violations = violations
        super().__init__(
            "runtime-mvp refuses to start; fix all of: " + " | ".join(violations)
        )


@dataclass(frozen=True)
class StartupReport:
    violations: tuple = ()


@dataclass(frozen=True)
class RuntimeConfig:
    production: bool
    memory_enabled: bool
    delegation_enabled: bool
    streaming_output: bool
    tools: dict
    policy_tools: tuple
    control_root: Path
    receipt_key: bytes | None
    audit_failure_policy: str
    audit_max_bytes: int
    semantic_enabled: bool
    classifier_lock_path: Path | None


def validate_startup(config: RuntimeConfig) -> StartupReport:
    violations = []

    # AD-6: hard exclusions — these are new sources/sinks, not options
    if config.memory_enabled:
        violations.append("persistent memory is enabled — disabled capability in the MVP")
    if config.delegation_enabled:
        violations.append("delegation is enabled — disabled capability in the MVP")
    if config.streaming_output:
        violations.append("streaming output is enabled — final output must be buffered")

    # tool registry and policy allowlist must agree exactly, both directions
    registry, policy = set(config.tools), set(config.policy_tools)
    for name in sorted(registry - policy):
        violations.append(f"tool {name!r} is registered but not in policy")
    for name in sorted(policy - registry):
        violations.append(f"tool {name!r} is in policy but not registered")
    for name, fn in sorted(config.tools.items()):
        if not callable(fn):
            violations.append(f"tool {name!r} is not callable — every tool must be wrapped code")

    # receipt authority needs a real key
    if not isinstance(config.receipt_key, bytes) or len(config.receipt_key) < _MIN_KEY_BYTES:
        violations.append(
            f"receipt key missing or shorter than {_MIN_KEY_BYTES} bytes — "
            "review authority cannot exist without it"
        )

    # audit behaviour must be explicit and bounded
    if config.audit_failure_policy not in _AUDIT_POLICIES:
        violations.append(
            f"audit failure policy {config.audit_failure_policy!r} — "
            f"must be one of {sorted(_AUDIT_POLICIES)}"
        )
    if config.audit_max_bytes <= 0:
        violations.append("audit rotation/size limit must be positive")

    # production: the worker must not be able to rewrite its own control plane
    if config.production:
        root = Path(config.control_root)
        if not root.is_dir():
            violations.append(f"control root {root} is not a directory")
        else:
            import os
            if os.access(root, os.W_OK):
                violations.append(
                    f"control root {root} is writable by this process — "
                    "production requires a read-only control plane"
                )

    # semantic enforcement needs the human-signed lock, and the artifacts must match it
    if config.semantic_enabled:
        if config.classifier_lock_path is None:
            violations.append("semantic enforcement enabled but no classifier lock configured")
        else:
            try:
                lock = load_lock(config.classifier_lock_path)
                SubprocessSemanticClassifier(lock, timeout_ms=1000)  # verifies digests
            except LockError as exc:
                violations.append(f"classifier lock invalid: {exc}")

    if violations:
        raise StartupError(tuple(violations))
    return StartupReport(violations=())
