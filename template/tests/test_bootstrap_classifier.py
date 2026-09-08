"""Bootstrap the pinned semantic classifier on another machine — fail closed at every step.

The signed lock names artifacts by absolute path on the operator's machine, and the
classifier is deliberately not shipped. `Security-kit/eval/bootstrap_classifier.py`
rebuilds the same classifier locally: pinned venv, digest-verified download, the committed
benchmark re-run and compared, then an UNSIGNED lock a human signs deliberately.

Nothing here touches `Security-kit/runtime/` (C-5). These tests use fakes for the network,
the venv and the benchmark; the real end-to-end run is recorded in progress.md.
"""
import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_KIT = _ROOT / "Security-kit"
sys.path.insert(0, str(_KIT))
sys.path.insert(0, str(_KIT / "eval"))

import bootstrap_classifier as bc  # noqa: E402

_SOURCE = json.loads((_KIT / "eval" / "classifier-source.json").read_text())
_LOCK = json.loads((_KIT / "runtime" / "semantic-model.lock.json").read_text())


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --- the module itself -----------------------------------------------------------------

def test_bootstrap_module_is_stdlib_only():
    tree = ast.parse((_KIT / "eval" / "bootstrap_classifier.py").read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    third_party = names - set(sys.stdlib_module_names) - {"eval_runtime_injection"}
    assert not third_party, f"non-stdlib imports: {sorted(third_party)}"


# --- the source manifest cannot drift from what was benchmarked and signed --------------

def test_source_pins_the_same_model_as_the_signed_lock_and_candidate_manifest():
    model = next(f for f in _SOURCE["files"] if f["local"].endswith("model.onnx"))
    assert model["sha256"] == _LOCK["model_sha256"]
    # Select the manifest belonging to the PINNED candidate by name, never by glob order.
    # This assertion used to take the first glob hit, which was correct only while exactly
    # one candidate manifest existed. Adding candidates 02/03 broke it on Linux and not on
    # macOS, because glob order is filesystem-dependent — it passed locally and failed CI.
    manifest_dir = _ROOT / "evaluation/runtime-security/candidate-manifests"
    matching = [json.loads(p.read_text()) for p in sorted(manifest_dir.glob("*.json"))
                if json.loads(p.read_text()).get("name") == _SOURCE["candidate"]]
    assert len(matching) == 1, (
        f"expected exactly one manifest named {_SOURCE['candidate']!r}, found {len(matching)}"
    )
    assert model["sha256"] == matching[0]["model_sha256"]
    assert _SOURCE["classifier"]["confidence_floor"] == _LOCK["confidence_floor"]


def test_source_wrapper_body_digest_matches_the_tracked_wrapper():
    text = (_ROOT / _SOURCE["wrapper"]["tracked"]).read_text()
    assert text.startswith("#!"), "tracked wrapper must start with a shebang line to be rewritten"
    assert bc.wrapper_body_sha256(text) == _SOURCE["wrapper"]["body_sha256"]


def test_source_reference_result_exists_and_carries_every_compare_field():
    ref = json.loads((_ROOT / _SOURCE["reference_result"]).read_text())
    for field in _SOURCE["compare_fields"]:
        assert field in ref, f"reference result lacks {field}"
    assert ref["model_sha256"] == _LOCK["model_sha256"]
    assert isinstance(ref["cases"], list) and ref["cases"], "reference must carry per-case verdicts"


def test_source_requirements_lock_exists_and_is_fully_pinned():
    lines = [l.strip() for l in (_ROOT / _SOURCE["environment"]["requirements_lock"]).read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    assert lines and all("==" in l for l in lines), "every requirement must be ==pinned"


# --- pure helpers --------------------------------------------------------------------

def test_render_wrapper_replaces_only_the_shebang():
    tracked = "#!/usr/bin/env python3\nimport x\nprint(1)\n"
    out = bc.render_wrapper(tracked, "/opt/venv/bin/python")
    assert out.splitlines()[0] == "#!/opt/venv/bin/python"
    assert out.split("\n", 1)[1] == tracked.split("\n", 1)[1]
    assert bc.wrapper_body_sha256(out) == bc.wrapper_body_sha256(tracked)


def test_fetch_reuses_a_valid_existing_file_without_touching_the_network():
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "a.bin"; dest.write_bytes(b"hello")
        def opener(url):
            raise AssertionError("network must not be used for a valid existing file")
        status = bc.fetch_file("https://x/a", dest, _sha(b"hello"), 5, opener=opener)
        assert status == "reused"


def test_fetch_rejects_a_digest_mismatch_and_leaves_no_file_behind():
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "a.bin"
        class R:
            def __init__(self): self.data = b"HELLO"   # same length as "hello": exercises the digest check, not the size check
            def read(self, n=-1):
                d, self.data = self.data, b""; return d
            def __enter__(self): return self
            def __exit__(self, *a): return False
        try:
            bc.fetch_file("https://x/a", dest, _sha(b"hello"), 5, opener=lambda url: R())
            assert False, "must raise on digest mismatch"
        except bc.BootstrapError as exc:
            assert "sha256" in str(exc), f"expected a digest failure, got: {exc}"
        assert not dest.exists() and not list(Path(tmp).iterdir()), "no partial or tampered file may remain"


def test_fetch_offline_refuses_to_download_a_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            bc.fetch_file("https://x/a", Path(tmp) / "a.bin", _sha(b"x"), 1, opener=None, offline=True)
            assert False
        except bc.BootstrapError as exc:
            assert "offline" in str(exc)


def test_ssl_context_always_verifies_and_loads_an_explicit_bundle():
    import ssl
    bundle = Path(ssl.get_default_verify_paths().cafile or ssl.get_default_verify_paths().openssl_cafile or "")
    ctx = bc.build_ssl_context(ca_bundle=bundle if bundle.is_file() else None, extra_roots=[])
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    try:
        bc.build_ssl_context(ca_bundle=Path("/nonexistent/ca.pem"), extra_roots=[])
        assert False
    except bc.BootstrapError as exc:
        assert "ca" in str(exc).lower()


def test_ssl_context_adds_extra_roots_without_dropping_verification():
    import ssl
    pem = ("-----BEGIN CERTIFICATE-----\nMIIB" + "A" * 40 + "\n-----END CERTIFICATE-----\n")
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "roots.pem"; bad.write_text(pem)   # malformed on purpose
        ctx = bc.build_ssl_context(ca_bundle=None, extra_roots=[bad])   # unloadable extras are skipped, not fatal
        assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_compare_result_flags_summary_and_per_case_drift():
    ref = {"attacks_caught_combined": 14, "attacks_total": 16,
           "cases": [{"id": "atk-001", "combined": "REQUIRE_REVIEW"}, {"id": "leg-001", "combined": "ALLOW"}]}
    same = json.loads(json.dumps(ref))
    assert bc.compare_result(same, ref, ["attacks_caught_combined", "attacks_total"]) == []
    drift = json.loads(json.dumps(ref)); drift["attacks_caught_combined"] = 13
    drift["cases"][1]["combined"] = "REQUIRE_REVIEW"
    diffs = bc.compare_result(drift, ref, ["attacks_caught_combined", "attacks_total"])
    assert any("attacks_caught_combined" in d for d in diffs)
    assert any("leg-001" in d for d in diffs)
    missing = json.loads(json.dumps(ref)); missing["cases"] = missing["cases"][:1]
    assert bc.compare_result(missing, ref, []), "a missing case is drift, not a pass"


def test_unsigned_lock_has_local_absolute_paths_and_no_approval():
    lock = bc.build_unsigned_lock(executable_path="/m/wrapper.py", executable_sha256="e" * 64,
                                  model_path="/m/model.onnx", model_sha256="m" * 64,
                                  corpus_sha256="c" * 64, confidence_floor=0.75)
    assert set(lock) == set(_LOCK), "unsigned lock must carry exactly the signed lock's fields"
    assert lock["approved_by"] == "" and lock["approved_date"] == ""
    assert lock["schema_version"] == 1 and lock["protocol_version"] == 1


def test_sign_refuses_an_empty_approver_and_refuses_on_artifact_drift():
    unsigned = bc.build_unsigned_lock(executable_path="/m/w", executable_sha256="e" * 64,
                                      model_path="/m/m", model_sha256="m" * 64,
                                      corpus_sha256="c" * 64, confidence_floor=0.75)
    digests_ok = {"executable_sha256": "e" * 64, "model_sha256": "m" * 64, "corpus_sha256": "c" * 64}
    for approver in ("", "   "):
        try:
            bc.sign_lock(unsigned, approved_by=approver, approved_date="2026-09-02", current_digests=digests_ok)
            assert False
        except bc.BootstrapError as exc:
            assert "approv" in str(exc)
    drifted = dict(digests_ok, model_sha256="x" * 64)
    try:
        bc.sign_lock(unsigned, approved_by="a@b", approved_date="2026-09-02", current_digests=drifted)
        assert False
    except bc.BootstrapError as exc:
        assert "model_sha256" in str(exc)


def test_signed_lock_is_accepted_by_the_runtime_loader():
    from runtime.classifier import load_lock
    with tempfile.TemporaryDirectory() as tmp:
        unsigned = bc.build_unsigned_lock(executable_path=str(Path(tmp) / "w"), executable_sha256="e" * 64,
                                          model_path=str(Path(tmp) / "m"), model_sha256="m" * 64,
                                          corpus_sha256="c" * 64, confidence_floor=0.75)
        signed = bc.sign_lock(unsigned, approved_by="a@b", approved_date="2026-09-02",
                              current_digests={"executable_sha256": "e" * 64, "model_sha256": "m" * 64, "corpus_sha256": "c" * 64})
        p = Path(tmp) / "lock.json"; p.write_text(json.dumps(signed))
        lock = load_lock(p)
        assert lock.approved_by == "a@b" and lock.model_sha256 == "m" * 64


# --- orchestration with fakes ----------------------------------------------------------

def _tiny_source(tmp: Path, model: bytes, tok: bytes):
    ref = {"attacks_caught_combined": 1, "attacks_total": 1, "cases": [{"id": "atk-001", "combined": "REQUIRE_REVIEW"}]}
    (tmp / "ref.json").write_text(json.dumps(ref))
    tracked = tmp / "wrapper.py"; tracked.write_text("#!/usr/bin/env python3\nprint('w')\n")
    (tmp / "req.txt").write_text("onnxruntime==1.29.0\n")
    return {
        "candidate": "cand", "source": {"base_url": "https://x/"},
        "files": [{"remote": "m.onnx", "local": "cand/model.onnx", "sha256": _sha(model), "size": len(model)},
                  {"remote": "t.json", "local": "cand/tokenizer.json", "sha256": _sha(tok), "size": len(tok)}],
        "wrapper": {"tracked": "wrapper.py", "body_sha256": bc.wrapper_body_sha256(tracked.read_text())},
        "environment": {"requirements_lock": "req.txt", "python_min": [3, 10]},
        "classifier": {"confidence_floor": 0.75, "timeout_ms": 1000, "protocol_version": 1},
        "reference_result": "ref.json", "compare_fields": ["attacks_caught_combined", "attacks_total"],
    }, ref


def _fake_steps(model: bytes, tok: bytes, benchmark_result):
    calls = []
    def create_venv(root):
        calls.append("venv"); (root / "venv/bin").mkdir(parents=True, exist_ok=True)
        py = root / "venv/bin/python"; py.write_text(""); return py
    def pip_install(python, lock): calls.append(("pip", lock.name))
    def fetch(url, dest, sha, size, offline):
        calls.append(("fetch", url)); dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(model if dest.name.endswith(".onnx") else tok); return "downloaded"
    def benchmark(manifest_path, out_dir):
        calls.append("benchmark"); return json.loads(json.dumps(benchmark_result))
    return bc.Steps(create_venv=create_venv, pip_install=pip_install, fetch=fetch,
                    benchmark=benchmark, corpus_sha256=lambda: "c" * 64), calls


def test_run_bootstrap_happy_path_writes_unsigned_lock_candidate_manifest_and_wrapper():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); model, tok = b"MODEL", b"TOK"
        source, ref = _tiny_source(tmp, model, tok)
        steps, calls = _fake_steps(model, tok, ref)
        root = tmp / ".classifier-candidates"
        report = bc.run_bootstrap(bc.BootstrapConfig(repo_root=tmp, root=root, source=source, offline=False), steps)
        assert report.ok, report.problems
        lock = json.loads((root / "semantic-model.lock.unsigned.json").read_text())
        assert Path(lock["model_path"]).is_absolute() and lock["model_sha256"] == _sha(model)
        assert lock["approved_by"] == "", "bootstrap must never sign"
        wrapper = (root / "wrapper.py").read_text()
        assert wrapper.splitlines()[0] == f"#!{root.resolve() / 'venv/bin/python'}", "lock paths are canonical (resolved)"
        assert lock["executable_sha256"] == _sha(wrapper.encode())
        manifest = json.loads((root / "candidate-manifest.local.json").read_text())
        assert manifest["model_sha256"] == _sha(model) and manifest["confidence_floor"] == 0.75
        assert calls[0] == "venv" and "benchmark" in calls and any(c[0] == "fetch" for c in calls if isinstance(c, tuple))


def test_run_bootstrap_stops_on_benchmark_drift_and_writes_no_lock():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); model, tok = b"MODEL", b"TOK"
        source, ref = _tiny_source(tmp, model, tok)
        drifted = json.loads(json.dumps(ref)); drifted["cases"][0]["combined"] = "ALLOW"; drifted["attacks_caught_combined"] = 0
        steps, _ = _fake_steps(model, tok, drifted)
        root = tmp / ".classifier-candidates"
        report = bc.run_bootstrap(bc.BootstrapConfig(repo_root=tmp, root=root, source=source, offline=False), steps)
        assert not report.ok and any("atk-001" in p for p in report.problems)
        assert not (root / "semantic-model.lock.unsigned.json").exists()


def test_run_bootstrap_stops_when_tracked_wrapper_body_drifts_from_the_source_digest():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); model, tok = b"MODEL", b"TOK"
        source, ref = _tiny_source(tmp, model, tok)
        (tmp / "wrapper.py").write_text("#!/usr/bin/env python3\nprint('edited')\n")
        steps, calls = _fake_steps(model, tok, ref)
        report = bc.run_bootstrap(bc.BootstrapConfig(repo_root=tmp, root=tmp / "r", source=source, offline=False), steps)
        assert not report.ok and any("wrapper" in p for p in report.problems)
        assert "benchmark" not in calls, "must stop before running anything with a drifted wrapper"


def test_run_bootstrap_stops_when_a_fetched_file_fails_verification():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); model, tok = b"MODEL", b"TOK"
        source, ref = _tiny_source(tmp, model, tok)
        steps, calls = _fake_steps(b"WRONG", tok, ref)   # fetch writes the wrong bytes
        report = bc.run_bootstrap(bc.BootstrapConfig(repo_root=tmp, root=tmp / "r", source=source, offline=False), steps)
        assert not report.ok and any("model.onnx" in p for p in report.problems)
        assert "benchmark" not in calls


def test_cli_sign_requires_an_approver():
    rc = bc.main(["sign", "--root", tempfile.gettempdir()])
    assert rc != 0


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1; print(f"FAIL {name}: {exc}")
        print(f"Results: {len(tests) - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
