# SuperDoc Benchmark

Visual comparison tool for SuperDoc document rendering. Compares how SuperDoc renders `.docx` files against Microsoft Word's output.

## Requirements

- macOS (uses AppleScript for Word automation)
- Microsoft Word
- Node.js / npm (for SuperDoc installation)

## Installation

**From GitHub Releases (recommended):**

Download the latest binary from [Releases](../../releases), then:

```bash
chmod +x ~/Downloads/superdoc-benchmark
./superdoc-benchmark
```

**From source:**

```bash
git clone https://github.com/superdoc-dev/superdoc-visual-benchmarks.git
cd superdoc-visual-benchmarks
uv sync
uv run superdoc-benchmark
```

## Usage

Run `superdoc-benchmark` to launch the interactive menu:

1. **Generate Word visual** - Export `.docx` files to PDF via Word, then rasterize to PNGs
2. **Compare DOCX** - Capture both Word and SuperDoc renders, generate side-by-side comparison reports
3. **Set SuperDoc version** - Install from npm (`latest`, `next`, or specific version) or use a local repo

Output is saved to:
- `captures/<document>/word/` - Word renders
- `captures/<document>/superdoc/` - SuperDoc renders
- `reports/` - Comparison PDFs

## Development

```bash
uv sync
uv run superdoc-benchmark
```

**Build binary:**

```bash
uv run pyinstaller superdoc-benchmark.spec
# Output: dist/superdoc-benchmark
```

**Release:**

```bash
./scripts/release.sh 0.1.0
```

## License

MIT
