"""The isolated review surface (Task 6). The reviewer is a target — render accordingly.

Quarantined content is attacker-authored, and this is the one place a human reads it.
The rendering rules are therefore security controls, not formatting taste:

- **No ANSI**: every C0/C1 control character except newline and tab is replaced with a
  visible ``·`` — an escape sequence cannot rewrite the reviewer's terminal.
- **No markup**: ``<`` becomes ``‹`` so nothing pasted into a browser or rich viewer
  executes.
- **No model rationale**: the preview shows detector IDs and digests, never any
  model-authored prose about the content — attacker framing does not get laundered
  through a summary.
- **No live links**: URLs render inside the escaped block like all other text; the CLI
  offers nothing clickable.

Issuing a receipt requires the reviewer to confirm the exact content digest they saw.
The receipt references the digest; it never carries the content.
"""
import argparse
import json
import secrets
import sys
from pathlib import Path

from .ingress import QuarantineStore
from .review import ContentReviewRequest, issue_content_receipt
from .contracts import Origin

_ALLOWED_WHITESPACE = {"\n", "\t"}


def _neutralize(text: str) -> str:
    out = []
    for ch in text:
        if ch == "<":
            out.append("‹")
        elif ch in _ALLOWED_WHITESPACE:
            out.append(ch)
        elif ord(ch) < 0x20 or 0x7F <= ord(ch) <= 0x9F:
            out.append("·")
        else:
            out.append(ch)
    return "".join(out)


def build_review_request(store: QuarantineStore, quarantine_id: str, *,
                         reviewer_id: str, policy_sha256: str, rule_version: str,
                         classifier_sha256: str, ttl_seconds: int = 300) -> ContentReviewRequest:
    """Look up a quarantine record by opaque ID and bind a review request to its
    exact digest and the detection context in force. Unknown IDs raise KeyError."""
    record = store.get(quarantine_id)  # KeyError for unknown id, deliberately
    return ContentReviewRequest(
        content_sha256=record.raw_sha256,
        origin=Origin(record.origin),
        policy_sha256=policy_sha256,
        rule_version=rule_version,
        classifier_sha256=classifier_sha256,
        reviewer_id=reviewer_id,
        ttl_seconds=ttl_seconds,
        nonce=secrets.token_hex(16),
        quarantine_id=quarantine_id,
    )


def render_review_request(request: ContentReviewRequest, store: QuarantineStore) -> str:
    record = store.get(request.quarantine_id)
    lines = [
        "QUARANTINED CONTENT REVIEW",
        f"quarantine_id : {record.quarantine_id}",
        f"origin        : {record.origin}",
        f"source        : {record.source}",
        f"content_sha256: {record.raw_sha256}",
        f"withheld for  : {', '.join(record.reasons)}",
        "",
        "-- content (neutralized plain text; nothing below is clickable or live) --",
        _neutralize(record.text),
        "-- end of content --",
        "",
        "Releasing approves EXACTLY this digest, once, under the current policy.",
        "It does not approve any action the content asks for.",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Isolated content-review CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="render one quarantine record for review")
    show.add_argument("quarantine_id")
    show.add_argument("--store-dir", required=True, type=Path)

    issue = sub.add_parser("issue", help="issue a single-use release receipt")
    issue.add_argument("quarantine_id")
    issue.add_argument("--store-dir", required=True, type=Path)
    issue.add_argument("--reviewer", required=True)
    issue.add_argument("--confirm-digest", required=True,
                       help="the exact content_sha256 shown by `show`")
    issue.add_argument("--key-file", required=True, type=Path,
                       help="host-owned receipt master key (bytes); never agent-visible config")
    issue.add_argument("--context-file", required=True, type=Path,
                       help="JSON with policy_sha256, rule_version, classifier_sha256")
    issue.add_argument("--ttl-seconds", type=int, default=300)

    args = parser.parse_args(argv)
    store = _load_store(args.store_dir)

    if args.command == "show":
        record = store.get(args.quarantine_id)
        request = ContentReviewRequest(
            content_sha256=record.raw_sha256, origin=Origin(record.origin),
            policy_sha256="0" * 64, rule_version="-", classifier_sha256="0" * 64,
            reviewer_id="-", ttl_seconds=300, nonce="preview",
            quarantine_id=args.quarantine_id,
        )
        sys.stdout.write(render_review_request(request, store) + "\n")
        return 0

    record = store.get(args.quarantine_id)
    if args.confirm_digest != record.raw_sha256:
        print("REFUSED: confirmed digest does not match the quarantined content", file=sys.stderr)
        return 1
    context = json.loads(args.context_file.read_text(encoding="utf-8"))
    request = build_review_request(
        store, args.quarantine_id, reviewer_id=args.reviewer,
        policy_sha256=context["policy_sha256"], rule_version=context["rule_version"],
        classifier_sha256=context["classifier_sha256"], ttl_seconds=args.ttl_seconds,
    )
    import time
    receipt = issue_content_receipt(request, args.key_file.read_bytes(), now=int(time.time()))
    sys.stdout.write(json.dumps(vars(receipt) | {"origin": receipt.origin.value},
                                sort_keys=True) + "\n")
    return 0


def _load_store(store_dir: Path) -> QuarantineStore:
    """Rehydrate a directory of quarantine records (one JSON file per record) into a
    store. The host owns writing these; the CLI only reads them."""
    store = QuarantineStore()
    for path in sorted(store_dir.glob("q-*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        from .ingress import QuarantineRecord
        record = QuarantineRecord(**raw)
        with store._lock:
            store._records[record.quarantine_id] = record
    return store


if __name__ == "__main__":
    raise SystemExit(main())
