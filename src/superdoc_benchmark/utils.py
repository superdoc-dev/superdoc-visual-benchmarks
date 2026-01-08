"""Utility functions for superdoc-benchmark."""

from pathlib import Path


def find_docx_files(path: Path) -> list[Path]:
    """Find all .docx files in a path.

    If path is a file, returns it (if it's a .docx).
    If path is a directory, recursively finds all .docx files.

    Args:
        path: File or directory path to search.

    Returns:
        List of paths to .docx files, sorted alphabetically.
    """
    if path.is_file():
        if path.suffix.lower() == ".docx":
            return [path]
        return []

    if path.is_dir():
        docx_files = list(path.rglob("*.docx"))
        # Filter out temp files (start with ~$)
        docx_files = [f for f in docx_files if not f.name.startswith("~$")]
        return sorted(docx_files)

    return []


def validate_path(path_str: str) -> Path | None:
    """Validate and resolve a path string.

    Args:
        path_str: Path string from user input.

    Returns:
        Resolved Path if valid, None otherwise.
    """
    if not path_str.strip():
        return None

    path = Path(path_str).expanduser().resolve()

    if not path.exists():
        return None

    return path
