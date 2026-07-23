#!/usr/bin/env python3
"""Fail CI if OVK Action pins drift to uses: ./ or unpinned @main."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TAG = "v1.2.1"
ALLOWED_COMMIT = "a27d5720f4350c00bca34f71d991c31f5a2f38c7"
ACTION_RE = re.compile(r"^\s*uses:\s*(?P<ref>[^\s#]+)", re.MULTILINE)

failures: list[str] = []
workflow_files = sorted((ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
    (ROOT / ".github" / "workflows").glob("*.yaml")
)
if not workflow_files:
    failures.append("no workflow files found")

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
    sys.exit(1)

print(f"OVK pin guard OK: Action pins are @{ALLOWED_TAG} (or exact SHA) and never uses: ./")
