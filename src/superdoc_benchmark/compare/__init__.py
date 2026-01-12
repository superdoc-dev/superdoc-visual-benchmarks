"""Visual comparison and report generation."""

from .diff import (
    build_diff_overlay,
    create_diff_from_files,
    WORD_DIFF_COLOR,
    SUPERDOC_DIFF_COLOR,
)
from .report import (
    build_run_label,
    create_run_report_dir,
    generate_reports,
    generate_comparison_pdf,
    generate_diff_pdf,
    get_doc_report_dir,
    get_reports_dir,
)
from .html_report import generate_html_report, DocumentReportInput
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
    "build_run_label",
    "create_run_report_dir",
    "get_doc_report_dir",
    "get_reports_dir",
    "generate_html_report",
    "DocumentReportInput",
    # Score
    "ScoreConfig",
    "ScoreWeights",
    "format_score_text",
    "score_document",
]
