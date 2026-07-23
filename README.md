# OVK Consumer - FastAPI + Terraform

Independent consumer repository for Open Verification Kernel program **section 23**.

This repository is **not** FormalPR-Holdout. It validates that an external adopter can
consume the immutable OVK release **`v1.2.1`** (Action + wheel) without `uses: ./`.

| Field | Value |
|---|---|
| Stack | FastAPI web app with Terraform infrastructure |
| OVK Action pin | `fraware/open-verification-kernel@v1.2.1` |
| OVK commit | `a27d5720f4350c00bca34f71d991c31f5a2f38c7` |
| Package version | `1.2.1` |
| Cosign identity | `https://github.com/fraware/open-verification-kernel/.github/workflows/publish.yml@refs/tags/v1.2.1` |
| Cosign issuer | `https://token.actions.githubusercontent.com` |
| Package status | **Beta** (does not claim vision completion or Production-stable) |

## Program section 23.1 scenario map

| Scenario | Coverage |
|---|---|
| Advisory passing PR | `scripts/run_scenario_matrix.py` + `fixtures/diffs/advisory_passing.diff` |
| Advisory failing PR | matrix + `fixtures/diffs/advisory_failing.diff` (recommendation `block`, exit 0) |
| Malformed / incomplete abstraction | matrix `malformed_auth` verify manifest |
| Strict blocking | matrix `--strict` + `.github/workflows/ovk-strict-fixture.yml` |
| Fork PR reduced permissions | `.github/workflows/ovk-fork-simulation.yml` + `docs/FORK_PR.md` (dry simulation) |
| PR comment | `.github/workflows/ovk-advisory-pr.yml` (`post-comment: true`) |
| Check run | `.github/workflows/ovk-advisory-pr.yml` (`emit-check: true`) |
| Release bundle | matrix `ovk verify` -> bundle artifacts |
| Published wheel | `scripts/install_ovk_wheel.py` (PyPI or Release + cosign verify-blob) |
| Cache reuse | matrix double-run with `.verification/cache` |
| Policy change | matrix rewrites `.verification/config.yml` |
| Backend unavailable | matrix cbmc-only / denied backends policy |
| Native backend timeout | matrix extreme `max_wall_time_seconds` budget |
| Generated regression artifact | matrix asserts `regression_unit_test` artifacts |

## Pin guard

CI fails if any workflow pins OVK as `uses: ./` or mutable `@main` / `@master`.
Allowed pins: `@v1.2.1` or exact commit `a27d5720f4350c00bca34f71d991c31f5a2f38c7`.

```bash
python scripts/assert_ovk_pin.py
```

## Pilot ledger

Machine-readable ledger: [`pilot/ledger.json`](pilot/ledger.json)
Schema: [`schemas/pilot.ledger.schema.json`](schemas/pilot.ledger.schema.json)

Seed entries from the automated matrix use `human_adjudication: automated_scenario`.
**`production_gate_met` is always `false` here.** Thirty human-adjudicated PRs per
independent consumer repository are still required before any Production-stable claim.

## Local commands

```bash
python scripts/install_ovk_wheel.py
python scripts/run_scenario_matrix.py
python scripts/seed_ledger_from_matrix.py
```

## Remaining human steps

1. Open a true cross-fork PR and adjudicate it in the ledger (see `docs/FORK_PR.md`).
2. Accumulate 30 human adjudications (not automated scenarios) before production-gate language.
3. Prefer PyPI install once `open-verification-kernel==1.2.1` is published; until then the Release wheel + cosign path is authoritative.
