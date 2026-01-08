"""Visual comparison and report generation."""

from .diff import (
    build_diff_overlay,
    create_diff_from_files,
    WORD_DIFF_COLOR,
    SUPERDOC_DIFF_COLOR,
)
from .report import (
    generate_reports,
    generate_comparison_pdf,
    generate_diff_pdf,
    get_reports_dir,
    get_report_dir,
)

__all__ = [
    # Diff
    "build_diff_overlay",
    "create_diff_from_files",
    "WORD_DIFF_COLOR",
    "SUPERDOC_DIFF_COLOR",
    # Report
    "generate_reports",
    "generate_comparison_pdf",
    "generate_diff_pdf",
    "get_reports_dir",
    "get_report_dir",
]
