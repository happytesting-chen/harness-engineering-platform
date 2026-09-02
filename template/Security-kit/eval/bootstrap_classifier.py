#!/usr/bin/env python3
"""Rebuild the pinned semantic classifier on this machine — fail closed at every step.

Why this exists. The classifier is deliberately not shipped (700 MB, and a hosted one is a
startup error), and the signed lock names its artifacts by absolute path on the operator's
machine. This script gives another machine the same classifier, proven the same way:

  1. a venv from the committed `requirements.lock.txt` (every version ==pinned);
  2. the model and tokenizer downloaded from the source named in
     `classifier-source.json`, each verified by SHA-256 and size BEFORE anything runs —
     a mismatch deletes the file and stops;
  3. the tracked wrapper installed with this venv's interpreter on its shebang line — its
     body must hash to the digest recorded beside the benchmark;
  4. the committed benchmark re-run against the local artifacts and compared with the
     committed result, summary figures AND every per-case verdict — any drift stops;
  5. an UNSIGNED lock written with local paths. `sign` is a separate, deliberate human step.

What it never does: modify `Security-kit/runtime/` (the verdict's C-5 artifacts), sign on
the human's behalf, or write into a path git would track.

Usage:
  python3 Security-kit/eval/bootstrap_classifier.py bootstrap [--root DIR] [--offline]
  python3 Security-kit/eval/bootstrap_classifier.py sign --approved-by you@example.org [--root DIR]

Stdlib only. The only non-stdlib code involved runs inside the venv this script creates.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_TEMPLATE = Path(__file__).resolve().parents[2]          # …/template
_EVAL = Path(__file__).resolve().parent
_DEFAULT_SOURCE = _EVAL / "classifier-source.json"
_DEFAULT_ROOT = _TEMPLATE.parent / ".classifier-candidates"
_UNSIGNED = "semantic-model.lock.unsigned.json"
_SIGNED = "semantic-model.lock.json"
_LOCAL_MANIFEST = "candidate-manifest.local.json"
_WRAPPER = "wrapper.py"
_CHUNK = 1 << 20


class BootstrapError(Exception):
    """Any condition under which continuing would be unsafe. Always fatal."""


# --- pure helpers -----------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: Path, sha256: str, size: int) -> None:
    if not path.is_file():
        raise BootstrapError(f"{path.name}: missing")
    actual_size = path.stat().st_size
    if actual_size != size:
        raise BootstrapError(f"{path.name}: size {actual_size} != expected {size}")
    actual = sha256_file(path)
    if actual != sha256:
        raise BootstrapError(f"{path.name}: sha256 {actual[:12]}… != expected {sha256[:12]}…")


def wrapper_body_sha256(text: str) -> str:
    """Digest of everything after the shebang line — the part that must never drift."""
    body = text.split("\n", 1)[1] if "\n" in text else ""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def render_wrapper(tracked_text: str, python_path) -> str:
    if not tracked_text.startswith("#!"):
        raise BootstrapError("tracked wrapper must begin with a shebang line")
    body = tracked_text.split("\n", 1)[1]
    return f"#!{python_path}\n{body}"


def macos_keychain_roots() -> list:
    """PEM exports of the macOS keychains — the CAs curl and pip trust that OpenSSL's bundle
    lacks (a TLS-inspecting corporate proxy lives here). Empty on other platforms."""
    if platform.system() != "Darwin" or shutil.which("security") is None:
        return []
    out = []
    for chain in ("/System/Library/Keychains/SystemRootCertificates.keychain",
                  "/Library/Keychains/System.keychain"):
        proc = subprocess.run(["security", "find-certificate", "-a", "-p", chain],
                              capture_output=True, text=True)
        if proc.returncode == 0 and "BEGIN CERTIFICATE" in proc.stdout:
            tmp = Path(tempfile.gettempdir()) / f"bootstrap-classifier-{Path(chain).stem}.pem"
            tmp.write_text(proc.stdout, encoding="utf-8")
            out.append(tmp)
    return out


def build_ssl_context(*, ca_bundle: Path | None, extra_roots: list | None = None) -> ssl.SSLContext:
    """Verification is never disabled. An explicit bundle replaces the defaults; extra roots
    are added on top of them; anything unloadable is skipped, never trusted."""
    if ca_bundle is not None:
        if not Path(ca_bundle).is_file():
            raise BootstrapError(f"CA bundle not found: {ca_bundle}")
        ctx = ssl.create_default_context(cafile=str(ca_bundle))
    else:
        ctx = ssl.create_default_context()          # honours SSL_CERT_FILE / SSL_CERT_DIR
        for pem in (extra_roots if extra_roots is not None else macos_keychain_roots()):
            try:
                ctx.load_verify_locations(cafile=str(pem))
            except (ssl.SSLError, OSError):
                continue
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def fetch_file(url: str, dest: Path, sha256: str, size: int, *, opener=urllib.request.urlopen,
               offline: bool = False) -> str:
    """Reuse a verified local copy; otherwise download to `.part`, verify, rename.
    A file that fails verification is deleted — nothing unverified stays on disk."""
    if dest.is_file():
        try:
            verify_file(dest, sha256, size)
            return "reused"
        except BootstrapError:
            dest.unlink()                       # a stale or tampered copy is not reused
    if offline:
        raise BootstrapError(f"{dest.name}: not present and --offline forbids downloading")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        with opener(url) as resp, open(part, "wb") as out:
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
        verify_file(part, sha256, size)
    except Exception as exc:
        if part.exists():
            part.unlink()
        if isinstance(exc, BootstrapError):
            raise
        raise BootstrapError(f"{dest.name}: download failed: {exc}") from exc
    os.replace(part, dest)
    return "downloaded"


def compare_result(actual: dict, reference: dict, fields) -> list:
    """Every summary field and every per-case verdict must match. Missing is drift."""
    diffs = []
    for f in fields:
        if actual.get(f) != reference.get(f):
            diffs.append(f"{f}: local {actual.get(f)!r} != reference {reference.get(f)!r}")
    ref_cases = {c["id"]: c.get("combined") for c in reference.get("cases", [])}
    act_cases = {c["id"]: c.get("combined") for c in actual.get("cases", [])}
    for cid, verdict in ref_cases.items():
        if cid not in act_cases:
            diffs.append(f"case {cid}: missing from local result")
        elif act_cases[cid] != verdict:
            diffs.append(f"case {cid}: local {act_cases[cid]!r} != reference {verdict!r}")
    for cid in act_cases.keys() - ref_cases.keys():
        diffs.append(f"case {cid}: not in reference")
    return diffs


def build_unsigned_lock(*, executable_path, executable_sha256, model_path, model_sha256,
                        corpus_sha256, confidence_floor) -> dict:
    return {
        "schema_version": 1,
        "protocol_version": 1,
        "executable_path": str(executable_path),
        "executable_sha256": executable_sha256,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "corpus_sha256": corpus_sha256,
        "confidence_floor": confidence_floor,
        "approved_by": "",
        "approved_date": "",
    }


def sign_lock(unsigned: dict, *, approved_by: str, approved_date: str, current_digests: dict) -> dict:
    """Fill the approval fields — only if the artifacts still hash as the unsigned lock says."""
    if not (approved_by or "").strip() or not (approved_date or "").strip():
        raise BootstrapError("signing needs an approver identity and a date")
    for name in ("executable_sha256", "model_sha256", "corpus_sha256"):
        if current_digests.get(name) != unsigned.get(name):
            raise BootstrapError(f"{name} drifted since bootstrap — re-run bootstrap, do not sign")
    return dict(unsigned, approved_by=approved_by.strip(), approved_date=approved_date.strip())


# --- side-effecting steps (injectable) -----------------------------------------------------

def _default_create_venv(root: Path) -> Path:
    venv = root / "venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    if not python.exists():
        raise BootstrapError(f"venv created but no interpreter at {python}")
    return python


def _default_pip_install(python: Path, lock: Path) -> None:
    probe = subprocess.run([str(python), "-c", "import onnxruntime, tokenizers, numpy"],
                           capture_output=True)
    if probe.returncode == 0:
        return                                  # already provisioned from the same lock
    cmd = [str(python), "-m", "pip", "install", "--quiet", "-r", str(lock)]
    if _lock_has_hashes(lock):
        cmd.insert(4, "--require-hashes")      # a lock that carries hashes must be enforced
    subprocess.run(cmd, check=True)
    probe = subprocess.run([str(python), "-c", "import onnxruntime, tokenizers, numpy"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise BootstrapError(f"venv provisioned but imports fail: {probe.stderr.strip()[:200]}")


def _lock_has_hashes(lock: Path) -> bool:
    return "--hash=" in lock.read_text(encoding="utf-8")


_CA_BUNDLE: Path | None = None      # set by the CLI's --ca-bundle


def _default_fetch(url, dest, sha256, size, offline) -> str:
    ctx = build_ssl_context(ca_bundle=_CA_BUNDLE)
    return fetch_file(url, dest, sha256, size, offline=offline,
                      opener=lambda u: urllib.request.urlopen(u, context=ctx, timeout=120))


def _default_benchmark(manifest_path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(_EVAL / "eval_runtime_injection.py"),
                           "--candidate-manifest", str(manifest_path), "--output", str(out_dir)],
                          cwd=_TEMPLATE, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BootstrapError(f"benchmark failed: {(proc.stdout + proc.stderr).strip()[-400:]}")
    results = sorted(out_dir.glob("*.result.json"))
    if len(results) != 1:
        raise BootstrapError(f"benchmark wrote {len(results)} result files in {out_dir}, expected 1")
    return json.loads(results[0].read_text(encoding="utf-8"))


def _default_corpus_sha256() -> str:
    sys.path.insert(0, str(_EVAL))
    import eval_runtime_injection  # noqa: E402  — same directory, stdlib-only module
    return eval_runtime_injection.corpus_sha256()


def _default_check_ignored(root: Path) -> None:
    """Refuse a root that git would track: 700 MB must never enter history again."""
    probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root.parent
                           if root.parent.exists() else Path.cwd(), capture_output=True, text=True)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return                                  # not in a git work tree: nothing to protect
    root.mkdir(parents=True, exist_ok=True)
    ignored = subprocess.run(["git", "check-ignore", "-q", str(root / "probe.bin")],
                             cwd=root.parent, capture_output=True)
    if ignored.returncode != 0:
        raise BootstrapError(f"{root} is not git-ignored — add it to .gitignore first")


@dataclass
class Steps:
    create_venv: object = _default_create_venv
    pip_install: object = _default_pip_install
    fetch: object = _default_fetch
    benchmark: object = _default_benchmark
    corpus_sha256: object = _default_corpus_sha256
    check_ignored: object = _default_check_ignored


@dataclass(frozen=True)
class BootstrapConfig:
    repo_root: Path                 # what the source manifest's relative paths are relative to
    root: Path                      # where artifacts, venv and locks live (must be git-ignored)
    source: dict
    offline: bool = False


@dataclass
class BootstrapReport:
    ok: bool
    problems: list = field(default_factory=list)
    steps_done: list = field(default_factory=list)
    unsigned_lock: Path | None = None


# --- orchestration --------------------------------------------------------------------------

def run_bootstrap(cfg: BootstrapConfig, steps: Steps | None = None) -> BootstrapReport:
    steps = steps or Steps()
    report = BootstrapReport(ok=False)
    src = cfg.source
    root = Path(cfg.root).resolve()
    try:
        need = tuple(src.get("environment", {}).get("python_min", (3, 10)))
        if sys.version_info[:2] < need:
            raise BootstrapError(f"python {sys.version_info[0]}.{sys.version_info[1]} < required {need[0]}.{need[1]}")
        # the tracked wrapper must be the benchmarked one, before anything else is touched
        tracked = (Path(cfg.repo_root) / src["wrapper"]["tracked"]).read_text(encoding="utf-8")
        if wrapper_body_sha256(tracked) != src["wrapper"]["body_sha256"]:
            raise BootstrapError("tracked wrapper body does not match classifier-source.json — "
                                 "the wrapper was edited after the benchmark; re-benchmark and re-pin")
        report.steps_done.append("wrapper-digest")
        steps.check_ignored(root)
        root.mkdir(parents=True, exist_ok=True)

        python = Path(steps.create_venv(root))
        report.steps_done.append("venv")
        steps.pip_install(python, Path(cfg.repo_root) / src["environment"]["requirements_lock"])
        report.steps_done.append("pip")

        base = src["source"]["base_url"]
        for f in src["files"]:
            dest = root / f["local"]
            status = steps.fetch(base + f["remote"], dest, f["sha256"], f["size"], cfg.offline)
            verify_file(dest, f["sha256"], f["size"])       # trust nothing a step returned
            report.steps_done.append(f"{f['local']}:{status}")

        wrapper_path = root / _WRAPPER
        wrapper_path.write_text(render_wrapper(tracked, python), encoding="utf-8")
        wrapper_path.chmod(0o755)
        model = next(root / f["local"] for f in src["files"] if f["local"].endswith("model.onnx"))
        manifest = {
            "name": src["candidate"],
            "executable_path": str(wrapper_path),
            "executable_sha256": sha256_file(wrapper_path),
            "model_path": str(model),
            "model_sha256": sha256_file(model),
            "timeout_ms": src["classifier"]["timeout_ms"],
            "confidence_floor": src["classifier"]["confidence_floor"],
            "notes": f"bootstrapped locally by bootstrap_classifier.py on {_dt.date.today().isoformat()}",
        }
        manifest_path = root / _LOCAL_MANIFEST
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        report.steps_done.append("manifest")

        out_dir = root / "benchmark" / _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
        actual = steps.benchmark(manifest_path, out_dir)
        reference = json.loads((Path(cfg.repo_root) / src["reference_result"]).read_text(encoding="utf-8"))
        diffs = compare_result(actual, reference, src["compare_fields"])
        if diffs:
            raise BootstrapError("benchmark differs from the committed reference: " + "; ".join(diffs))
        report.steps_done.append("benchmark")

        lock = build_unsigned_lock(
            executable_path=wrapper_path, executable_sha256=manifest["executable_sha256"],
            model_path=model, model_sha256=manifest["model_sha256"],
            corpus_sha256=steps.corpus_sha256(), confidence_floor=src["classifier"]["confidence_floor"],
        )
        unsigned = root / _UNSIGNED
        unsigned.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        report.unsigned_lock = unsigned
        report.ok = True
    except BootstrapError as exc:
        report.problems.append(str(exc))
    except Exception as exc:                    # a step blew up: still fail closed, still say why
        report.problems.append(f"{type(exc).__name__}: {exc}")
    return report


def run_sign(root: Path, approved_by: str, approved_date: str, steps: Steps | None = None) -> BootstrapReport:
    steps = steps or Steps()
    report = BootstrapReport(ok=False)
    root = Path(root).resolve()
    try:
        if not (approved_by or "").strip():
            raise BootstrapError("--approved-by is required: a lock is signed by a named human")
        unsigned_path = root / _UNSIGNED
        if not unsigned_path.is_file():
            raise BootstrapError(f"no {_UNSIGNED} in {root} — run bootstrap first")
        signed_path = root / _SIGNED
        if signed_path.exists():
            raise BootstrapError(f"{signed_path} already exists — delete it deliberately before re-signing")
        unsigned = json.loads(unsigned_path.read_text(encoding="utf-8"))
        current = {
            "executable_sha256": sha256_file(Path(unsigned["executable_path"])),
            "model_sha256": sha256_file(Path(unsigned["model_path"])),
            "corpus_sha256": steps.corpus_sha256(),
        }
        signed = sign_lock(unsigned, approved_by=approved_by, approved_date=approved_date, current_digests=current)
        signed_path.write_text(json.dumps(signed, indent=2) + "\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(_EVAL / "eval_runtime_injection.py"),
                               "--lock", str(signed_path), "--verify"],
                              cwd=_TEMPLATE, capture_output=True, text=True)
        if proc.returncode != 0:
            signed_path.unlink()
            raise BootstrapError(f"signed lock failed verification and was removed: {proc.stdout.strip()[-300:]}")
        report.unsigned_lock = signed_path
        report.ok = True
    except BootstrapError as exc:
        report.problems.append(str(exc))
    except Exception as exc:
        report.problems.append(f"{type(exc).__name__}: {exc}")
    return report


# --- CLI --------------------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bootstrap", help="venv + verified download + benchmark + unsigned lock")
    b.add_argument("--root", type=Path, default=_DEFAULT_ROOT)
    b.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
    b.add_argument("--offline", action="store_true", help="never download; fail if a file is missing")
    b.add_argument("--ca-bundle", type=Path, default=None,
                   help="PEM bundle to trust instead of the defaults (TLS-inspecting networks); "
                        "SSL_CERT_FILE is honoured too; verification is never disabled")
    s = sub.add_parser("sign", help="fill the approval fields of the unsigned lock — a human step")
    s.add_argument("--root", type=Path, default=_DEFAULT_ROOT)
    s.add_argument("--approved-by", default="")
    s.add_argument("--date", default=_dt.date.today().isoformat())
    args = parser.parse_args(argv)

    if args.cmd == "bootstrap":
        global _CA_BUNDLE
        _CA_BUNDLE = args.ca_bundle
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
        report = run_bootstrap(BootstrapConfig(repo_root=_TEMPLATE, root=args.root, source=source,
                                               offline=args.offline))
        for step in report.steps_done:
            print(f"  ok  {step}")
        if report.ok:
            print(f"BOOTSTRAPPED — unsigned lock: {report.unsigned_lock}")
            print("Next: a human runs  sign --approved-by <you>  after reading the benchmark output above.")
            return 0
    else:
        report = run_sign(args.root, args.approved_by, args.date)
        if report.ok:
            print(f"SIGNED and verified: {report.unsigned_lock}")
            return 0
    for p in report.problems:
        print(f"STOP: {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
