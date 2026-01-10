"""SuperDoc version installation and validation."""

import json
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

from .config import CONFIG_DIR

# Workspace for npm installations
WORKSPACE_DIR = CONFIG_DIR / "workspace"


def get_resource_path(relative_path: str) -> Path:
    """Get path to a resource file, handling both dev and bundled contexts.

    Args:
        relative_path: Path relative to the project root.

    Returns:
        Absolute path to the resource.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # Running from source - go up from src/superdoc_benchmark/superdoc/
        base_path = Path(__file__).parent.parent.parent.parent

    return base_path / relative_path


def is_npm_available() -> bool:
    """Check if npm is available on the system.

    Returns:
        True if npm is in PATH.
    """
    return shutil.which("npm") is not None


def resolve_npm_tag(package: str, tag: str) -> str:
    """Resolve an npm dist-tag (like 'latest' or 'next') to an actual version.

    Prefers npm itself to avoid local TLS/cert issues with Python's SSL stack.

    Args:
        package: Package name (e.g., "superdoc").
        tag: Dist-tag to resolve (e.g., "latest", "next").

    Returns:
        The resolved version string (e.g., "1.5.2").

    Raises:
        RuntimeError: If the tag cannot be resolved.
    """
    npm_path = shutil.which("npm")
    if npm_path:
        try:
            result = subprocess.run(
                [npm_path, "view", f"{package}@{tag}", "version", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                output = result.stdout.strip()
                try:
                    version = json.loads(output)
                except json.JSONDecodeError:
                    version = output.strip('"')
                if isinstance(version, str) and version:
                    return version
            error_output = ""
            if result.stdout:
                error_output += result.stdout
            if result.stderr:
                error_output += result.stderr
            if error_output:
                raise RuntimeError(error_output.strip())
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"npm view timed out after 30s") from exc

    url = f"https://registry.npmjs.org/{package}/{tag}"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            version = data.get("version")
            if not version:
                raise RuntimeError(f"No version found for {package}@{tag}")
            return version
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Tag '{tag}' not found for package '{package}'") from e
        raise RuntimeError(f"Failed to resolve {package}@{tag}: HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to resolve {package}@{tag}: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid response from npm registry for {package}@{tag}") from e


def ensure_npm_available() -> None:
    """Ensure npm is available, raise error if not.

    Raises:
        RuntimeError: If npm is not found.
    """
    if not is_npm_available():
        raise RuntimeError(
            "npm is required for SuperDoc version management. "
            "Please install Node.js to continue."
        )


def run_npm(args: list[str], cwd: Path, timeout: int = 600) -> None:
    """Run an npm command.

    Args:
        args: Arguments to pass to npm.
        cwd: Working directory.
        timeout: Timeout in seconds.

    Raises:
        RuntimeError: If the command fails.
    """
    try:
        result = subprocess.run(
            ["npm", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            check=False,
        )
        if result.returncode != 0:
            # Include both stdout and stderr for full error context
            error_output = ""
            if result.stdout:
                error_output += result.stdout
            if result.stderr:
                error_output += result.stderr
            if not error_output:
                error_output = f"Exit code {result.returncode}"
            raise RuntimeError(f"npm {' '.join(args)} failed:\n{error_output}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"npm command timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("npm not found") from exc


def ensure_workspace() -> Path:
    """Ensure the npm workspace exists with harness files.

    Copies package.json, vite.config.js, and harness files to the workspace
    if they don't exist or are outdated.

    Returns:
        Path to the workspace directory.
    """
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # Copy node config files
    node_dir = get_resource_path("node")
    missing_assets = []
    required_node_files = ["package.json", "vite.config.js"]
    for filename in required_node_files:
        if not (node_dir / filename).exists():
            missing_assets.append(f"node/{filename}")

    harness_src = get_resource_path("harness")
    if not harness_src.exists():
        missing_assets.append("harness/")

    if missing_assets:
        missing_list = ", ".join(missing_assets)
        raise RuntimeError(
            "Required benchmark assets are missing: "
            f"{missing_list}. "
            "If you're using the bundled binary, reinstall it. "
            "If running from source, ensure the repo contains the node/ and harness/ folders."
        )

    for filename in ["package.json", "vite.config.js"]:
        src = node_dir / filename
        dst = WORKSPACE_DIR / filename
        if src.exists():
            shutil.copy(src, dst)

    # Copy harness files
    harness_dst = WORKSPACE_DIR / "harness"
    if harness_src.exists():
        if harness_dst.exists():
            shutil.rmtree(harness_dst)
        shutil.copytree(harness_src, harness_dst)

    return WORKSPACE_DIR


def ensure_node_modules() -> None:
    """Run npm install if node_modules doesn't exist.

    Raises:
        RuntimeError: If npm install fails.
    """
    ensure_npm_available()
    workspace = ensure_workspace()

    node_modules = workspace / "node_modules"
    if node_modules.exists():
        return

    run_npm(["install"], cwd=workspace, timeout=900)


def install_superdoc_version(version: str) -> str:
    """Install a specific SuperDoc version from npm.

    Args:
        version: Version string like "2.0.0", "latest", or "next".

    Returns:
        The actual version installed (resolved from tag if applicable).

    Raises:
        RuntimeError: If installation fails.
    """
    ensure_npm_available()
    workspace = ensure_workspace()

    # Resolve dist-tags (latest, next) to actual versions via npm registry
    # This ensures we always get the current version, bypassing npm cache
    resolved_version = version
    if version in ("latest", "next"):
        resolved_version = resolve_npm_tag("superdoc", version)

    # Remove existing node_modules to force clean install
    node_modules = workspace / "node_modules"
    if node_modules.exists():
        shutil.rmtree(node_modules)

    # Update package.json with the resolved version BEFORE npm install
    package_json_path = workspace / "package.json"
    if package_json_path.exists():
        package_data = json.loads(package_json_path.read_text())
        package_data["dependencies"]["superdoc"] = f"npm:superdoc@{resolved_version}"
        package_json_path.write_text(json.dumps(package_data, indent=2))

    # Run npm install to get all dependencies including superdoc
    run_npm(["install"], cwd=workspace, timeout=600)
    validate_installed_superdoc(workspace)

    return resolved_version


def get_installed_version() -> str | None:
    """Get the currently installed SuperDoc version from workspace.

    Returns:
        Version string or None if not installed.
    """
    workspace = WORKSPACE_DIR
    package_json = workspace / "node_modules" / "superdoc" / "package.json"

    if not package_json.exists():
        return None

    try:
        data = json.loads(package_json.read_text())
        return data.get("version")
    except (json.JSONDecodeError, OSError):
        return None


def _collect_export_paths(exports: object, paths: set[str]) -> None:
    if isinstance(exports, str):
        if exports.startswith("."):
            paths.add(exports)
        return
    if isinstance(exports, dict):
        for value in exports.values():
            _collect_export_paths(value, paths)
        return
    if isinstance(exports, list):
        for value in exports:
            _collect_export_paths(value, paths)


def validate_installed_superdoc(workspace: Path | None = None) -> None:
    """Validate that the installed SuperDoc package has its entrypoints present."""
    workspace = workspace or WORKSPACE_DIR
    package_root = workspace / "node_modules" / "superdoc"
    package_json = package_root / "package.json"

    if not package_json.exists():
        raise RuntimeError(
            f"SuperDoc package not found after install (missing {package_json})."
        )

    try:
        data = json.loads(package_json.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"Failed to read installed SuperDoc package.json: {exc}"
        ) from exc

    candidates: list[tuple[str, str]] = []
    for field in ("main", "module", "browser", "types", "typings"):
        value = data.get(field)
        if isinstance(value, str):
            candidates.append((field, value))

    export_paths: set[str] = set()
    _collect_export_paths(data.get("exports"), export_paths)
    for value in sorted(export_paths):
        if "*" in value:
            continue
        candidates.append(("exports", value))

    missing: list[str] = []
    ignored_prefixes = ("http:", "https:", "node:", "data:")
    for field, rel_path in candidates:
        if rel_path.startswith(ignored_prefixes):
            continue
        target_path = Path(rel_path)
        target = target_path if target_path.is_absolute() else package_root / rel_path
        if not target.exists():
            missing.append(f"{field}: {rel_path}")

    if missing:
        details = "\n".join(missing[:20])
        raise RuntimeError(
            "SuperDoc package appears incomplete after install. "
            "The build may have failed. Missing entrypoints:\n"
            f"{details}"
        )


def validate_local_repo(path: Path) -> tuple[bool, str | None, Path | None, str | None]:
    """Validate a local SuperDoc repository path.

    Args:
        path: Path to the local repository.

    Returns:
        Tuple of (is_valid, version, package_path, error_message).
        package_path is the actual path to the superdoc package (may differ from input for monorepos).
    """
    if not path.exists():
        return False, None, None, f"Path does not exist: {path}"

    if not path.is_dir():
        return False, None, None, f"Path is not a directory: {path}"

    # Check for package.json in expected locations
    package_json_paths = [
        (path / "packages" / "superdoc" / "package.json", path / "packages" / "superdoc"),  # Monorepo
        (path / "package.json", path),  # Root package.json
    ]

    version = None
    package_path = None
    for pkg_json, pkg_dir in package_json_paths:
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                # Verify it's actually SuperDoc
                name = data.get("name", "")
                if "superdoc" in name.lower() or pkg_dir.name == "superdoc":
                    version = data.get("version")
                    package_path = pkg_dir
                    break
            except (json.JSONDecodeError, OSError):
                continue

    if version is None or package_path is None:
        return False, None, None, "Could not find SuperDoc package.json in repository"

    return True, version, package_path, None


def run_pnpm_build(repo_root: Path, timeout: int = 300) -> None:
    """Run pnpm build at the repository root.

    Args:
        repo_root: Path to the repository root.
        timeout: Timeout in seconds.

    Raises:
        RuntimeError: If the build fails.
    """
    # Check if pnpm is available
    if shutil.which("pnpm") is None:
        raise RuntimeError(
            "pnpm is required for building local SuperDoc. "
            "Please install pnpm to continue."
        )

    try:
        result = subprocess.run(
            ["pnpm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(repo_root),
            check=False,
        )
        if result.returncode != 0:
            # Include both stdout and stderr for full error context
            error_output = ""
            if result.stdout:
                error_output += result.stdout
            if result.stderr:
                error_output += result.stderr
            if not error_output:
                error_output = f"Exit code {result.returncode}"
            raise RuntimeError(f"pnpm run build failed:\n{error_output}")
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"pnpm build timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("pnpm not found") from exc


def install_superdoc_local(package_path: Path, repo_root: Path | None = None) -> None:
    """Install SuperDoc from a local path.

    Args:
        package_path: Path to the superdoc package directory (containing package.json).
        repo_root: Path to the repository root for running build. If None, uses package_path.

    Raises:
        RuntimeError: If installation fails.
    """
    # Run pnpm build at repo root first
    build_path = repo_root if repo_root else package_path
    run_pnpm_build(build_path)

    ensure_npm_available()
    workspace = ensure_workspace()

    # Remove existing node_modules to force clean install
    node_modules = workspace / "node_modules"
    if node_modules.exists():
        shutil.rmtree(node_modules)

    # Update package.json to use file: protocol
    package_json_path = workspace / "package.json"
    if package_json_path.exists():
        package_data = json.loads(package_json_path.read_text())
        package_data["dependencies"]["superdoc"] = f"file:{package_path}"
        package_json_path.write_text(json.dumps(package_data, indent=2))

    # Run npm install
    run_npm(["install"], cwd=workspace, timeout=600)
    validate_installed_superdoc(workspace)


def get_workspace_path() -> Path:
    """Get the workspace directory path.

    Returns:
        Path to the workspace directory.
    """
    return WORKSPACE_DIR
