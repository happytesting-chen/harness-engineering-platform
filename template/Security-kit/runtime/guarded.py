"""GuardedDispatcher — the sequence/turn layer composed AROUND the action gate (Task 8).

AD-7, structurally: this class holds a reference to the existing dispatcher and calls
it. It re-implements nothing the inner gate owns — the four governance gates fire on
every call exactly as they do without this wrapper (test-pinned: a hard-blocked command
still dies at gate ② through the wrapper, and this module's source carries none of the
inner gate's predicates).

What the wrapper adds is what a stateless per-call gate cannot see:

- **Schema binding** — a call with an unknown argument or a wrong argument type is
  denied before dispatch. The inner gate judges values; this judges shape.
- **Origin rules** — the turn's content origins (from the ingress envelopes) gate
  which tools are reachable: a turn tainted by EXTERNAL_CONTENT cannot reach a tool
  whose policy says USER_DIRECT-only. This is the origin-labelling half of the A-tier,
  wired to the labels the ingress layer already carries.
- **Session ceilings** — reserve → inner dispatch → commit, rollback on ANY failure
  (inner denial included), so twenty identical calls stop at the ceiling and a crashed
  call never burns budget.

Denials raise `PermissionError` before the tool runs, matching the inner contract —
a caller that ignores return values still cannot proceed.
"""
import asyncio

from .contracts import Origin
from .session import SessionPolicy, SessionState


class GuardedDispatcher:
    def __init__(self, *, inner, policy: SessionPolicy, state: SessionState | None = None,
                 verifier=None):
        if policy.require_approval and verifier is None:
            raise ValueError(
                "policy pauses tools for approval but no receipt verifier was given — "
                "an approval tier with nothing to verify receipts is an off switch"
            )
        self._inner = inner
        self._policy = policy
        self._state = state if state is not None else SessionState()
        self._verifier = verifier

    def _check_approval(self, tool_name: str, args: dict, approval, now: int) -> None:
        """REQUIRE_APPROVAL is a PAUSE: a valid receipt lets evaluation continue —
        the reservation and every inner gate still run after this. It is never a
        bypass, so a receipt cannot convert an inner DENY into anything."""
        if tool_name not in self._policy.require_approval:
            return
        if approval is None:
            raise PermissionError(
                f"{tool_name}: this tool requires human approval — no receipt presented"
            )
        # a wrong receipt TYPE raises TypeError inside the verifier, deliberately
        if not self._verifier.verify_action(approval, _as_action(tool_name, args), now=now):
            raise PermissionError(
                f"{tool_name}: approval receipt invalid — wrong action digest, "
                f"expired, replayed, or issued under a different policy"
            )

    def _check_schema(self, tool_name: str, args: dict) -> None:
        schema = self._policy.arg_schemas.get(tool_name)
        if schema is None:
            return
        for name, value in args.items():
            if name not in schema:
                raise PermissionError(
                    f"{tool_name}: unknown argument {name!r} — the schema binds "
                    f"exactly {sorted(schema)}"
                )
            expected = schema[name]
            if not isinstance(value, expected) or isinstance(value, bool) and expected is not bool:
                raise PermissionError(
                    f"{tool_name}: argument {name!r} must be {expected.__name__}, "
                    f"got {type(value).__name__}"
                )

    def _check_origins(self, tool_name: str, origins: frozenset) -> None:
        allowed = self._policy.origin_rules.get(tool_name)
        if allowed is None:
            return
        if not isinstance(origins, frozenset) or not all(isinstance(o, Origin) for o in origins):
            raise PermissionError(f"{tool_name}: origins must be a frozenset of Origin")
        excess = origins - allowed
        if excess:
            names = ", ".join(sorted(o.value for o in excess))
            raise PermissionError(
                f"{tool_name}: this turn carries content from [{names}], and policy "
                f"allows this tool only for [{', '.join(sorted(o.value for o in allowed))}]"
            )

    def execute(self, tool_name: str, tool_input: dict | None = None, *,
                origins: frozenset = frozenset(), approval=None, now: int = 0):
        args = dict(tool_input or {})
        # turn/shape rules first — they need no budget and their denial is cheap
        self._check_origins(tool_name, origins)
        self._check_schema(tool_name, args)
        self._check_approval(tool_name, args, approval, now)
        # then the reservation, then the inner gate; rollback on ANY failure
        if not self._state.reserve(tool_name, self._policy):
            raise PermissionError(f"{tool_name}: session ceiling reached — call refused")
        try:
            result = self._inner.execute(tool_name, args)
        except BaseException:
            self._state.rollback(tool_name)
            raise
        self._state.commit(tool_name)
        return result

    async def aexecute(self, tool_name: str, tool_input: dict | None = None, *,
                       origins: frozenset = frozenset(), approval=None, now: int = 0):
        """Async variant over the same lock-guarded state — the ceiling holds across
        a `gather` exactly as it does across threads."""
        return await asyncio.to_thread(
            lambda: self.execute(tool_name, tool_input, origins=origins,
                                 approval=approval, now=now)
        )


def _as_action(tool_name: str, args: dict):
    from .contracts import Action
    return Action(name=tool_name, args=args, origins=frozenset())
