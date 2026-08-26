#!/usr/bin/env python3
"""Validate immutable OVK Action pins in consumer workflows.

Default mode preserves the last attributable release policy (v1.2.1 or its exact
commit). ``--candidate-sha`` is the pre-publication release-evidence mode: every
OVK Action reference must equal that exact 40-hex candidate SHA. This keeps
historical release evidence distinct from candidate-bound authorization.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TAG = "v1.2.1"
ALLOWED_COMMIT = "a27d5720f4350c00bca34f71d991c31f5a2f38c7"
ACTION_RE = re.compile(r"^\s*uses:\s*(?P<ref>[^\s#]+)", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-sha",
        default=None,
        help="Require every OVK Action use to pin this exact 40-hex candidate SHA.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = args.candidate_sha.lower() if args.candidate_sha else None
    if candidate is not None and not SHA_RE.fullmatch(candidate):
        print(f"candidate SHA must be exact 40-hex, got {args.candidate_sha!r}", file=sys.stderr)
        return 2

    failures: list[str] = []
    workflow_files = sorted((ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
        (ROOT / ".github" / "workflows").glob("*.yaml")
    )
    if not workflow_files:
        failures.append("no workflow files found")

    expected_candidate_ref = (
        f"fraware/open-verification-kernel@{candidate}" if candidate is not None else None
    )

    for path in workflow_files:
        text = path.read_text(encoding="utf-8")
        for match in ACTION_RE.finditer(text):
            ref = match.group("ref").strip().strip("\"'")
            if "open-verification-kernel" not in ref:
                continue
            if ref in {"./", "./.", "fraware/open-verification-kernel"}:
                failures.append(f"{path.name}: forbidden local pin {ref!r}")
                continue
            if ref.endswith("@main") or ref.endswith("@master") or ref.endswith("@HEAD"):
                failures.append(f"{path.name}: unpinned mutable ref {ref!r}")
                continue

            if expected_candidate_ref is not None:
                if ref.lower() != expected_candidate_ref:
                    failures.append(
                        f"{path.name}: candidate evidence requires {expected_candidate_ref}, got {ref!r}"
                    )
                continue

            if ref == f"fraware/open-verification-kernel@{ALLOWED_TAG}":
                continue
            if ref == f"fraware/open-verification-kernel@{ALLOWED_COMMIT}":
                continue
            pin = ref.split("@", 1)[1] if "@" in ref else ""
            if (
                ref.startswith("fraware/open-verification-kernel@")
                and ALLOWED_COMMIT.startswith(pin)
                and len(pin) >= 7
            ):
                continue
            failures.append(
                f"{path.name}: OVK pin must be @{ALLOWED_TAG} or @{ALLOWED_COMMIT}, got {ref!r}"
            )

        for line in text.splitlines():
            if re.search(r"^\s*uses:\s*['\"]?\./", line):
                failures.append(f"{path.name}: forbidden uses: ./ ({line.strip()})")

        if "fraware/open-verification-kernel@" in text and "OVK_PACKAGE_VERSION" not in text:
            failures.append(f"{path.name}: missing OVK_PACKAGE_VERSION env for Action pin")

    if failures:
        print("OVK pin guard FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1

    if candidate is not None:
        print(f"OVK pin guard OK: all Action pins use exact candidate SHA {candidate}")
    else:
        print(
            f"OVK pin guard OK: Action pins are @{ALLOWED_TAG} (or attributable exact SHA) "
            "and never uses: ./"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
