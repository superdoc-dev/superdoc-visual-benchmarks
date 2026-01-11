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
from .html_report import generate_html_report
from .score import (
    ScoreConfig,
    ScoreWeights,
    format_score_text,
    score_document,
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
    "generate_html_report",
    # Score
    "ScoreConfig",
    "ScoreWeights",
    "format_score_text",
    "score_document",
]
