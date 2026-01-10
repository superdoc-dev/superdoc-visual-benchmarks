"""Word document export and PDF rasterization utilities."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import fitz  # PyMuPDF


def _sanitize_filename(name: str) -> str:
    """Sanitize a filename to be safe for filesystem and AppleScript.

    Args:
        name: Original filename (without extension).

    Returns:
        Sanitized filename with special characters replaced.
    """
    # Replace any non-alphanumeric characters (except . _ -) with underscore
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return sanitized.strip("_") or "document"

DPI_MIN = 72
DPI_MAX = 600
DEFAULT_DPI = 144

# Word's container folder - Word always has access here (no sandbox dialogs)
WORD_CONTAINER = Path.home() / "Library/Containers/com.microsoft.Word/Data"
WORD_TEMP_DIR = WORD_CONTAINER / "tmp" / "superdoc-benchmark"


def get_script_path() -> Path:
    """Get the path to the AppleScript file.

    Handles both development (source) and PyInstaller bundled contexts.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # Running from source
        base_path = Path(__file__).parent.parent.parent.parent

    script_path = base_path / "scripts" / "export_word_pdf.applescript"
    return script_path


def run_cmd(
    args: list[str], timeout: int | None = None, cwd: Path | None = None
) -> None:
    """Execute a shell command and raise an error if it fails.

    Args:
        args: Command and arguments as a list.
        timeout: Optional timeout in seconds.
        cwd: Optional working directory.

    Raises:
        RuntimeError: If the command returns a non-zero exit code or times out.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(cwd) if cwd else None,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}"
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Command timed out after {timeout}s: {' '.join(args)}"
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"Command not found: {args[0]}") from exc


def export_word_pdf(docx_path: Path, pdf_path: Path) -> None:
    """Export a Word document to PDF using AppleScript automation.

    This function requires Microsoft Word to be installed on macOS.

    Prefer a direct export to the destination path. If that fails (e.g.,
    Word cannot access the file path), fall back to using Word's container.

    Args:
        docx_path: Path to the input .docx file.
        pdf_path: Path where the PDF will be saved.

    Raises:
        RuntimeError: If AppleScript file not found or export command fails.
    """
    script_path = get_script_path()

    if not script_path.exists():
        raise RuntimeError(f"AppleScript not found: {script_path}")
    if not docx_path.exists():
        raise RuntimeError(f"Word document not found: {docx_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        run_cmd(
            ["osascript", str(script_path), str(docx_path), str(pdf_path)],
            timeout=300,
        )
        if not pdf_path.exists():
            raise RuntimeError("PDF was not created")
        return
    except RuntimeError as exc:
        direct_error = exc

    # Use Word's container folder as a fallback for stricter sandboxing setups.
    WORD_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = _sanitize_filename(docx_path.stem)
    temp_docx = WORD_TEMP_DIR / f"{safe_stem}.docx"
    temp_pdf = WORD_TEMP_DIR / f"{safe_stem}.pdf"

    try:
        shutil.copy2(str(docx_path), str(temp_docx))
        run_cmd(
            ["osascript", str(script_path), str(temp_docx), str(temp_pdf)],
            timeout=300,
        )
        if temp_pdf.exists():
            shutil.move(str(temp_pdf), str(pdf_path))
        else:
            raise RuntimeError("PDF was not created")
    except RuntimeError as exc:
        raise RuntimeError(
            "Failed to export Word document to PDF.\n"
            f"Direct export error: {direct_error}\n"
            f"Fallback export error: {exc}"
        ) from exc
    finally:
        if temp_docx.exists():
            temp_docx.unlink()
        if temp_pdf.exists():
            temp_pdf.unlink()


def rasterize_pdf(
    pdf_path: Path, out_dir: Path, dpi: int = DEFAULT_DPI, prefix: str = "page"
) -> int:
    """Convert PDF pages to PNG images at a specified DPI.

    Args:
        pdf_path: Path to the input PDF file.
        out_dir: Directory where PNG images will be saved.
        dpi: Dots per inch for rasterization (72-600, default 144).
        prefix: Filename prefix for output PNGs (e.g., "page" -> "page_0001.png").

    Returns:
        Number of pages rasterized.

    Raises:
        RuntimeError: If PDF cannot be opened or rasterization fails.
        ValueError: If DPI is out of valid range.
    """
    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")
    if dpi < DPI_MIN or dpi > DPI_MAX:
        raise ValueError(f"DPI must be between {DPI_MIN} and {DPI_MAX}, got {dpi}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF: {pdf_path}") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    page_count = len(doc)

    try:
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            pix.save(out_dir / f"{prefix}_{idx:04d}.png")
    except Exception as exc:
        raise RuntimeError(f"Failed to rasterize page {idx}: {exc}") from exc
    finally:
        doc.close()

    return page_count


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Number of pages in the PDF.
    """
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count
