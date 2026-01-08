"""SuperDoc document screenshot capture using Playwright."""

import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .server import ViteServer


def ensure_playwright_browsers() -> None:
    """Ensure Playwright browsers are installed, installing if needed.

    This runs on first use and installs Chromium if not present.
    """
    from rich.console import Console
    console = Console()

    # Try to launch browser to see if it's installed
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return  # Browser exists, we're good
    except Exception as e:
        if "Executable doesn't exist" not in str(e):
            raise  # Different error, re-raise

    # Browser not installed, install it
    console.print("[yellow]Playwright browser not found. Installing Chromium (one-time setup)...[/yellow]")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to install browser: {result.stderr}")
        console.print("[green]Browser installed successfully![/green]\n")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Browser installation timed out")
    except FileNotFoundError:
        raise RuntimeError("Could not find playwright. Is it installed?")

# Harness element selectors
FILE_INPUT_SELECTOR = "#fileInput"
PAGE_SELECTOR = ".superdoc-page"

# CSS selectors to hide before screenshots
HIDE_SELECTORS = [
    ".presentation-editor__selection-overlay",
    ".selection-layer",
    ".comments-layer",
    ".ai-layer",
    ".floating-comments",
    "#controls",
]

# Timing constants
DEFAULT_TIMEOUT_MS = 60000
PAGE_TIMEOUT_MS = 30000
PAGE_SETTLE_MS = 300
PAGE_DELAY_MS = 100

# Parallel capture settings
MAX_PARALLEL_BROWSERS = 4  # Cap to avoid memory issues (~150MB per browser)

# Ready state scripts
READY_SCRIPT = "() => window.__superdocBenchmarkHarness === true"
LAYOUT_READY_SCRIPT = """() => {
    return window.__superdocReady === true &&
           window.__superdocLayoutStable === true &&
           window.__superdocFontsReady === true;
}"""


def build_hide_css(selectors: list[str]) -> str:
    """Build CSS to hide elements.

    Args:
        selectors: List of CSS selectors to hide.

    Returns:
        CSS string.
    """
    if not selectors:
        return ""
    joined = ", ".join(selectors)
    return f"{joined} {{ display: none !important; visibility: hidden !important; }}"


def get_superdoc_version_label() -> str:
    """Get a label for the current SuperDoc version/path.

    Returns:
        A string like "v1.4.2" for npm versions or "local-<hash>" for local paths.
    """
    from superdoc_benchmark.superdoc.config import get_config
    import hashlib

    config = get_config()
    version = config.get("superdoc_version")
    local_path = config.get("superdoc_local_path")

    if version:
        return f"v{version}"
    elif local_path:
        # Use a short hash of the path for uniqueness
        path_hash = hashlib.md5(local_path.encode()).hexdigest()[:8]
        return f"local-{path_hash}"
    else:
        return "unknown"


def get_superdoc_output_dir(docx_path: Path, version_label: str | None = None) -> Path:
    """Get the SuperDoc output directory for a document.

    Args:
        docx_path: Path to the .docx file.
        version_label: Optional version label. If None, uses current config.

    Returns:
        Path to reports/superdoc-captures/<docx-stem>-<version>/
    """
    from superdoc_benchmark.word.capture import get_reports_dir

    if version_label is None:
        version_label = get_superdoc_version_label()

    return get_reports_dir() / "superdoc-captures" / f"{docx_path.stem}-{version_label}"


def capture_superdoc_pages(
    docx_path: Path,
    harness_url: str,
    output_dir: Path,
    headless: bool = True,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    device_scale_factor: float = 1.0,
    viewport_width: int = 1600,
    viewport_height: int = 1200,
) -> int:
    """Capture SuperDoc page screenshots for a document.

    Args:
        docx_path: Path to the .docx file.
        harness_url: URL of the SuperDoc harness.
        output_dir: Directory to save screenshots.
        headless: Run browser in headless mode.
        timeout_ms: Global timeout in milliseconds.
        device_scale_factor: Device pixel ratio for screenshots.
        viewport_width: Browser viewport width.
        viewport_height: Browser viewport height.

    Returns:
        Number of pages captured.

    Raises:
        RuntimeError: If capture fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=device_scale_factor,
        )
        page.set_default_timeout(timeout_ms)

        # Navigate to harness
        page.goto(harness_url, wait_until="commit")

        # Wait for harness to be ready
        page.wait_for_function(READY_SCRIPT)

        # Hide UI elements
        page.add_style_tag(content=build_hide_css(HIDE_SELECTORS))

        # Upload the document
        page.wait_for_selector(FILE_INPUT_SELECTOR, state="attached")
        page.set_input_files(FILE_INPUT_SELECTOR, str(docx_path))

        # Wait for first page to appear
        page.wait_for_selector(PAGE_SELECTOR, state="visible")

        # Wait for fonts
        page.evaluate("() => (document.fonts ? document.fonts.ready : true)")

        # Wait for layout to stabilize
        page.wait_for_function(LAYOUT_READY_SCRIPT, timeout=timeout_ms)

        # Extra settle time
        page.wait_for_timeout(PAGE_SETTLE_MS)

        # Count pages
        page_count = page.evaluate(
            "(selector) => document.querySelectorAll(selector).length",
            PAGE_SELECTOR,
        )

        if page_count == 0:
            raise RuntimeError("SuperDoc rendered 0 pages")

        # Screenshot each page
        for idx in range(page_count):
            locator = page.locator(PAGE_SELECTOR).nth(idx)

            try:
                locator.scroll_into_view_if_needed(timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(PAGE_DELAY_MS)

                locator.screenshot(
                    path=str(output_dir / f"page_{idx + 1:04d}.png"),
                    timeout=PAGE_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f"Failed to capture page {idx + 1}: {exc}") from exc

        browser.close()

    return page_count


def capture_single_document(
    docx_path: Path,
    output_dir: Path | None = None,
    headless: bool = True,
) -> dict:
    """Capture SuperDoc screenshots for a single document.

    Starts the Vite server, captures screenshots, then stops the server.

    Args:
        docx_path: Path to the .docx file.
        output_dir: Optional output directory. If None, uses captures/<docx-stem>/superdoc.
        headless: Run browser in headless mode.

    Returns:
        Dict with capture results.

    Raises:
        RuntimeError: If capture fails.
    """
    # Ensure browser is installed (auto-installs on first run)
    ensure_playwright_browsers()

    if output_dir is None:
        output_dir = get_superdoc_output_dir(docx_path)

    with ViteServer() as server:
        page_count = capture_superdoc_pages(
            docx_path=docx_path,
            harness_url=server.url,
            output_dir=output_dir,
            headless=headless,
        )

    return {
        "docx_path": docx_path,
        "output_dir": output_dir,
        "page_count": page_count,
    }


def _capture_single_doc_worker(
    docx_path: Path,
    harness_url: str,
    output_dir: Path,
    headless: bool,
) -> dict:
    """Worker function for parallel capture.

    Each worker launches its own browser instance.
    This is a module-level function so it works with ThreadPoolExecutor.

    Returns:
        Dict with docx_path, output_dir, page_count on success.

    Raises:
        Exception on failure.
    """
    page_count = capture_superdoc_pages(
        docx_path=docx_path,
        harness_url=harness_url,
        output_dir=output_dir,
        headless=headless,
    )
    return {
        "docx_path": docx_path,
        "output_dir": output_dir,
        "page_count": page_count,
    }


def capture_superdoc_visuals(
    docx_files: list[Path],
    output_dir: Path | None = None,
    headless: bool = True,
) -> list[dict]:
    """Capture SuperDoc screenshots for multiple documents.

    Starts the Vite server once and captures all documents.
    Uses parallel browser instances for multiple files.

    Args:
        docx_files: List of .docx file paths.
        output_dir: Optional base output directory.
        headless: Run browser in headless mode.

    Returns:
        List of result dicts.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    console = Console()
    results = []
    errors = []

    # Ensure browser is installed (auto-installs on first run)
    ensure_playwright_browsers()

    console.print()

    # Determine parallelism level
    max_workers = min(len(docx_files), MAX_PARALLEL_BROWSERS) if len(docx_files) > 1 else 1

    with ViteServer() as server:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            overall_task = progress.add_task(
                "[cyan]Capturing SuperDoc renders...", total=len(docx_files)
            )

            if max_workers == 1:
                # Sequential for single file
                for docx_path in docx_files:
                    progress.update(
                        overall_task,
                        description=f"[cyan]Capturing: [white]{docx_path.name}",
                    )

                    try:
                        doc_output_dir = output_dir
                        if doc_output_dir is None:
                            doc_output_dir = get_superdoc_output_dir(docx_path)

                        page_count = capture_superdoc_pages(
                            docx_path=docx_path,
                            harness_url=server.url,
                            output_dir=doc_output_dir,
                            headless=headless,
                        )

                        results.append({
                            "docx_path": docx_path,
                            "output_dir": doc_output_dir,
                            "page_count": page_count,
                        })
                    except Exception as exc:
                        errors.append((docx_path, str(exc)))
                        console.print(f"  [red]Error:[/red] {docx_path.name}: {exc}")

                    progress.advance(overall_task)
            else:
                # Parallel capture with multiple browsers
                progress.update(
                    overall_task,
                    description=f"[cyan]Capturing SuperDoc renders ({max_workers} browsers)...",
                )

                # Prepare arguments
                capture_args = []
                for docx_path in docx_files:
                    doc_output_dir = output_dir
                    if doc_output_dir is None:
                        doc_output_dir = get_superdoc_output_dir(docx_path)
                    capture_args.append((docx_path, server.url, doc_output_dir, headless))

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_path = {
                        executor.submit(
                            _capture_single_doc_worker,
                            docx_path,
                            harness_url,
                            doc_output_dir,
                            headless,
                        ): docx_path
                        for docx_path, harness_url, doc_output_dir, headless in capture_args
                    }

                    for future in as_completed(future_to_path):
                        docx_path = future_to_path[future]
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as exc:
                            errors.append((docx_path, str(exc)))
                            console.print(f"  [red]Error:[/red] {docx_path.name}: {exc}")

                        progress.advance(overall_task)

    # Summary
    console.print()
    cwd = Path.cwd()
    if results:
        console.print(f"[green]Successfully captured {len(results)} document(s)[/green]")
        for r in results:
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
        console.print(f"\n[red]Failed to capture {len(errors)} document(s)[/red]")
        for path, err in errors:
            console.print(f"  [dim]•[/dim] {path.name}: {err}")

    console.print()
    return results
