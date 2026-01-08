# SuperDoc Benchmark

Visual comparison tool for SuperDoc document rendering. Compares how SuperDoc renders `.docx` files against Microsoft Word's output.

## Requirements

> **This tool only works on macOS with Microsoft Word installed.**

| Requirement | Why |
|-------------|-----|
| **macOS** | Uses AppleScript to automate Word |
| **Microsoft Word** | Generates the "ground truth" PDF renders |
| **Node.js / npm** | Installs and runs SuperDoc |

## Installation

**From GitHub Releases (recommended):**

Download `superdoc-benchmark-macos.zip` from [Releases](../../releases), then:

```bash
# Extract and move to PATH
unzip ~/Downloads/superdoc-benchmark-macos.zip -d ~/Downloads
sudo mv ~/Downloads/superdoc-benchmark /usr/local/bin/

# macOS security: remove quarantine attribute
xattr -d com.apple.quarantine /usr/local/bin/superdoc-benchmark

# First run: install Playwright browser (one-time)
npx playwright install chromium
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

All outputs are saved to the `reports/` directory:

- `reports/word-captures/<document>/` - Word renders (PDF + page images)
- `reports/superdoc-captures/<document>-<version>/` - SuperDoc renders
- `reports/comparisons/<document>/` - Side-by-side comparison PDFs and `score-*.json` files

## How Scoring Works

Each page is compared pixel-by-pixel between Word and SuperDoc renders. The score (0-100) is a weighted combination of:

| Metric | Weight | What it measures |
|--------|--------|------------------|
| **SSIM** | 40% | Structural similarity (layout, shapes) |
| **Ink Match** | 20% | Whether text/graphics appear in the same places |
| **Edge Match** | 15% | Whether lines and boundaries align |
| **Color Match** | 15% | Whether colors are accurate |
| **Blob Penalty** | 10% | Penalizes large missing or extra content |

Before scoring, images are automatically aligned to handle minor position differences. The tool also detects "single issue" pages where only vertical spacing differs (common with fonts) and adjusts scoring accordingly.

**Overall document score** = 70% average + 30% worst page (so one bad page hurts but doesn't ruin everything).

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
