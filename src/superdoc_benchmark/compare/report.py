"""PDF report generation for visual comparisons."""

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from .diff import build_diff_overlay

# Reports folder in current working directory
REPORTS_DIR = Path.cwd() / "reports"


def get_reports_dir() -> Path:
    """Get the reports directory, creating it if needed.

    Returns:
        Path to the reports directory.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    return REPORTS_DIR


def get_report_dir(docx_name: str) -> Path:
    """Get the report directory for a document.

    Args:
        docx_name: Name of the document (stem).

    Returns:
        Path to reports/<docx_name>/
    """
    return get_reports_dir() / docx_name


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

    return {
        "comparison_pdf": comparison_path,
        "diff_pdf": diff_path,
        "word_pages": len(word_pages),
        "superdoc_pages": len(superdoc_pages),
    }
