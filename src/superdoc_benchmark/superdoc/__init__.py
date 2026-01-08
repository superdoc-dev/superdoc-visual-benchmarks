"""SuperDoc version, configuration, and capture management."""

from .config import (
    get_config,
    save_config,
    get_superdoc_version,
    get_superdoc_local_path,
    CONFIG_DIR,
)
from .version import (
    install_superdoc_version,
    install_superdoc_local,
    validate_local_repo,
    get_installed_version,
    ensure_workspace,
    is_npm_available,
)
from .server import (
    ViteServer,
    start_vite_server,
    stop_server,
)
from .capture import (
    capture_superdoc_pages,
    capture_superdoc_visuals,
    capture_single_document as capture_superdoc_single,
    get_superdoc_output_dir,
    get_superdoc_version_label,
)

__all__ = [
    # Config
    "get_config",
    "save_config",
    "get_superdoc_version",
    "get_superdoc_local_path",
    "CONFIG_DIR",
    # Version management
    "install_superdoc_version",
    "install_superdoc_local",
    "validate_local_repo",
    "get_installed_version",
    "ensure_workspace",
    "is_npm_available",
    # Server
    "ViteServer",
    "start_vite_server",
    "stop_server",
    # Capture
    "capture_superdoc_pages",
    "capture_superdoc_visuals",
    "capture_superdoc_single",
    "get_superdoc_output_dir",
    "get_superdoc_version_label",
]
