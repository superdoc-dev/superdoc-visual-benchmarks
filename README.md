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
sudo mv ~/Downloads/superdoc-benchmark /usr/local/bin/
```

**From source:**

```bash
git clone https://github.com/superdoc-dev/superdoc-visual-benchmarks.git
cd superdoc-visual-benchmarks
uv sync
uv run superdoc-benchmark
```

## Usage

> **Note:** If running from source, prefix commands with `uv run` (e.g., `uv run superdoc-benchmark`).
> The binary from GitHub Releases can be run directly.

### Interactive Mode

Run with no arguments for the interactive menu:

```bash
superdoc-benchmark
```

### CLI Commands

For scripting and automation:

```bash
# Capture Word visuals
superdoc-benchmark word ./path/to/docs/
superdoc-benchmark word ./document.docx --dpi 200 --force

# Compare Word vs SuperDoc
superdoc-benchmark compare ./path/to/docs/

# Manage SuperDoc version
superdoc-benchmark version                            # show current
superdoc-benchmark version set latest                 # install latest from npm
superdoc-benchmark version set 1.0.0                  # install specific version
superdoc-benchmark version set --local /path/to/repo  # use local repo
```

### Output

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
