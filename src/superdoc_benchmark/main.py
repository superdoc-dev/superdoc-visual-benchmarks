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
    path_str = inquirer.filepath(
        message="Enter path to .docx file or folder:",
        default="",
        validate=lambda p: validate_path(p) is not None,
        invalid_message="Path does not exist",
        qmark="",
        amark="",
    ).execute()

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
    console.print("\n[dim][Set SuperDoc version] - Not yet implemented[/dim]\n")


def main() -> None:
    """Main entry point."""
    show_welcome()

    while True:
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


if __name__ == "__main__":
    main()
