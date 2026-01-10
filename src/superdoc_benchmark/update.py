"""Update checks for the superdoc-benchmark CLI."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from superdoc_benchmark.superdoc.config import CONFIG_DIR

PACKAGE_NAME = "@superdoc-dev/visual-benchmarks"
CHECK_INTERVAL_S = 24 * 60 * 60
UPDATE_CHECK_FILE = CONFIG_DIR / "update-check.json"

_SEMVER_RE = re.compile(r"^(\\d+)\\.(\\d+)\\.(\\d+)(?:-([0-9A-Za-z.-]+))?$")


def _parse_version(version: str) -> tuple[int, int, int, list[tuple[int, object]] | None] | None:
    match = _SEMVER_RE.match(version)
    if not match:
        return None
    major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    pre = match.group(4)
    if not pre:
        return (major, minor, patch, None)
    parts: list[tuple[int, object]] = []
    for part in pre.split("."):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return (major, minor, patch, parts)


def compare_versions(a: str, b: str) -> int:
    """Compare two semver strings.

    Returns:
        1 if a > b, -1 if a < b, 0 if equal or unparsable.
    """
    pa = _parse_version(a)
    pb = _parse_version(b)
    if not pa or not pb:
        return 0
    for left, right in zip(pa[:3], pb[:3]):
        if left > right:
            return 1
        if left < right:
            return -1
    pre_a = pa[3]
    pre_b = pb[3]
    if pre_a is None and pre_b is None:
        return 0
    if pre_a is None:
        return 1
    if pre_b is None:
        return -1
    for left, right in zip(pre_a, pre_b):
        if left > right:
            return 1
        if left < right:
            return -1
    if len(pre_a) > len(pre_b):
        return 1
    if len(pre_a) < len(pre_b):
        return -1
    return 0


def _read_cache() -> tuple[float | None, str | None]:
    try:
        data = json.loads(UPDATE_CHECK_FILE.read_text())
        return float(data.get("last_check", 0)), data.get("latest_version")
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None


def _write_cache(latest_version: str) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(
            json.dumps(
                {"last_check": time.time(), "latest_version": latest_version},
                indent=2,
            )
        )
    except OSError:
        pass


def should_check_for_update() -> bool:
    last_check, _ = _read_cache()
    if last_check is None:
        return True
    return (time.time() - last_check) > CHECK_INTERVAL_S


def get_latest_version() -> str | None:
    npm_path = shutil.which("npm")
    if not npm_path:
        return None
    try:
        result = subprocess.run(
            [npm_path, "view", PACKAGE_NAME, "version", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if not output:
            return None
        try:
            version = json.loads(output)
        except json.JSONDecodeError:
            version = output.strip('"')
        return version if isinstance(version, str) and version else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def check_for_update(current_version: str) -> str | None:
    if not should_check_for_update():
        return None
    latest = get_latest_version()
    if not latest:
        return None
    _write_cache(latest)
    if compare_versions(latest, current_version) > 0:
        return latest
    return None


def run_update() -> None:
    npm_path = shutil.which("npm")
    if not npm_path:
        raise RuntimeError("npm is not available. Please install Node.js.")
    result = subprocess.run(
        [npm_path, "update", "-g", PACKAGE_NAME],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("npm update failed")
