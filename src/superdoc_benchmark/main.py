"""Main entry point for superdoc-benchmark CLI."""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.text import Text

from superdoc_benchmark import __version__

console = Console()

# ASCII art logo - "SUPER" in dark teal, "DOC" in dark purple
# Using hex colors for a darker, more mysterious vibe
SUPER_COLOR = "#0E7490"  # dark teal/cyan
DOC_COLOR = "#7C3AED"    # dark violet/purple

LOGO_LINES = [
    # Each tuple: (text, style)
    # Line 1
    [("███████╗██╗   ██╗██████╗ ███████╗██████╗ ", SUPER_COLOR),
     ("██████╗  ██████╗  ██████╗", DOC_COLOR)],
    # Line 2
    [("██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗", SUPER_COLOR),
     ("██╔══██╗██╔═══██╗██╔════╝", DOC_COLOR)],
    # Line 3
    [("███████╗██║   ██║██████╔╝█████╗  ██████╔╝", SUPER_COLOR),
     ("██║  ██║██║   ██║██║     ", DOC_COLOR)],
    # Line 4
    [("╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗", SUPER_COLOR),
     ("██║  ██║██║   ██║██║     ", DOC_COLOR)],
    # Line 5
    [("███████║╚██████╔╝██║     ███████╗██║  ██║", SUPER_COLOR),
     ("██████╔╝╚██████╔╝╚██████╗", DOC_COLOR)],
    # Line 6
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

    # Butterfly (centered over ~66 char logo)
    console.print("                            ⟡ 🦋 ⟡", highlight=False)
    console.print()

    # Big ASCII logo
    console.print(get_logo())

    # Version and subtitle
    console.print()
    subtitle = Text()
    subtitle.append("  Benchmark", style=f"bold {SUPER_COLOR}")
    subtitle.append(" v" + __version__, style="dim")
    subtitle.append("  ◦  ", style="dim")
    subtitle.append("Visual comparison for document rendering", style="dim italic")
    console.print(subtitle)

    # Current SuperDoc version
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
    """Handle the Generate Word visual option."""
    from superdoc_benchmark.utils import find_docx_files, validate_path
    from superdoc_benchmark.word import capture_word_visuals, get_word_output_dir

    console.print()

    # Ask for file or folder path
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

    # Find all docx files
    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]\n")
        return

    # Show what we found
    if path.is_dir():
        console.print(f"[dim]Found {len(docx_files)} .docx file(s) in {path}[/dim]")
    else:
        console.print(f"[dim]Processing: {path.name}[/dim]")

    # Check which files already have captures
    existing_captures = []
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        if word_dir.exists() and list(word_dir.glob("page_*.png")):
            existing_captures.append(docx_path)

    # If captures exist, ask to override
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

    # Run the capture process
    capture_word_visuals(docx_files, force=True)


def handle_compare_docx() -> None:
    """Handle the Compare DOCX option."""
    from pathlib import Path

    from superdoc_benchmark.utils import find_docx_files, validate_path
    from superdoc_benchmark.word import (
        capture_single_document as capture_word_single,
        get_word_output_dir,
        get_document_dir,
    )
    from superdoc_benchmark.superdoc import (
        capture_superdoc_single,
        get_superdoc_output_dir,
        get_superdoc_version_label,
        get_installed_version,
        ViteServer,
        capture_superdoc_pages,
    )
    from superdoc_benchmark.superdoc.config import get_config

    console.print()

    # Check if SuperDoc is configured
    config = get_config()
    if not config.get("superdoc_version") and not config.get("superdoc_local_path"):
        console.print("[yellow]SuperDoc is not configured.[/yellow]")
        console.print("[dim]Use option 3 to set a SuperDoc version first.[/dim]\n")
        return

    # Get current SuperDoc version label
    version_label = get_superdoc_version_label()
    console.print(f"[dim]SuperDoc version: [cyan]{version_label}[/cyan][/dim]")

    # Ask for file or folder path
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

    # Find all docx files
    docx_files = find_docx_files(path)

    if not docx_files:
        console.print(f"[yellow]No .docx files found in {path}[/yellow]\n")
        return

    # Show what we found
    if path.is_dir():
        console.print(f"[dim]Found {len(docx_files)} .docx file(s) in {path}[/dim]")
    else:
        console.print(f"[dim]Processing: {path.name}[/dim]")

    console.print()

    # Check which files need Word screenshots (SuperDoc always recaptured)
    word_missing = []

    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        word_pages = list(word_dir.glob("page_*.png")) if word_dir.exists() else []
        if not word_pages:
            word_missing.append(docx_path)

    # Report status
    console.print("[bold]Capture status:[/bold]")
    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        superdoc_dir = get_superdoc_output_dir(docx_path)

        word_pages = list(word_dir.glob("page_*.png")) if word_dir.exists() else []
        superdoc_pages = list(superdoc_dir.glob("page_*.png")) if superdoc_dir.exists() else []

        word_status = f"[green]{len(word_pages)} pages[/green]" if word_pages else "[yellow]missing[/yellow]"
        sd_status = f"[dim]{len(superdoc_pages)} pages (will recapture)[/dim]" if superdoc_pages else "[yellow]missing[/yellow]"

        console.print(f"  [dim]•[/dim] {docx_path.name}: Word={word_status}, SuperDoc={sd_status}")

    console.print()

    # Capture missing Word screenshots
    if word_missing:
        console.print(f"📄 [cyan]Capturing Word screenshots for {len(word_missing)} file(s)...[/cyan]")
        from superdoc_benchmark.word import capture_word_visuals
        capture_word_visuals(word_missing)

    # Always capture SuperDoc screenshots (for current version)
    console.print(f"🦋 [cyan]Capturing SuperDoc ({version_label}) screenshots for {len(docx_files)} file(s)...[/cyan]")
    from superdoc_benchmark.superdoc import capture_superdoc_visuals
    capture_superdoc_visuals(docx_files)

    # Generate comparison reports
    console.print(f"📊 [cyan]Generating comparison reports...[/cyan]")
    from superdoc_benchmark.compare import generate_reports

    report_results = []
    report_errors = []

    for docx_path in docx_files:
        word_dir = get_word_output_dir(docx_path)
        superdoc_dir = get_superdoc_output_dir(docx_path)

        try:
            result = generate_reports(
                docx_name=docx_path.stem,
                word_dir=word_dir,
                superdoc_dir=superdoc_dir,
                version_label=version_label,
            )
            report_results.append((docx_path, result))
        except Exception as exc:
            report_errors.append((docx_path, str(exc)))

    # Summary
    console.print()
    cwd = Path.cwd()
    if report_results:
        console.print(f"[green]Generated reports for {len(report_results)} document(s)[/green]")
        for docx_path, result in report_results:
            comparison_path = result["comparison_pdf"]
            diff_path = result["diff_pdf"]
            try:
                comparison_rel = comparison_path.relative_to(cwd)
                diff_rel = diff_path.relative_to(cwd)
            except ValueError:
                comparison_rel = comparison_path
                diff_rel = diff_path
            console.print(f"  [dim]•[/dim] {docx_path.name}:")
            console.print(f"      comparison: [cyan]./{comparison_rel}[/cyan]")
            console.print(f"      diff: [cyan]./{diff_rel}[/cyan]")

    if report_errors:
        console.print(f"\n[red]Failed to generate reports for {len(report_errors)} document(s)[/red]")
        for path, err in report_errors:
            console.print(f"  [dim]•[/dim] {path.name}: {err}")

    console.print()


def handle_set_superdoc_version() -> None:
    """Handle the Set SuperDoc version option."""
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

    # Show current configuration
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

    # Submenu for configuration options
    choices = [
        Choice(value="latest", name="Install 'latest'"),
        Choice(value="next", name="Install 'next'"),
        Choice(value="npm", name="Install from NPM (e.g., 1.0.0)"),
        Choice(value="local", name="Use local repository"),
    ]

    # Add re-install option if there's a current version
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
        # Re-install current configuration
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        try:
            if current_local:
                # Re-install from local path
                from superdoc_benchmark.superdoc.version import install_superdoc_local
                from pathlib import Path

                repo_root = Path(current_local)

                # Re-validate to get package path
                is_valid, version, package_path, error = validate_local_repo(repo_root)
                if not is_valid:
                    console.print(f"[red]Invalid repository:[/red] {error}\n")
                    return

                with console.status(f"[cyan]Building and re-installing superdoc from {repo_root}...", spinner="dots"):
                    install_superdoc_local(package_path, repo_root=repo_root)

                console.print(f"[green]Done![/green] Re-installed local SuperDoc {version} from {repo_root}\n")
            else:
                # Re-install npm version
                with console.status(f"[cyan]Re-installing superdoc@{current_version}...", spinner="dots"):
                    install_superdoc_version(current_version)
                    actual_version = get_installed_version()
                    set_superdoc_version(actual_version or current_version)

                console.print(f"[green]Done![/green] Re-installed SuperDoc {actual_version or current_version}\n")

        except Exception as exc:
            console.print(f"[red]Re-installation failed:[/red] {exc}\n")
        return

    if action == "latest":
        # Install latest tag
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
        # Install next tag
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
        # Check npm availability
        if not is_npm_available():
            console.print("[red]npm is not installed. Please install Node.js first.[/red]\n")
            return

        # Ask for version
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

        # Confirm installation
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
        # Ask for path
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

        # Validate the repo
        is_valid, version, package_path, error = validate_local_repo(path)

        if not is_valid:
            console.print(f"[red]Invalid repository:[/red] {error}\n")
            return

        # Show detected package path
        if package_path != path:
            console.print(f"[dim]Detected package at: {package_path}[/dim]")

        # Install from local path
        from superdoc_benchmark.superdoc.version import install_superdoc_local

        try:
            with console.status(f"[cyan]Building and installing superdoc from {path}...", spinner="dots"):
                install_superdoc_local(package_path, repo_root=path)
                # Store the repo root (user's input) so we can rebuild on reinstall
                set_superdoc_local_path(path)

            console.print(f"[green]Done![/green] Using local SuperDoc {version} from {path}\n")

        except Exception as exc:
            console.print(f"[red]Installation failed:[/red] {exc}\n")


def main() -> None:
    """Main entry point."""
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


if __name__ == "__main__":
    main()
