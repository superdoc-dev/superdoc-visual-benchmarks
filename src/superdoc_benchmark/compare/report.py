"""PDF report generation for visual comparisons."""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from .diff import build_diff_overlay
from .html_report import generate_html_report
from .score import score_document

# Reports folder in current working directory
REPORTS_DIR = Path.cwd() / "reports"


def get_reports_dir() -> Path:
    """Get the reports directory, creating it if needed.

    Returns:
        Path to the reports directory.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    return REPORTS_DIR


def get_comparisons_dir() -> Path:
    """Get the comparisons directory, creating it if needed.

    Returns:
        Path to reports/comparisons/
    """
    comparisons_dir = get_reports_dir() / "comparisons"
    comparisons_dir.mkdir(exist_ok=True)
    return comparisons_dir


def get_report_dir(docx_name: str) -> Path:
    """Get the report directory for a document.

    Args:
        docx_name: Name of the document (stem).

    Returns:
        Path to reports/comparisons/<docx_name>/
    """
    return get_comparisons_dir() / docx_name


def create_side_by_side(
    left_img: Image.Image,
    right_img: Image.Image,
    gap: int = 20,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Create a side-by-side image from two images.

    Args:
        left_img: Left image.
        right_img: Right image.
        gap: Gap between images in pixels.
        background: Background color (RGB).

    Returns:
        Combined side-by-side image.
    """
    # Resize right to match left height if needed
    if left_img.height != right_img.height:
        ratio = left_img.height / right_img.height
        new_width = int(right_img.width * ratio)
        right_img = right_img.resize((new_width, left_img.height), Image.Resampling.LANCZOS)

    # Create combined image
    total_width = left_img.width + gap + right_img.width
    combined = Image.new("RGB", (total_width, left_img.height), background)

    # Paste images
    combined.paste(left_img, (0, 0))
    combined.paste(right_img, (left_img.width + gap, 0))

    return combined


def images_to_pdf(images: list[Image.Image], output_path: Path) -> None:
    """Convert a list of PIL images to a PDF.

    Args:
        images: List of PIL images.
        output_path: Path to save the PDF.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()

    for img in images:
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Create page with image dimensions
        # Convert pixels to points (72 points per inch, assume 144 DPI)
        width_pt = img.width * 72 / 144
        height_pt = img.height * 72 / 144

        page = doc.new_page(width=width_pt, height=height_pt)

        # Insert image
        rect = fitz.Rect(0, 0, width_pt, height_pt)
        page.insert_image(rect, stream=img_bytes.read())

    doc.save(str(output_path))
    doc.close()


def generate_comparison_pdf(
    word_pages: list[Path],
    superdoc_pages: list[Path],
    output_path: Path,
    gap: int = 20,
) -> None:
    """Generate a comparison PDF with Word and SuperDoc side by side.

    Args:
        word_pages: List of Word page image paths (sorted).
        superdoc_pages: List of SuperDoc page image paths (sorted).
        output_path: Path to save the PDF.
        gap: Gap between images in pixels.
    """
    combined_images = []

    # Match pages by index
    num_pages = min(len(word_pages), len(superdoc_pages))

    for i in range(num_pages):
        word_img = Image.open(word_pages[i])
        superdoc_img = Image.open(superdoc_pages[i])

        combined = create_side_by_side(word_img, superdoc_img, gap=gap)
        combined_images.append(combined)

    images_to_pdf(combined_images, output_path)


def generate_diff_pdf(
    word_pages: list[Path],
    superdoc_pages: list[Path],
    output_path: Path,
    gap: int = 20,
) -> None:
    """Generate a diff PDF with Word and diff overlay side by side.

    Args:
        word_pages: List of Word page image paths (sorted).
        superdoc_pages: List of SuperDoc page image paths (sorted).
        output_path: Path to save the PDF.
        gap: Gap between images in pixels.
    """
    combined_images = []

    # Match pages by index
    num_pages = min(len(word_pages), len(superdoc_pages))

    for i in range(num_pages):
        word_img = Image.open(word_pages[i])
        superdoc_img = Image.open(superdoc_pages[i])

        # Generate diff overlay
        diff_img = build_diff_overlay(word_img, superdoc_img)

        combined = create_side_by_side(word_img, diff_img, gap=gap)
        combined_images.append(combined)

    images_to_pdf(combined_images, output_path)


def generate_reports(
    docx_name: str,
    word_dir: Path,
    superdoc_dir: Path,
    version_label: str,
) -> dict:
    """Generate comparison and diff PDF reports for a document.

    Args:
        docx_name: Name of the document (stem).
        word_dir: Directory containing Word page images.
        superdoc_dir: Directory containing SuperDoc page images.
        version_label: SuperDoc version label for filename.

    Returns:
        Dict with paths to generated reports.
    """
    # Get sorted page lists
    word_pages = sorted(word_dir.glob("page_*.png"))
    superdoc_pages = sorted(superdoc_dir.glob("page_*.png"))

    if not word_pages:
        raise RuntimeError(f"No Word pages found in {word_dir}")
    if not superdoc_pages:
        raise RuntimeError(f"No SuperDoc pages found in {superdoc_dir}")

    # Create report directory
    report_dir = get_report_dir(docx_name)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Generate comparison PDF
    comparison_path = report_dir / f"comparison-{version_label}.pdf"
    generate_comparison_pdf(word_pages, superdoc_pages, comparison_path)

    # Generate diff PDF
    diff_path = report_dir / f"diff-{version_label}.pdf"
    generate_diff_pdf(word_pages, superdoc_pages, diff_path)

    # Generate scoring files
    try:
        score_data = score_document(word_pages, superdoc_pages)
    except Exception as exc:
        raise RuntimeError(f"Failed to score document: {exc}") from exc

    score_json_path = report_dir / f"score-{version_label}.json"
    score_json_path.write_text(
        json.dumps(score_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report_by_version_path = _update_report_by_version(report_dir, docx_name)
    html_report_path = generate_html_report(
        docx_name=docx_name,
        word_pages=word_pages,
        superdoc_pages=superdoc_pages,
        version_label=version_label,
        report_dir=report_dir,
    )

    return {
        "comparison_pdf": comparison_path,
        "diff_pdf": diff_path,
        "score_json": score_json_path,
        "report_by_version": report_by_version_path,
        "html_report": html_report_path,
        "word_pages": len(word_pages),
        "superdoc_pages": len(superdoc_pages),
    }


def _update_report_by_version(report_dir: Path, docx_name: str) -> Path:
    score_files = sorted(
        report_dir.glob("score-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    entries = []
    for score_path in score_files:
        version = score_path.stem.removeprefix("score-")
        mtime = score_path.stat().st_mtime
        generated_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        try:
            data = json.loads(score_path.read_text(encoding="utf-8"))
            entry = {
                "version": version,
                "score_file": score_path.name,
                "generated_at": generated_at,
                "mtime_epoch": mtime,
                "score": data,
            }
        except Exception as exc:
            entry = {
                "version": version,
                "score_file": score_path.name,
                "generated_at": generated_at,
                "mtime_epoch": mtime,
                "error": str(exc),
            }
        entries.append(entry)

    report_data = {
        "document": docx_name,
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scores": entries,
    }

    report_path = report_dir / "report-by-version.json"
    report_path.write_text(
        json.dumps(report_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path
