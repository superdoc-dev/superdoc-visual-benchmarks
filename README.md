# SuperDoc Benchmark

Visual comparison tool for SuperDoc document rendering. Compares how SuperDoc renders `.docx` files against Microsoft Word's output.

## Requirements

> **This tool only works on macOS with Microsoft Word installed.**

| Requirement | Why |
|-------------|-----|
| **macOS** | Uses AppleScript to automate Word |
| **Microsoft Word** | Generates the "ground truth" PDF renders |
| **Node.js / npm** | Installs and runs SuperDoc |
| **pnpm** | Only needed if using a local SuperDoc repo |

## Installation

### From GitHub Releases (recommended)

Download `superdoc-benchmark-macos.zip` from [Releases](../../releases), then:

```bash
# Extract and move to PATH
unzip ~/Downloads/superdoc-benchmark-macos.zip -d ~/Downloads
sudo mv ~/Downloads/superdoc-benchmark /usr/local/bin/

# macOS security: remove quarantine attribute
xattr -d com.apple.quarantine /usr/local/bin/superdoc-benchmark
```

On first run, the app will automatically install the Playwright browser. If that fails, install manually:

```bash
npx playwright install chromium
```

### From source

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv) (Python package manager).

```bash
git clone https://github.com/superdoc-dev/superdoc-visual-benchmarks.git
cd superdoc-visual-benchmarks
uv sync
uv run superdoc-benchmark
```

## First Run

On first use:
1. **macOS will ask for permission** to control Microsoft Word - click "OK" to allow
2. **Playwright browser** will be downloaded automatically (~150MB, one-time)

## Usage

> **Note:** If running from source, prefix commands with `uv run` (e.g., `uv run superdoc-benchmark`).

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
superdoc-benchmark version set next                   # install next (pre-release) from npm
superdoc-benchmark version set 1.0.0                  # install specific version
superdoc-benchmark version set --local /path/to/repo  # use local repo (requires pnpm)
```

## Output

All outputs are saved to a `reports/` folder in your current working directory:

```
reports/
├── word-captures/<document>/
│   ├── <document>.pdf          # PDF exported from Word
│   └── page_0001.png ...       # Rasterized pages
├── superdoc-captures/<document>-<version>/
│   └── page_0001.png ...       # Screenshots from SuperDoc
└── comparisons/<document>/
    ├── comparison-<version>.pdf  # Side-by-side: Word | SuperDoc
    ├── diff-<version>.pdf        # Diff overlay: Word | colored differences
    └── score-<version>.json      # Similarity scores
```

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

## Data Locations

| What | Location |
|------|----------|
| Config | `~/.superdoc-benchmark/config.json` |
| SuperDoc workspace | `~/.superdoc-benchmark/workspace/` |
| Playwright browsers | `~/Library/Caches/ms-playwright/` |

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
