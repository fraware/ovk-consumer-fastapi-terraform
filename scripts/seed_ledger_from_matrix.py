#!/usr/bin/env python3
"""Seed pilot/ledger.json from scenario-matrix artifacts (honest automated_scenario labels)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "scenario-matrix" / "summary.json"
LEDGER = ROOT / "pilot" / "ledger.json"
SCHEMA_VERSION = "ovk.pilot_ledger.v1"


def main() -> int:
    if not SUMMARY.is_file():
        print(f"missing {SUMMARY}; run scripts/run_scenario_matrix.py first", file=sys.stderr)
        return 1
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    repo = summary.get("repository", ROOT.name)
    if not str(repo).startswith("fraware/"):
        repo = f"fraware/{repo}"
    entries = []
    for result in summary.get("results", []):
        entries.append(
            {
                "entry_id": f"auto-{result['scenario_id']}",
                "repository": repo,
                "ovk_source_version": result.get("ovk_source_version", "v1.2.1"),
                "pr_identifier": f"automated_scenario:{result['scenario_id']}",
                "intent": result.get("intent", result["scenario_id"]),
                "recommendation": result.get("recommendation", "unknown"),
                "human_adjudication": "automated_scenario",
                "false_positive": None,
                "missed_detection": None,
                "unknown_appropriateness": None,
                "reviewer_comments": result.get(
                    "notes",
                    "Seeded from automated scenario matrix; not a human adjudication.",
                ),
                "runtime": {
                    "elapsed_ms": result.get("elapsed_ms"),
                    "mode": "automated_scenario",
                    "runner": "scripts/run_scenario_matrix.py",
                },
                "artifacts": result.get("artifacts", []),
                "final_disposition": result.get("final_disposition", "scenario_pass"),
            }
        )
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "ledger_id": f"{ROOT.name}-pilot-ledger",
        "description": (
            "Independent consumer pilot ledger for program section 23. "
            "Entries labeled automated_scenario are CI fixtures, not human adjudications. "
            "production_gate_met remains false until 30 human-adjudicated PRs exist."
        ),
        "ovk_source_version": "v1.2.1",
        "consumer_repos": [repo],
        "production_gate_met": False,
        "entries": entries,
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {LEDGER} with {len(entries)} automated_scenario entries; production_gate_met=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
