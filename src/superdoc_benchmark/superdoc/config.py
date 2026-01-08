"""SuperDoc configuration file management."""

import json
from pathlib import Path

# Config directory in user's home
CONFIG_DIR = Path.home() / ".superdoc-benchmark"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict:
    """Load the configuration from disk.

    Returns:
        Configuration dict with keys:
        - superdoc_version: NPM version string or None
        - superdoc_local_path: Path to local repo or None
    """
    if not CONFIG_FILE.exists():
        return {
            "superdoc_version": None,
            "superdoc_local_path": None,
        }

    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "superdoc_version": None,
            "superdoc_local_path": None,
        }


def save_config(config: dict) -> None:
    """Save configuration to disk.

    Args:
        config: Configuration dict to save.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_superdoc_version() -> str | None:
    """Get the configured SuperDoc NPM version.

    Returns:
        Version string like "2.0.0" or None if not set.
    """
    config = get_config()
    return config.get("superdoc_version")


def get_superdoc_local_path() -> Path | None:
    """Get the configured local SuperDoc repo path.

    Returns:
        Path to local repo or None if not set.
    """
    config = get_config()
    path_str = config.get("superdoc_local_path")
    if path_str:
        return Path(path_str)
    return None


def set_superdoc_version(version: str) -> None:
    """Set the SuperDoc NPM version (clears local path).

    Args:
        version: NPM version string like "2.0.0".
    """
    config = get_config()
    config["superdoc_version"] = version
    config["superdoc_local_path"] = None
    save_config(config)


def set_superdoc_local_path(path: Path) -> None:
    """Set the local SuperDoc repo path (clears NPM version).

    Args:
        path: Path to local SuperDoc repository.
    """
    config = get_config()
    config["superdoc_version"] = None
    config["superdoc_local_path"] = str(path.resolve())
    save_config(config)


def clear_superdoc_config() -> None:
    """Clear both version and local path settings."""
    config = get_config()
    config["superdoc_version"] = None
    config["superdoc_local_path"] = None
    save_config(config)
