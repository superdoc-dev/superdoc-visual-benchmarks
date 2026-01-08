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
    from superdoc_benchmark.word import capture_word_visuals

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

    # Confirm before processing
    confirm = inquirer.confirm(
        message=f"Process {len(docx_files)} file(s)?",
        default=True,
        qmark="",
        amark="",
    ).execute()

    if not confirm:
        console.print("[dim]Cancelled[/dim]\n")
        return

    # Run the capture process
    capture_word_visuals(docx_files)


def handle_compare_docx() -> None:
    """Handle the Compare DOCX option."""
    console.print("\n[dim][Compare DOCX] - Not yet implemented[/dim]\n")


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
        Choice(value="back", name="Back to main menu"),
    ]

    action = inquirer.rawlist(
        message="How would you like to configure SuperDoc?",
        choices=choices,
        default="latest",
        qmark="🦋",
        amark="🦋",
    ).execute()

    if action == "back":
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
                default=current_version or "1.0.0",
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
                default=current_local or "",
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
        is_valid, version, error = validate_local_repo(path)

        if not is_valid:
            console.print(f"[red]Invalid repository:[/red] {error}\n")
            return

        # Save configuration
        set_superdoc_local_path(path)
        console.print(f"[green]Done![/green] Using local SuperDoc {version} at {path}\n")


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
