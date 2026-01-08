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
        superdoc_status.append(" (use option 3 to set)", style="dim")
    console.print(superdoc_status)
    console.print()


def show_main_menu() -> str | None:
    """Display the main menu and return the selected option."""
    choices = [
        Choice(value="generate_word_visual", name="Generate Word visual"),
        Choice(value="compare_docx", name="Compare DOCX"),
        Choice(value="set_superdoc_version", name="Set SuperDoc version"),
        Choice(value=None, name="Exit"),
    ]

    result = inquirer.rawlist(
        message="Select an option:",
        choices=choices,
        default="generate_word_visual",
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
        console.print("[dim]Use option 3 to set a SuperDoc version first.[/dim]\n")
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

    run_compare(docx_files)


def _generate_report_task(
    docx_path: Path,
    word_dir: Path,
    superdoc_dir: Path,
    version_label: str,
) -> dict:
    """Worker function for parallel report generation.

    This is a module-level function so it can be pickled for ProcessPoolExecutor.
    """
    from superdoc_benchmark.compare import generate_reports

    return generate_reports(
        docx_name=docx_path.stem,
        word_dir=word_dir,
        superdoc_dir=superdoc_dir,
        version_label=version_label,
    )


def run_compare(docx_files: list[Path]) -> None:
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
    from superdoc_benchmark.compare import generate_reports

    version_label = get_superdoc_version_label()
    config = get_config()
    is_local = config.get("superdoc_local_path") is not None

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
        capture_word_visuals(word_missing)

    # Capture SuperDoc screenshots (missing only for npm, all for local)
    if superdoc_missing:
        if is_local:
            console.print(f"🦋 [cyan]Capturing SuperDoc ({version_label}) screenshots for {len(superdoc_missing)} file(s) (local - always recapture)...[/cyan]")
        else:
            console.print(f"🦋 [cyan]Capturing SuperDoc ({version_label}) screenshots for {len(superdoc_missing)} file(s)...[/cyan]")
        capture_superdoc_visuals(superdoc_missing)
    else:
        console.print(f"🦋 [dim]SuperDoc captures exist for all files (npm version - skipping)[/dim]")

    # Generate comparison reports (parallel for multiple files)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    import os

    report_results = []
    report_errors = []

    console.print()

    # Prepare arguments for parallel execution
    report_args = []
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        superdoc_dir = get_superdoc_output_dir(docx_path)
        report_args.append((docx_path, word_dir, superdoc_dir, version_label))

    # Use parallel processing for multiple files, sequential for single file
    max_workers = min(len(docx_files), max(1, os.cpu_count() - 1)) if len(docx_files) > 1 else 1

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        report_task = progress.add_task(
            "[cyan]Generating comparison reports...", total=len(docx_files)
        )

        if max_workers == 1:
            # Sequential processing for single file
            for docx_path, word_dir, superdoc_dir, ver_label in report_args:
                progress.update(
                    report_task,
                    description=f"[cyan]Generating report: [white]{docx_path.name}",
                )
                try:
                    result = generate_reports(
                        docx_name=docx_path.stem,
                        word_dir=word_dir,
                        superdoc_dir=superdoc_dir,
                        version_label=ver_label,
                    )
                    report_results.append((docx_path, result))
                except Exception as exc:
                    report_errors.append((docx_path, str(exc)))
                    console.print(f"  [red]Error:[/red] {docx_path.name}: {exc}")
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
                        docx_path,
                        word_dir,
                        superdoc_dir,
                        ver_label,
                    ): docx_path
                    for docx_path, word_dir, superdoc_dir, ver_label in report_args
                }

                # Collect results as they complete
                for future in as_completed(future_to_path):
                    docx_path = future_to_path[future]
                    try:
                        result = future.result()
                        report_results.append((docx_path, result))
                    except Exception as exc:
                        report_errors.append((docx_path, str(exc)))
                        console.print(f"  [red]Error:[/red] {docx_path.name}: {exc}")
                    progress.advance(report_task)

    # Summary
    console.print()
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

    if report_errors:
        console.print(f"\n[red]Failed to generate reports for {len(report_errors)} document(s)[/red]")
        for path, err in report_errors:
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
            with console.status("[cyan]Installing superdoc@latest...", spinner="dots"):
                install_superdoc_version("latest")
                actual_version = get_installed_version()
                set_superdoc_version(actual_version or "latest")

            console.print(f"[green]Done![/green] SuperDoc {actual_version or 'latest'} is now active.\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")

    elif action == "next":
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            with console.status("[cyan]Installing superdoc@next...", spinner="dots"):
                install_superdoc_version("next")
                actual_version = get_installed_version()
                set_superdoc_version(actual_version or "next")

            console.print(f"[green]Done![/green] SuperDoc {actual_version or 'next'} is now active.\n")

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


def interactive_mode() -> None:
    """Run the interactive menu-driven interface."""
    show_welcome()

    while True:
        try:
            choice = show_main_menu()

            if choice is None:
                console.print("[dim]Goodbye![/dim]")
                break
            elif choice == "generate_word_visual":
                handle_generate_word_visual()
            elif choice == "compare_docx":
                handle_compare_docx()
            elif choice == "set_superdoc_version":
                handle_set_superdoc_version()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled[/dim]\n")
            continue


# =============================================================================
# CLI Commands
# =============================================================================

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """SuperDoc visual benchmarking tool.

    Run without arguments for interactive mode.
    """
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


@app.command("compare")
def cmd_compare(
    path: Path = typer.Argument(..., help="Path to .docx file or folder"),
) -> None:
    """Compare Word and SuperDoc rendering for .docx files."""
    from superdoc_benchmark.utils import find_docx_files
    from superdoc_benchmark.superdoc.config import get_config

    if not path.exists():
        console.print(f"[red]Path not found:[/red] {path}")
        raise typer.Exit(1)

    config = get_config()
    if not config.get("superdoc_version") and not config.get("superdoc_local_path"):
        console.print("[red]SuperDoc is not configured.[/red]")
        console.print("[dim]Run: superdoc-benchmark version set <version>[/dim]")
        raise typer.Exit(1)

    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]")
        raise typer.Exit(1)

    run_compare(docx_files)


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
) -> None:
    """Set the SuperDoc version to use."""
    from superdoc_benchmark.superdoc.config import set_superdoc_version, set_superdoc_local_path
    from superdoc_benchmark.superdoc.version import (
        install_superdoc_version,
        install_superdoc_local,
        validate_local_repo,
        get_installed_version,
        is_npm_available,
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
            with console.status(f"[cyan]Building and installing superdoc from {local}...", spinner="dots"):
                install_superdoc_local(package_path, repo_root=local)
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
            with console.status(f"[cyan]Installing superdoc@{version}...", spinner="dots"):
                install_superdoc_version(version)
                actual_version = get_installed_version()
                set_superdoc_version(actual_version or version)

            console.print(f"[green]Done![/green] SuperDoc {actual_version or version} is now active.")
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


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
