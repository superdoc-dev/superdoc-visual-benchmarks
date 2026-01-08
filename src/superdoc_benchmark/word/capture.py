"""Word document visual capture process."""

from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .export import export_word_pdf, rasterize_pdf, DEFAULT_DPI

console = Console()

# Artifacts folder in current working directory
ARTIFACTS_DIR = Path.cwd() / "artifacts"


def get_artifacts_dir() -> Path:
    """Get the artifacts directory, creating it if needed.

    Returns:
        Path to the artifacts directory in the current working directory.
    """
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    return ARTIFACTS_DIR


def get_output_dir(docx_path: Path) -> Path:
    """Get the output directory for a document's artifacts.

    Creates an 'artifacts/<docx-stem>' folder in the current working directory.

    Args:
        docx_path: Path to the .docx file.

    Returns:
        Path to the output directory.
    """
    return get_artifacts_dir() / docx_path.stem


def capture_single_document(
    docx_path: Path,
    output_dir: Path | None = None,
    dpi: int = DEFAULT_DPI,
) -> dict:
    """Capture Word visual for a single document.

    Args:
        docx_path: Path to the .docx file.
        output_dir: Optional output directory. If None, uses artifacts/<docx-stem>.
        dpi: DPI for rasterization (default 144).

    Returns:
        Dict with capture results including paths and page count.

    Raises:
        RuntimeError: If capture fails at any step.
    """
    if output_dir is None:
        output_dir = get_output_dir(docx_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    pdf_path = output_dir / f"{docx_path.stem}.pdf"

    # Step 1: Export to PDF via Word
    export_word_pdf(docx_path, pdf_path)

    # Step 2: Rasterize PDF to PNGs
    page_count = rasterize_pdf(
        pdf_path,
        output_dir,
        dpi=dpi,
        prefix="word-page",
    )

    return {
        "docx_path": docx_path,
        "pdf_path": pdf_path,
        "output_dir": output_dir,
        "page_count": page_count,
        "dpi": dpi,
    }


def capture_word_visuals(
    docx_files: list[Path],
    output_dir: Path | None = None,
    dpi: int = DEFAULT_DPI,
) -> list[dict]:
    """Capture visual renders from Word for the given documents.

    This process:
    1. Opens each .docx file in Microsoft Word via AppleScript
    2. Exports to PDF using Word's rendering engine
    3. Rasterizes the PDF to PNG images (one per page)

    Args:
        docx_files: List of .docx file paths to process.
        output_dir: Optional output directory. If None, creates artifacts/
                   folder in the current working directory.
        dpi: DPI for rasterization (default 144).

    Returns:
        List of result dicts, one per document.
    """
    results = []
    errors = []

    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        overall_task = progress.add_task(
            "[cyan]Processing documents...", total=len(docx_files)
        )

        for docx_path in docx_files:
            progress.update(
                overall_task,
                description=f"[cyan]Processing: [white]{docx_path.name}",
            )

            try:
                result = capture_single_document(
                    docx_path,
                    output_dir=output_dir,
                    dpi=dpi,
                )
                results.append(result)
            except Exception as exc:
                errors.append((docx_path, str(exc)))
                console.print(f"  [red]Error:[/red] {docx_path.name}: {exc}")

            progress.advance(overall_task)

    # Summary
    console.print()
    cwd = Path.cwd()
    if results:
        console.print(f"[green]Successfully processed {len(results)} document(s)[/green]")
        for r in results:
            # Show relative path if under cwd
            out_dir = r["output_dir"]
            try:
                rel_path = out_dir.relative_to(cwd)
                display_path = f"./{rel_path}"
            except ValueError:
                display_path = str(out_dir)
            console.print(
                f"  [dim]•[/dim] {r['docx_path'].name}: "
                f"{r['page_count']} page(s) → {display_path}"
            )

    if errors:
        console.print(f"\n[red]Failed to process {len(errors)} document(s)[/red]")
        for path, err in errors:
            console.print(f"  [dim]•[/dim] {path.name}: {err}")

    console.print()
    return results
