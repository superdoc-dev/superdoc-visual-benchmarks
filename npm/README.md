# superdoc-benchmark (npm wrapper)

This npm package installs a lightweight wrapper and a bundled macOS binary.

## Requirements

- macOS (Apple Silicon)
- Microsoft Word
- Node.js (npm)

## Install

```bash
npm install -g @superdoc-dev/visual-benchmarks
```

## Run

```bash
superdoc-benchmark
superdoc-benchmark compare ./docs/
```

## Update

```bash
npm update -g @superdoc-dev/visual-benchmarks
```

## Publish (maintainers)

From the `npm/` folder:

```bash
npm run publish
```

## Troubleshooting

If the download fails, you can run from source instead:

```bash
git clone https://github.com/superdoc-dev/superdoc-visual-benchmarks
cd superdoc-visual-benchmarks
uv run superdoc-benchmark
```
