"""The owned single-agent runtime host (Task 11). The assembly, not a new control.

Fixed loop order, and the host is the only thing that knows it:

    startup validation
      → prompt ingress (①)
      → model proposal            (the model is the CALLER's — this host has no LLM)
      → guarded tool action (② ③) — session ceilings, origin rules, inner gates
      → tool-result ingress (④)
      → buffered final output
    audited throughout, hash-chained

Assembly rules the tests pin:
- Nothing unapproved is ever appended to `messages`: allowed text goes in verbatim,
  withheld content is replaced by OUR notice, and there is no third case.
- The model-facing surface is strings only — `messages` rows are `{"role","content"}`;
  no control object, policy, key or store is reachable from it.
- Turn taint is accumulated from what actually entered context: an admitted
  EXTERNAL_CONTENT result taints the turn, and the origin rules at the action gate
  read that taint — which is what stops the classifier-false-negative case (R-1) at
  the sink even after the text got in.
"""
import io
from dataclasses import dataclass, field

from .adapters import ingress_tool_result, ingress_user_prompt
from .audit import AuditPolicy, AuditRecorder
from .contracts import IngressOutcome, Origin
from .guarded import GuardedDispatcher
from .ingress import IngressPolicy, QuarantineStore
from .output import BufferedSender, OutputPolicy, screen_output
from .review import NonceStore, ReceiptVerifier
from .session import SessionPolicy, SessionState
from .startup import RuntimeConfig, StartupReport, validate_startup


class _ListSink:
    """Default audit sink: in-memory lines. A deployment passes a FileAuditSink."""

    def __init__(self):
        self.lines = []

    def append(self, line: str) -> None:
        self.lines.append(line)


@dataclass(frozen=True)
class HostConfig:
    tools: dict
    policy_tools: tuple
    session_policy: SessionPolicy
    classifier: object
    output_policy: OutputPolicy
    transport: object
    receipt_key: bytes
    ingress_policy: IngressPolicy = field(default_factory=IngressPolicy)
    audit_sink: object = None
    audit_policy: AuditPolicy = field(
        default_factory=lambda: AuditPolicy(failure_policy="deny", max_bytes=10_000_000)
    )
    policy_sha256: str = "0" * 64
    classifier_sha256: str = "0" * 64
    control_root: object = "."
    production: bool = False
    memory_enabled: bool = False
    delegation_enabled: bool = False
    streaming_output: bool = False
    run_id: str = "run-local"
    session_id: str = "session-local"


@dataclass(frozen=True)
class HostResult:
    outcome: IngressOutcome
    notice: str | None = None


class RuntimeHost:
    def __init__(self, config: HostConfig):
        # startup validation FIRST — a disabled capability dies before any wiring
        self.startup_report: StartupReport = validate_startup(RuntimeConfig(
            production=config.production,
            memory_enabled=config.memory_enabled,
            delegation_enabled=config.delegation_enabled,
            streaming_output=config.streaming_output,
            tools=config.tools,
            policy_tools=config.policy_tools,
            control_root=config.control_root,
            receipt_key=config.receipt_key,
            audit_failure_policy=config.audit_policy.failure_policy,
            audit_max_bytes=config.audit_policy.max_bytes,
            semantic_enabled=False,   # the classifier instance arrives lock-verified
            classifier_lock_path=None,
        ))
        self._config = config
        self._classifier = config.classifier
        self._ingress_policy = config.ingress_policy
        self.quarantine = QuarantineStore()
        self._verifier = ReceiptVerifier(
            master_key=config.receipt_key,
            nonce_store=NonceStore(),
            policy_sha256=config.policy_sha256,
            rule_version=config.ingress_policy.rules.version,
            classifier_sha256=config.classifier_sha256,
        )
        # the action plane: the existing dispatcher, composed — never re-implemented
        from runtime_dispatcher import RuntimeDispatcher  # resolved via governance/ on sys.path
        self._dispatcher = GuardedDispatcher(
            inner=RuntimeDispatcher(dict(config.tools)),
            policy=config.session_policy,
            state=SessionState(),
            verifier=self._verifier if config.session_policy.require_approval else None,
        )
        self._audit = AuditRecorder(
            sink=config.audit_sink if config.audit_sink is not None else _ListSink(),
            policy=config.audit_policy,
            run_id=config.run_id,
            session_id=config.session_id,
        )
        self.audit_records = []
        self.messages = []          # strings only — the model-facing surface
        self._origins = set()       # taint accumulated from ADMITTED content
        self._sender = BufferedSender(config.transport, config.output_policy)
        self.transport = config.transport
        self.last_ingress = None

    # -- audit helper ------------------------------------------------------------
    def _record(self, event_type: str, *, content_sha256=None, action_sha256=None,
                decision: str = "", receipt_ref=None):
        record = self._audit.record({
            "event_type": event_type,
            "content_sha256": content_sha256,
            "action_sha256": action_sha256,
            "rule_version": self._ingress_policy.rules.version,
            "classifier_sha256": self._config.classifier_sha256,
            "policy_sha256": self._config.policy_sha256,
            "decision": decision,
            "receipt_ref": receipt_ref,
        })
        self.audit_records.append(record)
        return record

    # -- the loop ----------------------------------------------------------------
    def submit_prompt(self, text) -> HostResult:
        result = ingress_user_prompt(
            text, classifier=self._classifier, policy=self._ingress_policy,
            quarantine=self.quarantine,
        )
        self.last_ingress = result.decision
        self._record("INGRESS_PROMPT",
                     content_sha256=result.decision.raw_sha256,
                     decision=result.outcome.value)
        if result.outcome is IngressOutcome.ALLOW:
            self.messages.append({"role": "user", "content": result.context_text})
            self._origins.add(Origin.USER_DIRECT)
            return HostResult(outcome=result.outcome)
        notice = ("[prompt withheld] The request was withheld before reaching the "
                  "model; a reviewer can release it by exact digest.")
        return HostResult(outcome=result.outcome, notice=notice)

    def deliver_tool_result(self, tool: str, result) -> HostResult:
        outcome = ingress_tool_result(
            result, tool, classifier=self._classifier, policy=self._ingress_policy,
            quarantine=self.quarantine,
        )
        self.last_ingress = outcome.decision
        self._record("INGRESS_TOOL_RESULT",
                     content_sha256=outcome.decision.raw_sha256,
                     decision=outcome.outcome.value)
        if outcome.outcome is IngressOutcome.ALLOW:
            self.messages.append({"role": "tool", "content": outcome.context_text})
            self._origins.add(Origin.EXTERNAL_CONTENT)
            return HostResult(outcome=outcome.outcome)
        self.messages.append({"role": "tool", "content": outcome.notice})
        return HostResult(outcome=outcome.outcome, notice=outcome.notice)

    def invoke_tool(self, name: str, args: dict | None = None, *, approval=None, now: int = 0):
        from .review import action_sha256
        digest = action_sha256(name, dict(args or {}))
        try:
            result = self._dispatcher.execute(
                name, args, origins=frozenset(self._origins),
                approval=approval, now=now,
            )
        except BaseException as exc:
            self._record("ACTION", action_sha256=digest,
                         decision=f"DENY:{type(exc).__name__}")
            raise
        self._record("ACTION", action_sha256=digest, decision="ALLOW",
                     receipt_ref=getattr(approval, "nonce", None))
        return result

    def finish(self, text: str):
        self._sender.prepare(text)
        decision = self._sender.release()
        self._record("OUTPUT", decision=f"RELEASED:{decision.redactions}-redactions")
        return decision
