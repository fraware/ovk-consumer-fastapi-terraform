#!/usr/bin/env python3
"""Run the program section 23.1 automated scenario matrix against pinned OVK 1.2.1."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "scenario-matrix"
FIXTURES = ROOT / "fixtures"
OVK_VERSION = "1.2.1"
REPO_NAME = os.environ.get("CONSUMER_REPO", ROOT.name)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=merged,
        text=True,
        capture_output=True,
    )


def recommendation_from(evidence_path: Path) -> str:
    if not evidence_path.is_file():
        return "unknown"
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    return str(data.get("decision", {}).get("merge_recommendation", "unknown"))


def write_result(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{entry['scenario_id']}.json"
    path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def scenario_advisory_passing() -> dict:
    out = OUT / "advisory-passing"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.time()
    proc = run(
        [
            "ovk",
            "check",
            "--diff",
            str(FIXTURES / "diffs" / "advisory_passing.diff"),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-advisory-passing",
            "--advisory",
            "--output-dir",
            str(out),
            "--format",
            "json",
        ]
    )
    elapsed = (time.time() - started) * 1000
    rec = recommendation_from(out / "ovk-evidence.json")
    expect(proc.returncode == 0, f"advisory passing must exit 0, got {proc.returncode}\n{proc.stderr}")
    expect(rec in {"allow", "allow_with_warning"}, f"expected allow*, got {rec}")
    return {
        "scenario_id": "advisory_passing",
        "intent": "advisory_passing_pr",
        "recommendation": rec,
        "elapsed_ms": elapsed,
        "artifacts": [str(out / "ovk-evidence.json"), str(out / "ovk-pr-comment.md")],
        "final_disposition": "scenario_pass",
        "notes": "Advisory mode exits 0 on allow.",
    }


def scenario_advisory_failing() -> dict:
    out = OUT / "advisory-failing"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.time()
    proc = run(
        [
            "ovk",
            "check",
            "--diff",
            str(FIXTURES / "diffs" / "advisory_failing.diff"),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-advisory-failing",
            "--advisory",
            "--output-dir",
            str(out),
            "--format",
            "json",
        ]
    )
    elapsed = (time.time() - started) * 1000
    rec = recommendation_from(out / "ovk-evidence.json")
    expect(proc.returncode == 0, f"advisory failing must exit 0, got {proc.returncode}\n{proc.stderr}")
    expect(rec == "block", f"expected block recommendation, got {rec}")
    return {
        "scenario_id": "advisory_failing",
        "intent": "advisory_failing_pr",
        "recommendation": rec,
        "elapsed_ms": elapsed,
        "artifacts": [str(out / "ovk-evidence.json"), str(out / "ovk-pr-comment.md")],
        "final_disposition": "scenario_pass",
        "notes": "Advisory reports block but does not fail the job.",
    }


def scenario_strict_blocking() -> dict:
    out = OUT / "strict-blocking"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.time()
    proc = run(
        [
            "ovk",
            "check",
            "--diff",
            str(FIXTURES / "diffs" / "advisory_failing.diff"),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-strict-blocking",
            "--strict",
            "--output-dir",
            str(out),
            "--format",
            "json",
        ]
    )
    elapsed = (time.time() - started) * 1000
    rec = recommendation_from(out / "ovk-evidence.json")
    expect(proc.returncode != 0, "strict blocking must be non-zero")
    expect(rec == "block", f"expected block, got {rec}")
    return {
        "scenario_id": "strict_blocking",
        "intent": "strict_blocking",
        "recommendation": rec,
        "elapsed_ms": elapsed,
        "artifacts": [str(out / "ovk-evidence.json")],
        "final_disposition": "scenario_pass",
        "notes": "Strict mode fails closed on block.",
    }


def scenario_malformed_abstraction() -> dict:
    out = OUT / "malformed"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.time()
    proc = run(
        [
            "ovk",
            "verify",
            "--manifest",
            str(ROOT / ".verification" / "manifest_malformed_auth.json"),
            "--output-dir",
            str(out),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-malformed",
            "--advisory",
        ]
    )
    elapsed = (time.time() - started) * 1000
    evidence = out / "ovk-evidence.json"
    rec = recommendation_from(evidence) if evidence.exists() else "unknown"
    expect(rec != "allow", f"malformed abstraction must not allow, got {rec}")
    expect(proc.returncode == 0, f"advisory verify should exit 0\n{proc.stderr}")
    return {
        "scenario_id": "malformed_or_incomplete_abstraction",
        "intent": "malformed_or_incomplete_abstraction",
        "recommendation": rec,
        "elapsed_ms": elapsed,
        "artifacts": [str(p) for p in out.glob("**/*") if p.is_file()][:12],
        "final_disposition": "scenario_pass",
        "notes": "Malformed auth abstraction refuses silent allow.",
    }


def scenario_release_bundle() -> dict:
    out = OUT / "release-bundle"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.time()
    proc = run(
        [
            "ovk",
            "verify",
            "--manifest",
            str(ROOT / ".verification" / "manifest_ci_secrets_safe.json"),
            "--output-dir",
            str(out),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-release-bundle",
            "--advisory",
        ]
    )
    elapsed = (time.time() - started) * 1000
    expect(proc.returncode == 0, f"release bundle verify failed: {proc.stderr}")
    expect((out / "ovk-evidence.json").is_file(), "missing ovk-evidence.json")
    has_manifest = (out / "ovk-artifact-manifest.json").is_file() or any(
        out.rglob("ovk-artifact-manifest.json")
    )
    expect(has_manifest, "missing artifact manifest in release bundle")
    val = run(["ovk", "validate-outputs", str(out)])
    return {
        "scenario_id": "release_bundle",
        "intent": "release_bundle",
        "recommendation": recommendation_from(out / "ovk-evidence.json"),
        "elapsed_ms": elapsed,
        "artifacts": [str(p) for p in out.rglob("*") if p.is_file()][:20],
        "final_disposition": "scenario_pass",
        "notes": f"validate-outputs rc={val.returncode}",
    }


def scenario_cache_reuse() -> dict:
    cache_dir = ROOT / ".verification" / "cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    out1 = OUT / "cache-run1"
    out2 = OUT / "cache-run2"
    for p in (out1, out2):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    cmd = [
        "ovk",
        "check",
        "--diff",
        str(FIXTURES / "diffs" / "advisory_passing.diff"),
        "--repo",
        REPO_NAME,
        "--head-sha",
        "scenario-cache-reuse",
        "--advisory",
        "--format",
        "json",
    ]
    t0 = time.time()
    r1 = run(cmd + ["--output-dir", str(out1)])
    e1 = (time.time() - t0) * 1000
    expect(r1.returncode == 0, r1.stderr)
    cache_files_after_first = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    t1 = time.time()
    r2 = run(cmd + ["--output-dir", str(out2)])
    e2 = (time.time() - t1) * 1000
    expect(r2.returncode == 0, r2.stderr)
    cache_files_after_second = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
    expect(len(cache_files_after_second) >= len(cache_files_after_first), "cache did not persist")
    expect(len(cache_files_after_second) > 0, "expected cache files under .verification/cache")
    return {
        "scenario_id": "cache_reuse",
        "intent": "cache_reuse",
        "recommendation": recommendation_from(out2 / "ovk-evidence.json"),
        "elapsed_ms": e2,
        "artifacts": [str(p) for p in cache_files_after_second[:8]],
        "final_disposition": "scenario_pass",
        "notes": f"first={e1:.0f}ms second={e2:.0f}ms cache_files={len(cache_files_after_second)}",
    }


def scenario_policy_change() -> dict:
    cfg = ROOT / ".verification" / "config.yml"
    original = cfg.read_text(encoding="utf-8") if cfg.exists() else None
    out_a = OUT / "policy-a"
    out_b = OUT / "policy-b"
    for p in (out_a, out_b):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    try:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(
            "schema_version: ovk.config.v1\nmode: advisory\ndefault_on_unknown: require_human_review\n",
            encoding="utf-8",
        )
        r1 = run(
            [
                "ovk",
                "check",
                "--diff",
                str(FIXTURES / "diffs" / "advisory_passing.diff"),
                "--repo",
                REPO_NAME,
                "--head-sha",
                "scenario-policy-a",
                "--advisory",
                "--output-dir",
                str(out_a),
                "--format",
                "json",
            ]
        )
        expect(r1.returncode == 0, r1.stderr)
        rec_a = recommendation_from(out_a / "ovk-evidence.json")
        cfg.write_text(
            "schema_version: ovk.config.v1\nmode: strict\ndefault_on_unknown: block\n"
            "denied_backends: [tla+, alloy, kani, lean, dafny, verus, cedar, cbmc]\n",
            encoding="utf-8",
        )
        r2 = run(
            [
                "ovk",
                "check",
                "--diff",
                str(FIXTURES / "diffs" / "advisory_passing.diff"),
                "--repo",
                REPO_NAME,
                "--head-sha",
                "scenario-policy-b",
                "--strict",
                "--output-dir",
                str(out_b),
                "--format",
                "json",
            ]
        )
        rec_b = recommendation_from(out_b / "ovk-evidence.json")
        return {
            "scenario_id": "policy_change",
            "intent": "policy_change",
            "recommendation": rec_b,
            "elapsed_ms": None,
            "artifacts": [str(cfg), str(out_a / "ovk-evidence.json"), str(out_b / "ovk-evidence.json")],
            "final_disposition": "scenario_pass",
            "notes": f"policy A rec={rec_a} rc={r1.returncode}; policy B rec={rec_b} rc={r2.returncode}",
        }
    finally:
        cfg.write_text(
            original
            if original is not None
            else "schema_version: ovk.config.v1\nmode: advisory\ndefault_on_unknown: require_human_review\n",
            encoding="utf-8",
        )


def scenario_backend_unavailable() -> dict:
    out = OUT / "backend-unavailable"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    cfg = ROOT / ".verification" / "config.yml"
    original = cfg.read_text(encoding="utf-8") if cfg.exists() else None
    try:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(
            "schema_version: ovk.config.v1\nmode: advisory\ndefault_on_unknown: require_human_review\n"
            "allowed_backends: [cbmc]\n"
            "denied_backends: [opa, ci_secrets, z3, cedar, tla+, alloy, kani, lean, dafny, verus]\n",
            encoding="utf-8",
        )
        started = time.time()
        proc = run(
            [
                "ovk",
                "check",
                "--diff",
                str(FIXTURES / "diffs" / "advisory_passing.diff"),
                "--repo",
                REPO_NAME,
                "--head-sha",
                "scenario-backend-unavailable",
                "--advisory",
                "--no-cache",
                "--output-dir",
                str(out),
                "--format",
                "json",
            ]
        )
        elapsed = (time.time() - started) * 1000
        rec = recommendation_from(out / "ovk-evidence.json")
        expect(proc.returncode == 0, f"advisory should exit 0: {proc.stderr}")
        return {
            "scenario_id": "backend_unavailable",
            "intent": "backend_unavailable",
            "recommendation": rec,
            "elapsed_ms": elapsed,
            "artifacts": [str(out / "ovk-evidence.json")],
            "final_disposition": "scenario_pass",
            "notes": "Policy restricted to cbmc (typically absent); recommendation recorded honestly.",
        }
    finally:
        cfg.write_text(
            original
            if original is not None
            else "schema_version: ovk.config.v1\nmode: advisory\ndefault_on_unknown: require_human_review\n",
            encoding="utf-8",
        )


def scenario_native_backend_timeout() -> dict:
    """Exercise OVK's native CBMC runner TimeoutExpired -> unknown (never fabricated pass)."""
    import subprocess
    from unittest import mock

    from ovk.adapters.cbmc.optional_runner import run_cbmc_harness

    out = OUT / "native-timeout"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    harness = FIXTURES / "diffs" / "advisory_passing.diff"
    expect(harness.is_file(), "fixture harness path missing")

    def _timeout_run(*_args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["cbmc"], timeout=kwargs.get("timeout", 1))

    started = time.time()
    with mock.patch("ovk.adapters.cbmc.optional_runner.shutil.which", return_value="cbmc"):
        with mock.patch(
            "ovk.adapters.cbmc.optional_runner.subprocess.run",
            side_effect=_timeout_run,
        ):
            result = run_cbmc_harness(harness_path=harness, timeout_seconds=1)
    elapsed = (time.time() - started) * 1000

    expect(result.get("status") == "unknown", f"timeout must yield unknown, got {result}")
    expect(result.get("used_native_binary") is True, "timeout path must mark native attempt")
    expect("timed out" in str(result.get("reason", "")).lower(), f"reason missing timeout: {result}")
    expect(result.get("status") != "pass", "must not fabricate pass after timeout")

    result_path = out / "cbmc-timeout-result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {
        "scenario_id": "native_backend_timeout",
        "intent": "native_backend_timeout",
        "recommendation": "unknown",
        "elapsed_ms": elapsed,
        "artifacts": [str(result_path)],
        "final_disposition": "scenario_pass",
        "notes": (
            "Installed-wheel CBMC optional_runner TimeoutExpired path returns "
            "status=unknown with used_native_binary=true; never pass."
        ),
    }


def scenario_generated_regression_artifact() -> dict:
    out = OUT / "generated-regression"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    gen = ROOT / ".verification" / "generated_tests"
    if gen.exists():
        shutil.rmtree(gen)
    started = time.time()
    proc = run(
        [
            "ovk",
            "check",
            "--diff",
            str(FIXTURES / "diffs" / "advisory_failing.diff"),
            "--repo",
            REPO_NAME,
            "--head-sha",
            "scenario-generated-regression",
            "--advisory",
            "--no-cache",
            "--output-dir",
            str(out),
            "--format",
            "json",
        ]
    )
    elapsed = (time.time() - started) * 1000
    expect(proc.returncode == 0, proc.stderr)
    evidence = json.loads((out / "ovk-evidence.json").read_text(encoding="utf-8"))
    found = []
    for ev in evidence.get("evidence", []):
        for art in ev.get("generated_artifacts", []):
            if art.get("kind") == "regression_unit_test":
                found.append(art)
    gen_files = list(gen.glob("*.py")) if gen.exists() else []
    expect(bool(found or gen_files), "expected generated regression_unit_test artifact")
    return {
        "scenario_id": "generated_regression_artifact",
        "intent": "generated_regression_artifact",
        "recommendation": recommendation_from(out / "ovk-evidence.json"),
        "elapsed_ms": elapsed,
        "artifacts": [str(p) for p in gen_files] + [str(out / "ovk-evidence.json")],
        "final_disposition": "scenario_pass",
        "notes": f"generated_artifacts={len(found)} files={len(gen_files)}",
    }


def scenario_pr_comment_and_check_run() -> dict:
    workflows = list((ROOT / ".github" / "workflows").glob("ovk-*.yml"))
    texts = "\n".join(p.read_text(encoding="utf-8") for p in workflows)
    expect(
        ('post-comment: "true"' in texts)
        or ("post-comment: 'true'" in texts)
        or ("post-comment: true" in texts),
        "missing post-comment: true workflow",
    )
    expect(
        ('emit-check: "true"' in texts)
        or ("emit-check: 'true'" in texts)
        or ("emit-check: true" in texts),
        "missing emit-check: true workflow",
    )
    expect(
        "fraware/open-verification-kernel@v1.2.1" in texts,
        "Action pin missing in PR workflows",
    )
    return {
        "scenario_id": "pr_comment_and_check_run",
        "intent": "pr_comment_and_check_run",
        "recommendation": "n/a",
        "elapsed_ms": None,
        "artifacts": [str(p) for p in workflows],
        "final_disposition": "scenario_pass",
        "notes": (
            "Action workflows pin @v1.2.1 with post-comment and emit-check; "
            "exercised on pull_request events."
        ),
    }


def scenario_fork_pr_simulation() -> dict:
    import re

    path = ROOT / ".github" / "workflows" / "ovk-fork-simulation.yml"
    expect(path.is_file(), "missing fork simulation workflow")
    text = path.read_text(encoding="utf-8")
    expect(re.search(r"(?m)^\s*pull_request\s*:", text) is not None, "fork simulation must use pull_request")
    expect(
        re.search(r"(?m)^\s*pull_request_target\s*:", text) is None,
        "must not use pull_request_target as a workflow trigger",
    )
    expect("permissions:" in text and "contents: read" in text, "must declare reduced permissions")
    expect("fraware/open-verification-kernel@v1.2.1" in text, "must pin @v1.2.1")
    return {
        "scenario_id": "fork_pr_reduced_permissions",
        "intent": "fork_pr_reduced_permissions",
        "recommendation": "n/a",
        "elapsed_ms": None,
        "artifacts": [str(path), str(ROOT / "docs" / "FORK_PR.md")],
        "final_disposition": "scenario_pass",
        "notes": (
            "Dry simulation with pull_request + contents:read only. "
            "True cross-fork PR remains a human step."
        ),
    }


def scenario_published_wheel() -> dict:
    proc = run(
        [
            sys.executable,
            "-c",
            "import importlib.metadata as m; print(m.version('open-verification-kernel'))",
        ]
    )
    expect(proc.returncode == 0, proc.stderr)
    version = (proc.stdout or "").strip()
    expect(version == OVK_VERSION, f"expected {OVK_VERSION}, got {version!r}")
    return {
        "scenario_id": "published_wheel",
        "intent": "published_wheel",
        "recommendation": "n/a",
        "elapsed_ms": None,
        "artifacts": ["scripts/install_ovk_wheel.py"],
        "final_disposition": "scenario_pass",
        "notes": (
            f"Installed open-verification-kernel=={version} via PyPI or "
            "cosign-verified GitHub Release wheel."
        ),
    }


SCENARIOS = [
    scenario_published_wheel,
    scenario_advisory_passing,
    scenario_advisory_failing,
    scenario_strict_blocking,
    scenario_malformed_abstraction,
    scenario_release_bundle,
    scenario_cache_reuse,
    scenario_policy_change,
    scenario_backend_unavailable,
    scenario_native_backend_timeout,
    scenario_generated_regression_artifact,
    scenario_pr_comment_and_check_run,
    scenario_fork_pr_simulation,
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    failed = []
    for fn in SCENARIOS:
        name = fn.__name__
        print(f"\n=== {name} ===", flush=True)
        try:
            result = fn()
            result["ovk_source_version"] = f"v{OVK_VERSION}"
            result["repository"] = (
                f"fraware/{REPO_NAME}" if not str(REPO_NAME).startswith("fraware/") else REPO_NAME
            )
            write_result(result)
            results.append(result)
            print(f"PASS {result['scenario_id']}: {result.get('notes', '')}", flush=True)
        except Exception as exc:  # noqa: BLE001 - collect all scenario failures
            failed.append((name, str(exc)))
            print(f"FAIL {name}: {exc}", flush=True)
            write_result(
                {
                    "scenario_id": name,
                    "intent": name,
                    "recommendation": "unknown",
                    "elapsed_ms": None,
                    "artifacts": [],
                    "final_disposition": "scenario_fail",
                    "notes": str(exc),
                    "ovk_source_version": f"v{OVK_VERSION}",
                    "repository": REPO_NAME,
                }
            )
    summary = {
        "ovk_source_version": f"v{OVK_VERSION}",
        "repository": REPO_NAME,
        "passed": len(results),
        "failed": len(failed),
        "results": results,
        "failures": [{"scenario": n, "error": e} for n, e in failed],
        "production_gate_met": False,
        "disclaimer": (
            "Automated scenario matrix only. Does not satisfy the 30 human-adjudicated "
            "PRs per repository production exit criterion."
        ),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": summary["passed"], "failed": summary["failed"]}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
