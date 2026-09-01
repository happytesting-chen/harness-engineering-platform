"""Session state and policy: the sequence-plane rules (Task 8, AD-7).

This module holds exactly what the per-call gate cannot: memory across calls. Ceilings
are enforced with reserve → commit / rollback under one lock, so two concurrent calls
against a remaining budget of one admit exactly one — the reservation is taken before
the tool runs and released only if the tool fails.

Deliberately absent (AD-7): any predicate the inner gate already owns. No command
patterns, no host rules, no allowlist membership — those live in the governance gate
this layer wraps, and a copy here would be a copy that drifts.
"""
import threading
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionPolicy:
    """Committed per-session rules. All optional; an empty policy adds nothing."""

    max_calls: dict = field(default_factory=dict)        # tool -> per-session ceiling
    total_max_calls: int | None = None                   # across all tools
    origin_rules: dict = field(default_factory=dict)     # tool -> frozenset of allowed Origins
    arg_schemas: dict = field(default_factory=dict)      # tool -> {arg_name: type}

    def __post_init__(self):
        for tool, ceiling in self.max_calls.items():
            if ceiling < 0:
                raise ValueError(f"ceiling for {tool} must be non-negative")
        if self.total_max_calls is not None and self.total_max_calls < 0:
            raise ValueError("total_max_calls must be non-negative")


class SessionState:
    """Reserve/commit/rollback call accounting, atomic under one lock."""

    def __init__(self):
        self._lock = threading.Lock()
        self._committed = {}   # tool -> count
        self._reserved = {}    # tool -> count

    def _in_flight(self, tool: str) -> int:
        return self._committed.get(tool, 0) + self._reserved.get(tool, 0)

    def _total_in_flight(self) -> int:
        return sum(self._committed.values()) + sum(self._reserved.values())

    def reserve(self, tool: str, policy: SessionPolicy) -> bool:
        """Take one slot of budget if every applicable ceiling still holds. The check
        counts committed AND reserved calls, so a concurrent racer sees the slot as
        taken the instant this returns True."""
        with self._lock:
            ceiling = policy.max_calls.get(tool)
            if ceiling is not None and self._in_flight(tool) >= ceiling:
                return False
            if (policy.total_max_calls is not None
                    and self._total_in_flight() >= policy.total_max_calls):
                return False
            self._reserved[tool] = self._reserved.get(tool, 0) + 1
            return True

    def commit(self, tool: str) -> None:
        with self._lock:
            self._reserved[tool] -= 1
            self._committed[tool] = self._committed.get(tool, 0) + 1

    def rollback(self, tool: str) -> None:
        """A failed or denied call must not consume the session's budget."""
        with self._lock:
            self._reserved[tool] -= 1
