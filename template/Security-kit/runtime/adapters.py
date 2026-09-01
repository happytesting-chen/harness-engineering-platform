"""runtime-mvp entry points: prompts, tool results, structured records (Task 7).

These are the functions a deployed application calls; `Task 11`'s host calls nothing
else. Each converts host input into a `ContentEnvelope` and runs the strict pipeline
(`evaluate_ingress`), so there is exactly one place the decision table lives.

Profile boundary, stated plainly (R-3 and the plan's Task 7 deviation record):

- The **IDE hook screens** (the ① and ④ adapters wired in `.claude/settings.json`)
  stay regex-only and keep their documented fail-open on malformed envelopes. That
  behavior is confined to the IDE profile; this module does not import them and must
  not (test-pinned by scanning this file's source for their module names).
- The regex-only deployed screen module (a protected path, unedited by this task)
  remains available for applications that do not adopt the classifier.
- **This module is the semantic tier** — the runtime-mvp profile's front door. The plan
  originally said to route the deployed screen module itself through the pipeline; that
  file is a protected path, so the semantic entry points live here instead, beside the
  pipeline they call. One package, one decision table, no second copy of anything.

Malformed input fails TOWARD review: a non-string prompt or tool result yields
`REQUIRE_REVIEW` with `context_text=None`. It never raises toward the caller and never
passes annotated — "unscannable" and "clean" must not share a value.
"""
import hashlib
from dataclasses import dataclass

from .contracts import ContentEnvelope, IngressDecision, IngressOutcome, Origin
from .ingress import IngressPolicy, evaluate_ingress

_DEFAULT_POLICY = IngressPolicy()


@dataclass(frozen=True)
class AdapterResult:
    """What the application gets back. `context_text` is the ONLY field ever appended
    to model context: the original text on ALLOW, None on withhold — there is no
    annotated or partially-screened variant."""

    outcome: IngressOutcome
    context_text: str | None
    decision: IngressDecision | None
    notice: str | None = None


def _malformed(kind: str, value) -> AdapterResult:
    decision = IngressDecision(
        outcome=IngressOutcome.REQUIRE_REVIEW,
        content_id=f"malformed-{kind}",
        raw_sha256=hashlib.sha256(repr(type(value)).encode()).hexdigest(),
        reasons=(f"envelope:malformed:{type(value).__name__}",),
    )
    return AdapterResult(outcome=IngressOutcome.REQUIRE_REVIEW,
                         context_text=None, decision=decision)


def _envelope(text: str, *, origin: Origin, source: str, prefix: str) -> ContentEnvelope:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ContentEnvelope(
        content_id=f"{prefix}-{digest[:12]}",
        text=text,
        origin=origin,
        source=source,
        media_type="text/plain",
        raw_sha256=digest,
    )


def _run(text, *, origin, source, prefix, classifier, policy, quarantine, receipts, now):
    if not isinstance(text, str):
        return _malformed(prefix, text)
    decision = evaluate_ingress(
        _envelope(text, origin=origin, source=source, prefix=prefix),
        policy=policy or _DEFAULT_POLICY, classifier=classifier,
        quarantine=quarantine, receipts=receipts, now=now,
    )
    allowed = decision.outcome is IngressOutcome.ALLOW
    return AdapterResult(
        outcome=decision.outcome,
        context_text=text if allowed else None,
        decision=decision,
    )


def ingress_user_prompt(text, *, classifier, policy=None, quarantine=None,
                        receipts=None, source="request", now=0) -> AdapterResult:
    """Gate ① for the runtime-mvp profile: screen a user request before the model."""
    return _run(text, origin=Origin.USER_DIRECT, source=source, prefix="user",
                classifier=classifier, policy=policy, quarantine=quarantine,
                receipts=receipts, now=now)


def ingress_tool_result(result, tool: str, *, classifier, policy=None,
                        quarantine=None, receipts=None, now=0) -> AdapterResult:
    """Gate ④ for the runtime-mvp profile: screen tool output before the model reads
    it. On withhold, `notice` carries our-words text the application may surface in
    place of the result — it names the tool and the fact of withholding, and never
    quotes the content."""
    outcome = _run(result, origin=Origin.EXTERNAL_CONTENT, source=tool, prefix="tool",
                   classifier=classifier, policy=policy, quarantine=quarantine,
                   receipts=receipts, now=now)
    if outcome.outcome is IngressOutcome.ALLOW:
        return outcome
    notice = (
        f"[tool result withheld] The call to {tool} succeeded, but its output was "
        f"withheld before reaching the model"
        + (f" (quarantine {outcome.decision.quarantine_id})"
           if getattr(outcome.decision, "quarantine_id", None) else "")
        + ". A reviewer can release it by exact digest."
    )
    return AdapterResult(outcome=outcome.outcome, context_text=None,
                         decision=outcome.decision, notice=notice)


def ingress_structured_record(record: dict, *, allowed_fields, classifier,
                              policy=None, quarantine=None, receipts=None,
                              now=0) -> tuple:
    """Structured-record ingress: drop every non-allowlisted field FIRST (authority
    fields never even reach a screen), then run each allowed text field through the
    pipeline as its own envelope. Returns `(filtered_record, results_by_field)`;
    a withheld field is present in the filtered record as None."""
    allowed = tuple(allowed_fields)
    filtered, results = {}, {}
    for field_name in allowed:
        if field_name not in record:
            continue
        value = record[field_name]
        if not isinstance(value, str):
            filtered[field_name] = value  # numbers/bools carry no instruction text
            continue
        outcome = _run(value, origin=Origin.EXTERNAL_CONTENT,
                       source=f"record:{field_name}", prefix="field",
                       classifier=classifier, policy=policy, quarantine=quarantine,
                       receipts=receipts, now=now)
        results[field_name] = outcome
        filtered[field_name] = value if outcome.outcome is IngressOutcome.ALLOW else None
    return filtered, results
