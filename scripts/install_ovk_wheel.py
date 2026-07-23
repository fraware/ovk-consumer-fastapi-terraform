#!/usr/bin/env python3
"""Install OVK 1.2.1 from PyPI if present, else GitHub Release + cosign verify-blob."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

VERSION = "1.2.1"
TAG = "v1.2.1"
REPO = "fraware/open-verification-kernel"
WHEEL = f"open_verification_kernel-{VERSION}-py3-none-any.whl"
BUNDLE = f"{WHEEL}.cosign.bundle.json"
IDENTITY = (
    "https://github.com/fraware/open-verification-kernel/"
    ".github/workflows/publish.yml@refs/tags/v1.2.1"
)
ISSUER = "https://token.actions.githubusercontent.com"
RELEASE_BASE = f"https://github.com/{REPO}/releases/download/{TAG}"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def pypi_available() -> bool:
    url = f"https://pypi.org/pypi/open-verification-kernel/{VERSION}/json"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.status == 200
    except Exception:
        return False


def download(url: str, dest: Path) -> None:
    print(f"Downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def ensure_cosign() -> str:
    path = shutil.which("cosign")
    if path:
        return path
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux" and machine in {"x86_64", "amd64"}:
        url = "https://github.com/sigstore/cosign/releases/download/v2.4.1/cosign-linux-amd64"
        dest = Path(tempfile.gettempdir()) / "cosign"
        download(url, dest)
        dest.chmod(0o755)
        return str(dest)
    raise SystemExit("cosign not found; install cosign to verify the release wheel")


def install_from_release() -> None:
    with tempfile.TemporaryDirectory(prefix="ovk-wheel-") as tmp:
        tmp_path = Path(tmp)
        wheel = tmp_path / WHEEL
        bundle = tmp_path / BUNDLE
        download(f"{RELEASE_BASE}/{WHEEL}", wheel)
        download(f"{RELEASE_BASE}/{BUNDLE}", bundle)
        cosign = ensure_cosign()
        run(
            [
                cosign,
                "verify-blob",
                "--bundle",
                str(bundle),
                "--certificate-identity",
                IDENTITY,
                "--certificate-oidc-issuer",
                ISSUER,
                str(wheel),
            ]
        )
        run([sys.executable, "-m", "pip", "install", "--no-cache-dir", str(wheel)])


def main() -> None:
    if pypi_available():
        print(f"PyPI has open-verification-kernel=={VERSION}; installing from PyPI")
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-cache-dir",
                f"open-verification-kernel=={VERSION}",
            ]
        )
    else:
        print("PyPI package missing; installing signed wheel from GitHub Release")
        install_from_release()
    run(["ovk", "--help"], stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
