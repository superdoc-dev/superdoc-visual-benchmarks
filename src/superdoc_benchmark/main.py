"""Main entry point for superdoc-benchmark CLI."""

from pathlib import Path
from typing import Optional

import typer
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.text import Text

from superdoc_benchmark import __version__

console = Console()
app = typer.Typer(
    help="Visual benchmarking tool for SuperDoc document rendering.",
    no_args_is_help=False,
    invoke_without_command=True,
)

# ASCII art logo - "SUPER" in dark teal, "DOC" in dark purple
SUPER_COLOR = "#0E7490"
DOC_COLOR = "#7C3AED"

LOGO_LINES = [
    [("███████╗██╗   ██╗██████╗ ███████╗██████╗ ", SUPER_COLOR),
     ("██████╗  ██████╗  ██████╗", DOC_COLOR)],
    [("██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗", SUPER_COLOR),
     ("██╔══██╗██╔═══██╗██╔════╝", DOC_COLOR)],
    [("███████╗██║   ██║██████╔╝█████╗  ██████╔╝", SUPER_COLOR),
     ("██║  ██║██║   ██║██║     ", DOC_COLOR)],
    [("╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗", SUPER_COLOR),
     ("██║  ██║██║   ██║██║     ", DOC_COLOR)],
    [("███████║╚██████╔╝██║     ███████╗██║  ██║", SUPER_COLOR),
     ("██████╔╝╚██████╔╝╚██████╗", DOC_COLOR)],
    [("╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝", SUPER_COLOR),
     ("╚═════╝  ╚═════╝  ╚═════╝", DOC_COLOR)],
]


def maybe_check_for_cli_update() -> None:
    """Check npm for a newer superdoc-benchmark version and offer to update."""
    import os
    import sys

    if os.environ.get("SUPERDOC_BENCHMARK_SKIP_UPDATE_CHECK") == "1":
        return

    if not sys.stdin.isatty() or not sys.stderr.isatty():
        return

    try:
        from superdoc_benchmark.update import check_for_update, run_update
    except Exception:
        return

    latest = check_for_update(__version__)
    if not latest:
        return

    console.print()
    console.print(
        f"[yellow]New version available:[/yellow] {latest} (current: {__version__})"
    )

    try:
        should_update = inquirer.confirm(
            message="Update now with npm?",
            default=True,
            qmark="🦋",
            amark="🦋",
        ).execute()
    except KeyboardInterrupt:
        return

    if not should_update:
        console.print(
            "[dim]Skipped. Run `npm update -g @superdoc-dev/visual-benchmarks` anytime.[/dim]"
        )
        return

    try:
        with console.status("[cyan]Updating via npm...", spinner="dots"):
            run_update()
    except Exception as exc:
        console.print(f"[red]Update failed:[/red] {exc}\n")
        return

    console.print(
        "[green]Updated successfully![/green] Please re-run your command.\n"
    )
    raise typer.Exit(0)


def get_logo() -> Text:
    """Generate the colored SuperDoc ASCII art logo."""
    text = Text()
    for i, line_parts in enumerate(LOGO_LINES):
        for part_text, style in line_parts:
            text.append(part_text, style=style)
        if i < len(LOGO_LINES) - 1:
            text.append("\n")
    return text


def show_welcome() -> None:
    """Display the welcome screen with logo and info."""
    from superdoc_benchmark.superdoc.config import get_config

    console.print()
    console.print("                            ⟡ 🦋 ⟡", highlight=False)
    console.print()
    console.print(get_logo())
    console.print()

    subtitle = Text()
    subtitle.append("  Benchmark", style=f"bold {SUPER_COLOR}")
    subtitle.append(" v" + __version__, style="dim")
    subtitle.append("  ◦  ", style="dim")
    subtitle.append("Visual comparison for document rendering", style="dim italic")
    console.print(subtitle)

    config = get_config()
    superdoc_version = config.get("superdoc_version")
    superdoc_local = config.get("superdoc_local_path")

    superdoc_status = Text()
    superdoc_status.append("  SuperDoc: ", style="dim")
    if superdoc_version:
        superdoc_status.append(f"v{superdoc_version}", style=f"bold {DOC_COLOR}")
        superdoc_status.append(" (npm)", style="dim")
    elif superdoc_local:
        superdoc_status.append("local", style=f"bold {DOC_COLOR}")
        superdoc_status.append(f" ({superdoc_local})", style="dim")
    else:
        superdoc_status.append("not configured", style="yellow")
        superdoc_status.append(" (use Set SuperDoc version)", style="dim")
    console.print(superdoc_status)
    console.print()


def show_main_menu() -> str | None:
    """Display the main menu and return the selected option."""
    choices = [
        Choice(value="compare_docx", name="Compare DOCX"),
        Choice(value="set_superdoc_version", name="Set SuperDoc version"),
        Choice(value="check_updates", name="Check for updates"),
        Choice(value=None, name="Exit"),
    ]

    result = inquirer.rawlist(
        message="Select an option:",
        choices=choices,
        default="compare_docx",
        qmark="🦋",
        amark="🦋",
        instruction="(↑↓ or type number)",
    ).execute()

    return result


def handle_generate_word_visual() -> None:
    """Handle the Generate Word visual option (interactive)."""
    from superdoc_benchmark.utils import find_docx_files, validate_path
    from superdoc_benchmark.word import capture_word_visuals, get_word_output_dir

    console.print()

    try:
        path_str = inquirer.filepath(
            message="Enter path to .docx file or folder:",
            default="",
            qmark="🦋",
            amark="🦋",
            instruction="(ctrl+c to go back)",
        ).execute()
    except KeyboardInterrupt:
        path_str = None

    if path_str:
        path_str = path_str.strip()

    if not path_str:
        console.print("[dim]Cancelled[/dim]\n")
        return

    path = validate_path(path_str)
    if path is None:
        console.print("[red]Invalid path[/red]\n")
        return

    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]\n")
        return

    if path.is_dir():
        console.print(f"[dim]Found {len(docx_files)} .docx file(s) in {path}[/dim]")
    else:
        console.print(f"[dim]Processing: {path.name}[/dim]")

    existing_captures = []
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        if word_dir.exists() and list(word_dir.glob("page_*.png")):
            existing_captures.append(docx_path)

    if existing_captures:
        console.print()
        console.print(f"[yellow]Word captures already exist for {len(existing_captures)} file(s):[/yellow]")
        for docx_path in existing_captures:
            console.print(f"  [dim]•[/dim] {docx_path.name}")
        console.print()

        try:
            override = inquirer.confirm(
                message="Override existing captures?",
                default=False,
                qmark="🦋",
                amark="🦋",
            ).execute()
        except KeyboardInterrupt:
            override = False

        if not override:
            console.print("[dim]Cancelled[/dim]\n")
            return

    capture_word_visuals(docx_files, force=True)


def handle_compare_docx() -> None:
    """Handle the Compare DOCX option (interactive)."""
    from superdoc_benchmark.utils import find_docx_files, validate_path
    from superdoc_benchmark.superdoc.config import get_config

    console.print()

    config = get_config()
    if not config.get("superdoc_version") and not config.get("superdoc_local_path"):
        console.print("[yellow]SuperDoc is not configured.[/yellow]")
        console.print("[dim]Use Set SuperDoc version first.[/dim]\n")
        return

    try:
        path_str = inquirer.filepath(
            message="Enter path to .docx file or folder:",
            default="",
            qmark="🦋",
            amark="🦋",
            instruction="(ctrl+c to go back)",
        ).execute()
    except KeyboardInterrupt:
        path_str = None

    if path_str:
        path_str = path_str.strip()

    if not path_str:
        console.print("[dim]Cancelled[/dim]\n")
        return

    path = validate_path(path_str)
    if path is None:
        console.print("[red]Invalid path[/red]\n")
        return

    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]\n")
        return

    run_compare(docx_files, root_path=path)


def _generate_report_task(
    docx_name: str,
    word_dir: Path,
    superdoc_dir: Path,
    version_label: str,
    report_dir: Path,
) -> dict:
    """Worker function for parallel report generation.

    This is a module-level function so it can be pickled for ProcessPoolExecutor.
    """
    from superdoc_benchmark.compare import generate_reports

    return generate_reports(
        docx_name=docx_name,
        word_dir=word_dir,
        superdoc_dir=superdoc_dir,
        version_label=version_label,
        report_dir=report_dir,
    )


def run_compare(
    docx_files: list[Path],
    root_path: Path | None = None,
    skip_reports: bool = False,
) -> None:
    """Run the compare workflow for a list of docx files."""
    from superdoc_benchmark.word import (
        capture_word_visuals,
        get_word_output_dir,
    )
    from superdoc_benchmark.superdoc import (
        capture_superdoc_visuals,
        get_superdoc_output_dir,
        get_superdoc_version_label,
    )
    from superdoc_benchmark.superdoc.config import get_config
    from superdoc_benchmark.compare import (
        DocumentReportInput,
        create_run_report_dir,
        generate_html_report,
        generate_reports,
    )
    from superdoc_benchmark.utils import make_docx_output_path

    separator = "[dim]────────────────────────────────────────────────────────[/dim]"
    version_label = get_superdoc_version_label()
    config = get_config()
    is_local = config.get("superdoc_local_path") is not None
    run_dir, run_label = create_run_report_dir(version_label)

    version_type = "local" if is_local else "npm"
    console.print(f"[dim]SuperDoc version: [cyan]{version_label}[/cyan] ({version_type})[/dim]")

    if len(docx_files) == 1:
        console.print(f"[dim]Processing: {docx_files[0].name}[/dim]")
    else:
        console.print(f"[dim]Found {len(docx_files)} .docx file(s)[/dim]")

    console.print()

    # Check which files need Word screenshots
    word_missing = []
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        word_pages = list(word_dir.glob("page_*.png")) if word_dir.exists() else []
        if not word_pages:
            word_missing.append(docx_path)

    # Check which files need SuperDoc screenshots
    # - Local version: always recapture (code may have changed)
    # - NPM version: only capture if missing
    superdoc_missing = []
    for docx_path in docx_files:
        superdoc_dir = get_superdoc_output_dir(docx_path)
        superdoc_pages = list(superdoc_dir.glob("page_*.png")) if superdoc_dir.exists() else []
        if is_local or not superdoc_pages:
            superdoc_missing.append(docx_path)

    # Report status
    console.print("[bold]Capture status:[/bold]")
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        superdoc_dir = get_superdoc_output_dir(docx_path)

        word_pages = list(word_dir.glob("page_*.png")) if word_dir.exists() else []
        superdoc_pages = list(superdoc_dir.glob("page_*.png")) if superdoc_dir.exists() else []

        word_status = f"[green]{len(word_pages)} pages[/green]" if word_pages else "[yellow]missing[/yellow]"

        if is_local:
            sd_status = f"[dim]{len(superdoc_pages)} pages (will recapture - local)[/dim]" if superdoc_pages else "[yellow]missing[/yellow]"
        else:
            sd_status = f"[green]{len(superdoc_pages)} pages[/green]" if superdoc_pages else "[yellow]missing[/yellow]"

        console.print(f"  [dim]•[/dim] {docx_path.name}: Word={word_status}, SuperDoc={sd_status}")

    console.print()

    # Capture missing Word screenshots
    if word_missing:
        console.print(f"📄 [cyan]Capturing Word screenshots for {len(word_missing)} file(s)...[/cyan]")
        capture_word_visuals(word_missing, print_trailing_newline=False)
        console.print(separator)
        console.print()

    # Capture SuperDoc screenshots (missing only for npm, all for local)
    if superdoc_missing:
        if is_local:
            console.print(f"🦋 [cyan]Capturing SuperDoc ({version_label}) screenshots for {len(superdoc_missing)} file(s) (local - always recapture)...[/cyan]")
        else:
            console.print(f"🦋 [cyan]Capturing SuperDoc ({version_label}) screenshots for {len(superdoc_missing)} file(s)...[/cyan]")
        capture_superdoc_visuals(superdoc_missing, print_trailing_newline=False)
    else:
        console.print(f"🦋 [dim]SuperDoc captures exist for all files (npm version - skipping)[/dim]")
    console.print(separator)
    console.print()

    if skip_reports:
        console.print("[dim]Skipping report generation.[/dim]\n")
        return

    # Generate comparison reports (parallel for multiple files)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
    import os

    report_results = []
    report_errors = []

    root_for_reports = None
    if root_path is not None and root_path.is_dir():
        root_for_reports = root_path.parent

    # Prepare arguments for parallel execution
    report_entries = []
    for docx_path in docx_files:
        docx_rel = make_docx_output_path(docx_path, root_for_reports)
        docx_name = docx_rel.as_posix()
        word_dir = get_word_output_dir(docx_path)
        superdoc_dir = get_superdoc_output_dir(docx_path)
        report_dir = run_dir / docx_rel
        report_entries.append({
            "docx_path": docx_path,
            "docx_name": docx_name,
            "word_dir": word_dir,
            "superdoc_dir": superdoc_dir,
            "report_dir": report_dir,
        })

    # Use parallel processing for multiple files, sequential for single file
    max_workers = min(len(report_entries), max(1, os.cpu_count() - 1)) if len(report_entries) > 1 else 1

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        report_task = progress.add_task(
            "[cyan]Generating comparison reports...", total=len(report_entries)
        )

        if max_workers == 1:
            # Sequential processing for single file
            for entry in report_entries:
                docx_path = entry["docx_path"]
                progress.update(
                    report_task,
                    description=f"[cyan]Generating report: [white]{docx_path.name}",
                )
                try:
                    progress.update(
                        report_task,
                        description=f"[cyan]Generating report: [white]{docx_path.name}",
                    )
                    result = generate_reports(
                        docx_name=entry["docx_name"],
                        word_dir=entry["word_dir"],
                        superdoc_dir=entry["superdoc_dir"],
                        version_label=version_label,
                        report_dir=entry["report_dir"],
                    )
                    report_results.append((docx_path, result))
                except Exception as exc:
                    report_errors.append((docx_path, str(exc)))
                    console.print(f"[red]Error:[/red] {docx_path.name}: {exc}")
                progress.advance(report_task)
        else:
            # Parallel processing for multiple files
            progress.update(
                report_task,
                description=f"[cyan]Generating reports ({max_workers} workers)...",
            )
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(
                        _generate_report_task,
                        entry["docx_name"],
                        entry["word_dir"],
                        entry["superdoc_dir"],
                        version_label,
                        entry["report_dir"],
                    ): entry["docx_path"]
                    for entry in report_entries
                }

                # Collect results as they complete
                for future in as_completed(future_to_path):
                    docx_path = future_to_path[future]
                    try:
                        result = future.result()
                        report_results.append((docx_path, result))
                    except Exception as exc:
                        report_errors.append((docx_path, str(exc)))
                        console.print(f"[red]Error:[/red] {docx_path.name}: {exc}")
                    progress.advance(report_task)

    html_report_path = None
    html_errors = []
    html_inputs = []
    for entry in report_entries:
        word_pages = sorted(entry["word_dir"].glob("page_*.png"))
        superdoc_pages = sorted(entry["superdoc_dir"].glob("page_*.png"))
        if not word_pages:
            html_errors.append((entry["docx_path"], f"No Word pages found in {entry['word_dir']}"))
            continue
        if not superdoc_pages:
            html_errors.append((entry["docx_path"], f"No SuperDoc pages found in {entry['superdoc_dir']}"))
            continue
        score_path = entry["report_dir"] / f"score-{version_label}.json"
        html_inputs.append(DocumentReportInput(
            name=entry["docx_name"],
            word_pages=word_pages,
            superdoc_pages=superdoc_pages,
            assets_dir=entry["report_dir"],
            score_path=score_path if score_path.exists() else None,
        ))

    if html_inputs:
        try:
            html_report_path = generate_html_report(
                documents=html_inputs,
                version_label=version_label,
                report_dir=run_dir,
                run_label=run_label,
            )
        except Exception as exc:
            console.print(f"[red]Failed to generate HTML report:[/red] {exc}")
    else:
        console.print("[yellow]No HTML report generated (missing page captures).[/yellow]")

    # Summary
    from superdoc_benchmark.word.capture import get_reports_dir

    reports_dir = get_reports_dir()
    console.print(f"[dim]Reports directory:[/dim] {reports_dir}")
    cwd = Path.cwd()
    if report_results:
        console.print(f"[green]Generated reports for {len(report_results)} document(s)[/green]")
        for docx_path, result in report_results:
            comparison_path = result["comparison_pdf"]
            diff_path = result["diff_pdf"]
            score_path = result.get("score_json")
            try:
                comparison_rel = comparison_path.relative_to(cwd)
                diff_rel = diff_path.relative_to(cwd)
                score_rel = score_path.relative_to(cwd) if score_path else None
            except ValueError:
                comparison_rel = comparison_path
                diff_rel = diff_path
                score_rel = score_path
            console.print(f"  [dim]•[/dim] {docx_path.name}:")
            console.print(f"      comparison: [cyan]./{comparison_rel}[/cyan]")
            console.print(f"      diff: [cyan]./{diff_rel}[/cyan]")
            if score_rel:
                console.print(f"      score: [cyan]./{score_rel}[/cyan]")

    if html_report_path:
        console.print()
        html_display = str(html_report_path.resolve())
        console.print(f"[dim]📄 Report viewer:[/dim] [cyan]{html_display}[/cyan]")
        console.print("[dim]────────────────────────────────────────[/dim]")

    if report_errors:
        console.print(f"\n[red]Failed to generate reports for {len(report_errors)} document(s)[/red]")
        for path, err in report_errors:
            console.print(f"  [dim]•[/dim] {path.name}: {err}")

    if html_errors:
        console.print(f"\n[yellow]Skipped {len(html_errors)} document(s) in the HTML report[/yellow]")
        for path, err in html_errors:
            console.print(f"  [dim]•[/dim] {path.name}: {err}")

    console.print()


def handle_set_superdoc_version() -> None:
    """Handle the Set SuperDoc version option (interactive)."""
    from superdoc_benchmark.superdoc.config import (
        get_config,
        set_superdoc_version,
        set_superdoc_local_path,
    )
    from superdoc_benchmark.superdoc.version import (
        install_superdoc_version,
        validate_local_repo,
        get_installed_version,
        is_npm_available,
        resolve_npm_tag,
    )
    from superdoc_benchmark.utils import validate_path

    console.print()

    config = get_config()
    current_version = config.get("superdoc_version")
    current_local = config.get("superdoc_local_path")
    installed = get_installed_version()

    if current_version:
        console.print(f"[dim]Current setting:[/dim] NPM version [cyan]{current_version}[/cyan]")
        if installed:
            console.print(f"[dim]Installed version:[/dim] [cyan]{installed}[/cyan]")
    elif current_local:
        console.print(f"[dim]Current setting:[/dim] Local repo [cyan]{current_local}[/cyan]")
    else:
        console.print("[dim]No SuperDoc version configured[/dim]")

    console.print()

    choices = [
        Choice(value="latest", name="Install 'latest'"),
        Choice(value="next", name="Install 'next'"),
        Choice(value="npm", name="Install from NPM (e.g., 1.0.0)"),
        Choice(value="local", name="Use local repository"),
    ]

    if current_version or current_local:
        choices.append(Choice(value="reinstall", name="Re-install current version"))

    choices.append(Choice(value="back", name="Back to main menu"))

    action = inquirer.rawlist(
        message="How would you like to configure SuperDoc?",
        choices=choices,
        default="latest",
        qmark="🦋",
        amark="🦋",
    ).execute()

    if action == "back":
        return

    if action == "reinstall":
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            if current_local:
                from superdoc_benchmark.superdoc.version import install_superdoc_local

                repo_root = Path(current_local)
                is_valid, version, package_path, error = validate_local_repo(repo_root)
                if not is_valid:
                    console.print(f"[red]Invalid repository:[/red] {error}\n")
                    return

                with console.status(f"[cyan]Building and re-installing superdoc from {repo_root}...", spinner="dots"):
                    install_superdoc_local(package_path, repo_root=repo_root)

                console.print(f"[green]Done![/green] Re-installed local SuperDoc {version} from {repo_root}\n")
            else:
                with console.status(f"[cyan]Re-installing superdoc@{current_version}...", spinner="dots"):
                    install_superdoc_version(current_version)
                    actual_version = get_installed_version()
                    set_superdoc_version(actual_version or current_version)

                console.print(f"[green]Done![/green] Re-installed SuperDoc {actual_version or current_version}\n")

        except Exception as exc:
            console.print(f"[red]Re-installation failed:[/red] {exc}\n")
        return

    if action == "latest":
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            # Resolve 'latest' tag to actual version first
            console.print("[dim]Resolving latest version from npm...[/dim]")
            resolved_version = resolve_npm_tag("superdoc", "latest")
            console.print(f"[dim]Latest version: {resolved_version}[/dim]")

            with console.status(f"[cyan]Installing superdoc@{resolved_version}...", spinner="dots"):
                install_superdoc_version("latest")
                set_superdoc_version(resolved_version)

            console.print(f"[green]Done![/green] SuperDoc {resolved_version} is now active.\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")

    elif action == "next":
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            # Resolve 'next' tag to actual version first
            console.print("[dim]Resolving next version from npm...[/dim]")
            resolved_version = resolve_npm_tag("superdoc", "next")
            console.print(f"[dim]Next version: {resolved_version}[/dim]")

            with console.status(f"[cyan]Installing superdoc@{resolved_version}...", spinner="dots"):
                install_superdoc_version("next")
                set_superdoc_version(resolved_version)

            console.print(f"[green]Done![/green] SuperDoc {resolved_version} is now active.\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")

    elif action == "npm":
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            version = inquirer.text(
                message="Enter SuperDoc version:",
                default="",
                qmark="🦋",
                amark="🦋",
                instruction="(ctrl+c to go back)",
            ).execute()
        except KeyboardInterrupt:
            version = None

        if not version:
            console.print("[dim]Cancelled[/dim]\n")
            return

        version = version.strip()

        console.print(f"\n[dim]Will install superdoc@{version} from npm...[/dim]")

        try:
            with console.status(f"[cyan]Installing superdoc@{version}...", spinner="dots"):
                install_superdoc_version(version)
                actual_version = get_installed_version()
                set_superdoc_version(actual_version or version)

            console.print(f"[green]Done![/green] SuperDoc {actual_version or version} is now active.\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")

    elif action == "local":
        try:
            path_str = inquirer.filepath(
                message="Enter path to SuperDoc repository:",
                default="",
                qmark="🦋",
                amark="🦋",
                instruction="(ctrl+c to go back)",
            ).execute()
        except KeyboardInterrupt:
            path_str = None

        if path_str:
            path_str = path_str.strip()

        if not path_str:
            console.print("[dim]Cancelled[/dim]\n")
            return

        path = validate_path(path_str)
        if path is None:
            console.print("[red]Invalid path[/red]\n")
            return

        is_valid, version, package_path, error = validate_local_repo(path)

        if not is_valid:
            console.print(f"[red]Invalid repository:[/red] {error}\n")
            return

        if package_path != path:
            console.print(f"[dim]Detected package at: {package_path}[/dim]")

        from superdoc_benchmark.superdoc.version import install_superdoc_local

        try:
            with console.status(f"[cyan]Building and installing superdoc from {path}...", spinner="dots"):
                install_superdoc_local(package_path, repo_root=path)
                set_superdoc_local_path(path)

            console.print(f"[green]Done![/green] Using local SuperDoc {version} from {path}\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")


def handle_check_updates() -> None:
    """Handle the Check for updates option (interactive)."""
    console.print()
    try:
        from superdoc_benchmark.update import compare_versions, get_latest_version, run_update
    except Exception as exc:
        console.print(f"[red]Update check failed:[/red] {exc}\n")
        return

    latest = get_latest_version()
    if not latest:
        console.print("[red]Unable to check for updates (npm unavailable or offline).[/red]\n")
        return

    if compare_versions(latest, __version__) <= 0:
        if latest != __version__:
            console.print(
                f"[dim]Latest on npm: {latest} (current: {__version__}).[/dim]\n"
            )
        else:
            console.print("[dim]You are on the latest version.[/dim]\n")
        return

    console.print(
        f"[yellow]New version available:[/yellow] {latest} (current: {__version__})"
    )
    try:
        should_update = inquirer.confirm(
            message="Update now with npm?",
            default=True,
            qmark="🦋",
            amark="🦋",
        ).execute()
    except KeyboardInterrupt:
        console.print("[dim]Cancelled[/dim]\n")
        return

    if not should_update:
        console.print(
            "[dim]Skipped. Run `npm update -g @superdoc-dev/visual-benchmarks` anytime.[/dim]\n"
        )
        return

    try:
        with console.status("[cyan]Updating via npm...", spinner="dots"):
            run_update()
    except Exception as exc:
        console.print(f"[red]Update failed:[/red] {exc}\n")
        return

    console.print(
        "[green]Updated successfully![/green] Please re-run your command.\n"
    )
    raise typer.Exit(0)


def interactive_mode() -> None:
    """Run the interactive menu-driven interface."""
    maybe_check_for_cli_update()
    show_welcome()

    while True:
        try:
            choice = show_main_menu()

            if choice is None:
                console.print("[dim]Goodbye![/dim]")
                break
            elif choice == "compare_docx":
                handle_compare_docx()
            elif choice == "set_superdoc_version":
                handle_set_superdoc_version()
            elif choice == "check_updates":
                handle_check_updates()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled[/dim]\n")
            continue


# =============================================================================
# CLI Commands
# =============================================================================

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show superdoc-benchmark version and exit",
    ),
) -> None:
    """SuperDoc visual benchmarking tool.

    Run without arguments for interactive mode.
    """
    if version:
        console.print(__version__)
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        interactive_mode()


@app.command("word")
def cmd_word(
    path: Path = typer.Argument(..., help="Path to .docx file or folder"),
    dpi: int = typer.Option(144, "--dpi", "-d", help="DPI for rasterization"),
    force: bool = typer.Option(False, "--force", "-f", help="Override existing captures"),
) -> None:
    """Capture Word visuals for .docx files."""
    from superdoc_benchmark.utils import find_docx_files
    from superdoc_benchmark.word import capture_word_visuals

    if not path.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        raise typer.Exit(1)

    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]")
        raise typer.Exit(1)

    console.print(f"[dim]Processing {len(docx_files)} .docx file(s)...[/dim]")
    capture_word_visuals(docx_files, dpi=dpi, force=force)


def _process_baseline_uploads(
    results: list[dict],
    key_by_path: dict[Path, str],
    r2_config: "R2Config",
    filter_name: str | None,
    dry_run: bool,
    client: "S3Client",
) -> list[tuple[Path | None, str]]:
    """Process and upload baseline captures for each result.

    Returns list of (docx_path, error_message) tuples for any failures.
    """
    from superdoc_benchmark.baselines.r2_upload import upload_word_baseline_capture

    errors: list[tuple[Path | None, str]] = []
    for result in results:
        docx_path = result.get("docx_path")
        word_dir = result.get("output_dir")
        if not docx_path or not word_dir:
            errors.append((docx_path, "Missing capture output metadata"))
            continue

        r2_key = key_by_path.get(docx_path, docx_path.name)
        action = "Checking" if dry_run else "Uploading"
        console.print(f"[cyan]{action} baselines for {r2_key}...[/cyan]")
        try:
            summary = upload_word_baseline_capture(
                docx_path,
                word_dir,
                r2_config,
                filter_name,
                docx_key=r2_key,
                dry_run=dry_run,
                client=client,
            )
            bucket = summary.get("bucket") or "unknown"
            prefix = summary.get("prefix") or "unknown"
            if dry_run:
                existing = summary.get("existing", 0)
                missing = len(summary.get("missing", []))
                extra = len(summary.get("extra", []))
                console.print(
                    f"  [yellow]Dry run:[/yellow] s3://{bucket}/{prefix}/ "
                    f"(existing: {existing}, missing: {missing}, extra: {extra})"
                )
            else:
                uploaded = summary.get("uploaded", 0)
                deleted = summary.get("deleted", 0)
                console.print(
                    f"  [green]Uploaded[/green] {r2_key} -> "
                    f"s3://{bucket}/{prefix}/ (files: {uploaded}, deleted: {deleted})"
                )
        except Exception as exc:
            errors.append((docx_path, str(exc)))
            console.print(f"  [red]Upload failed:[/red] {r2_key}: {exc}")

    return errors


@app.command("baseline")
def cmd_baseline(
    r2_path: Optional[str] = typer.Argument(
        None, help="R2 key or prefix for .docx files (defaults to --filter)"
    ),
    filter_name: Optional[str] = typer.Option(
        None,
        "--filter",
        help="R2 folder prefix for baselines (e.g. lists, tables)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Rebuild and overwrite baselines even if they already exist",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Capture and check R2 without uploading",
    ),
) -> None:
    """Capture Word baselines and upload to R2."""
    from superdoc_benchmark.baselines.r2_upload import (
        baseline_exists,
        build_baseline_prefix,
        create_r2_client,
        download_docx_keys,
        load_r2_config,
        normalize_filter,
        resolve_docx_keys,
    )
    from superdoc_benchmark.word import capture_word_visuals

    try:
        r2_config = load_r2_config()
    except RuntimeError as exc:
        console.print(f"[red]R2 config error:[/red] {exc}")
        raise typer.Exit(1)

    # Create R2 client once and reuse for all operations
    client = create_r2_client(r2_config)

    if filter_name is not None:
        try:
            filter_name = normalize_filter(filter_name)
        except RuntimeError as exc:
            console.print(f"[red]Invalid filter:[/red] {exc}")
            raise typer.Exit(1)

    if not r2_path and filter_name:
        r2_path = filter_name

    try:
        docx_keys = resolve_docx_keys(r2_config, r2_path, client=client)
    except RuntimeError as exc:
        console.print(f"[red]R2 docx error:[/red] {exc}")
        raise typer.Exit(1)

    keys_to_process = []
    skipped = []
    if force:
        keys_to_process = docx_keys
    else:
        for key in docx_keys:
            prefix = build_baseline_prefix(filter_name, Path(key), docx_key=key)
            try:
                exists = baseline_exists(r2_config, prefix, client=client)
            except Exception as exc:
                console.print(f"[red]Baseline check failed:[/red] {key}: {exc}")
                raise typer.Exit(1)
            if exists:
                skipped.append(key)
            else:
                keys_to_process.append(key)

    if skipped:
        console.print(
            f"[dim]Skipping {len(skipped)} .docx file(s) with existing baselines.[/dim]"
        )

    if not keys_to_process:
        console.print("[green]No new baselines to generate.[/green]")
        return

    console.print(
        f"[dim]Downloading {len(keys_to_process)} .docx file(s) from superdoc-labs...[/dim]"
    )
    temp_dir = None
    try:
        docx_files, temp_dir = download_docx_keys(r2_config, keys_to_process, client=client)
        key_by_path = {path: key for path, key in zip(docx_files, keys_to_process)}

        console.print(f"[dim]Processing {len(docx_files)} .docx file(s)...[/dim]")
        results = capture_word_visuals(docx_files, force=True)

        if len(results) != len(docx_files):
            console.print(
                "[red]Baseline capture failed for one or more documents. Aborting upload.[/red]"
            )
            raise typer.Exit(1)

        errors = _process_baseline_uploads(
            results, key_by_path, r2_config, filter_name, dry_run, client
        )

        if errors:
            console.print(
                f"[red]Baseline upload failed for {len(errors)} document(s).[/red]"
            )
            raise typer.Exit(1)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


@app.command("compare")
def cmd_compare(
    path: Path = typer.Argument(..., help="Path to .docx file or folder"),
    superdoc_version: Optional[str] = typer.Option(
        None,
        "--superdoc-version",
        help="SuperDoc version to install and use (e.g., 1.5.0, latest, next)",
    ),
    superdoc_local: Optional[Path] = typer.Option(
        None,
        "--superdoc-local",
        help="Path to local SuperDoc repository to install and use",
    ),
    skip_build: bool = typer.Option(
        False,
        "--skip-build",
        "--no-build",
        help="Skip pnpm build when installing from --superdoc-local",
    ),
    skip_reports: bool = typer.Option(
        False,
        "--skip-reports",
        help="Skip report generation (captures only)",
    ),
) -> None:
    """Compare Word and SuperDoc rendering for .docx files."""
    from superdoc_benchmark.utils import find_docx_files
    from superdoc_benchmark.superdoc.config import get_config, set_superdoc_local_path, set_superdoc_version
    from superdoc_benchmark.superdoc.version import (
        install_superdoc_local,
        install_superdoc_version,
        is_npm_available,
        resolve_npm_tag,
        validate_local_repo,
    )

    if not path.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        raise typer.Exit(1)

    if superdoc_version and superdoc_local:
        console.print("[red]Use either --superdoc-version or --superdoc-local (not both).[/red]")
        raise typer.Exit(1)

    if superdoc_local:
        if not superdoc_local.exists():
            console.print(f"[red]Path not found:[/red] {superdoc_local}")
            raise typer.Exit(1)
        is_valid, ver, package_path, error = validate_local_repo(superdoc_local)
        if not is_valid:
            console.print(f"[red]Invalid repository:[/red] {error}")
            raise typer.Exit(1)
        try:
            status_label = "Installing superdoc from"
            if not skip_build:
                status_label = "Building and installing superdoc from"
            with console.status(
                f"[cyan]{status_label} {superdoc_local}...", spinner="dots"
            ):
                install_superdoc_local(
                    package_path,
                    repo_root=superdoc_local,
                    skip_build=skip_build,
                )
                set_superdoc_local_path(superdoc_local)
            console.print(f"[green]Using local SuperDoc {ver} from {superdoc_local}[/green]")
        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}")
            raise typer.Exit(1)
    elif superdoc_version:
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]")
            raise typer.Exit(1)
        try:
            resolved_version = superdoc_version
            if superdoc_version in ("latest", "next"):
                console.print(f"[dim]Resolving {superdoc_version} version from npm...[/dim]")
                resolved_version = resolve_npm_tag("superdoc", superdoc_version)
                console.print(f"[dim]{superdoc_version.capitalize()} version: {resolved_version}[/dim]")

            with console.status(
                f"[cyan]Installing superdoc@{resolved_version}...", spinner="dots"
            ):
                install_superdoc_version(superdoc_version)
                set_superdoc_version(resolved_version)
            console.print(f"[green]Using SuperDoc {resolved_version}[/green]")
        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}")
            raise typer.Exit(1)
    else:
        config = get_config()
        if not config.get("superdoc_version") and not config.get("superdoc_local_path"):
            console.print("[red]SuperDoc is not configured.[/red]")
            console.print("[dim]Run: superdoc-benchmark version set <version>[/dim]")
            raise typer.Exit(1)

    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]")
        raise typer.Exit(1)

    run_compare(docx_files, root_path=path, skip_reports=skip_reports)


@app.command("uninstall")
def cmd_uninstall(
    remove_outputs: bool = typer.Option(
        False,
        "--remove-outputs",
        help="Also remove captures/ and reports/ in the current directory",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Remove local SuperDoc Benchmark data and caches."""
    import shutil

    from superdoc_benchmark.superdoc.config import CONFIG_DIR

    targets = [
        CONFIG_DIR,
        Path.home() / "Library" / "Caches" / "ms-playwright",
    ]
    if remove_outputs:
        targets.extend([Path.cwd() / "captures", Path.cwd() / "reports"])

    existing = [path for path in targets if path.exists()]
    if not existing:
        console.print("[dim]Nothing to remove.[/dim]")
        return

    console.print("[bold]This will remove:[/bold]")
    for path in existing:
        console.print(f"  [dim]•[/dim] {path}")

    if not yes and not typer.confirm("Proceed?"):
        console.print("[dim]Cancelled[/dim]")
        return

    errors = []
    for path in existing:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except Exception as exc:
            errors.append((path, str(exc)))

    if errors:
        console.print("[red]Some paths could not be removed:[/red]")
        for path, err in errors:
            console.print(f"  [dim]•[/dim] {path}: {err}")
        raise typer.Exit(1)

    console.print("[green]Cleanup complete.[/green]")
    if not remove_outputs:
        console.print("[dim]Note: captures/ and reports/ were not removed.[/dim]")


# Version subcommand group
version_app = typer.Typer(help="Manage SuperDoc version")
app.add_typer(version_app, name="version")


@version_app.callback(invoke_without_command=True)
def version_callback(ctx: typer.Context) -> None:
    """Show or manage SuperDoc version."""
    if ctx.invoked_subcommand is None:
        # Show current version
        from superdoc_benchmark.superdoc.config import get_config
        from superdoc_benchmark.superdoc.version import get_installed_version

        config = get_config()
        current_version = config.get("superdoc_version")
        current_local = config.get("superdoc_local_path")
        installed = get_installed_version()

        console.print()
        if current_version:
            console.print(f"[bold]Configured:[/bold] {current_version} (npm)")
            if installed:
                console.print(f"[bold]Installed:[/bold]  {installed}")
        elif current_local:
            console.print(f"[bold]Configured:[/bold] local ({current_local})")
            if installed:
                console.print(f"[bold]Installed:[/bold]  {installed}")
        else:
            console.print("[yellow]SuperDoc is not configured.[/yellow]")
            console.print("[dim]Run: superdoc-benchmark version set <version>[/dim]")
        console.print()


@version_app.command("set")
def cmd_version_set(
    version: Optional[str] = typer.Argument(None, help="Version to install (e.g., 1.0.0, latest, next)"),
    local: Optional[Path] = typer.Option(None, "--local", "-l", help="Path to local SuperDoc repository"),
    skip_build: bool = typer.Option(
        False,
        "--skip-build",
        "--no-build",
        help="Skip pnpm build when using --local",
    ),
) -> None:
    """Set the SuperDoc version to use."""
    from superdoc_benchmark.superdoc.config import set_superdoc_version, set_superdoc_local_path
    from superdoc_benchmark.superdoc.version import (
        install_superdoc_version,
        install_superdoc_local,
        validate_local_repo,
        is_npm_available,
        resolve_npm_tag,
    )

    if local:
        # Install from local path
        if not local.exists():
            console.print(f"[red]Path not found:[/red] {local}")
            raise typer.Exit(1)

        is_valid, ver, package_path, error = validate_local_repo(local)
        if not is_valid:
            console.print(f"[red]Invalid repository:[/red] {error}")
            raise typer.Exit(1)

        try:
            status_label = "Installing superdoc from"
            if not skip_build:
                status_label = "Building and installing superdoc from"
            with console.status(f"[cyan]{status_label} {local}...", spinner="dots"):
                install_superdoc_local(
                    package_path,
                    repo_root=local,
                    skip_build=skip_build,
                )
                set_superdoc_local_path(local)

            console.print(f"[green]Done![/green] Using local SuperDoc {ver} from {local}")
        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}")
            raise typer.Exit(1)

    elif version:
        # Install from npm
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]")
            raise typer.Exit(1)

        try:
            # Resolve dist-tags (latest, next) to actual versions
            resolved_version = version
            if version in ("latest", "next"):
                console.print(f"[dim]Resolving {version} version from npm...[/dim]")
                resolved_version = resolve_npm_tag("superdoc", version)
                console.print(f"[dim]{version.capitalize()} version: {resolved_version}[/dim]")

            with console.status(f"[cyan]Installing superdoc@{resolved_version}...", spinner="dots"):
                install_superdoc_version(version)
                set_superdoc_version(resolved_version)

            console.print(f"[green]Done![/green] SuperDoc {resolved_version} is now active.")
        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}")
            raise typer.Exit(1)

    else:
        console.print("[red]Provide a version or use --local[/red]")
        console.print("[dim]Examples:[/dim]")
        console.print("[dim]  superdoc-benchmark version set latest[/dim]")
        console.print("[dim]  superdoc-benchmark version set 1.0.0[/dim]")
        console.print("[dim]  superdoc-benchmark version set --local /path/to/repo[/dim]")
        raise typer.Exit(1)


def _init_playwright() -> None:
    """Initialize Playwright browser at startup."""
    from superdoc_benchmark.superdoc.capture import ensure_playwright_browsers
    try:
        ensure_playwright_browsers()
    except Exception as e:
        console.print(f"[red]Warning:[/red] {e}")
        console.print("[dim]SuperDoc captures may not work until browser is installed.[/dim]\n")


def main() -> None:
    """Main entry point."""
    import multiprocessing

    multiprocessing.freeze_support()
    # Ensure Playwright browser is available at startup
    _init_playwright()
    app()


if __name__ == "__main__":
    main()
