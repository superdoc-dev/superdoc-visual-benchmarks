"""SuperDoc version and configuration management."""

from .config import (
    get_config,
    save_config,
    get_superdoc_version,
    get_superdoc_local_path,
    CONFIG_DIR,
)
from .version import (
    install_superdoc_version,
    validate_local_repo,
    get_installed_version,
    ensure_workspace,
    is_npm_available,
)

__all__ = [
    "get_config",
    "save_config",
    "get_superdoc_version",
    "get_superdoc_local_path",
    "CONFIG_DIR",
    "install_superdoc_version",
    "validate_local_repo",
    "get_installed_version",
    "ensure_workspace",
    "is_npm_available",
]
