"""SuperDoc version installation and validation."""

import json
import shutil
import subprocess
import sys
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
            raise RuntimeError(f"npm {' '.join(args)} failed:\n{result.stderr}")
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
    for filename in ["package.json", "vite.config.js"]:
        src = node_dir / filename
        dst = WORKSPACE_DIR / filename
        if src.exists():
            shutil.copy(src, dst)

    # Copy harness files
    harness_src = get_resource_path("harness")
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


def install_superdoc_version(version: str) -> None:
    """Install a specific SuperDoc version from npm.

    Args:
        version: Version string like "2.0.0", "latest", or "next".

    Raises:
        RuntimeError: If installation fails.
    """
    ensure_npm_available()
    workspace = ensure_workspace()

    # Remove existing node_modules to force clean install
    node_modules = workspace / "node_modules"
    if node_modules.exists():
        shutil.rmtree(node_modules)

    # Update package.json with the requested version BEFORE npm install
    package_json_path = workspace / "package.json"
    if package_json_path.exists():
        package_data = json.loads(package_json_path.read_text())
        # Use the version directly for tags like "latest" or "next"
        if version in ("latest", "next"):
            package_data["dependencies"]["superdoc"] = version
        else:
            package_data["dependencies"]["superdoc"] = f"npm:superdoc@{version}"
        package_json_path.write_text(json.dumps(package_data, indent=2))

    # Run npm install to get all dependencies including superdoc
    run_npm(["install"], cwd=workspace, timeout=600)


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
            raise RuntimeError(f"pnpm run build failed:\n{result.stderr}")
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


def get_workspace_path() -> Path:
    """Get the workspace directory path.

    Returns:
        Path to the workspace directory.
    """
    return WORKSPACE_DIR
