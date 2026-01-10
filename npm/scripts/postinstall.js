"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const VERSION = require("../package.json").version;

const platform = process.platform;
const arch = process.arch;

if (platform !== "darwin") {
  console.error("superdoc-benchmark only supports macOS");
  process.exit(1);
}

const archMap = { arm64: "arm64" };
const binaryArch = archMap[arch];

if (!binaryArch) {
  console.error(`Unsupported architecture: ${arch}`);
  process.exit(1);
}

const binDir = path.join(__dirname, "..", ".bin-cache");
const binaryPath = path.join(binDir, "superdoc-benchmark");
const vendorTarball = path.join(
  __dirname,
  "..",
  "vendor",
  `superdoc-benchmark-darwin-${binaryArch}.tar.gz`
);

function extractTarball(tarballPath) {
  execSync(`tar -xzf "${tarballPath}" -C "${binDir}"`, {
    stdio: "inherit",
  });
}

function download() {
  if (fs.existsSync(binaryPath)) {
    console.log("superdoc-benchmark binary already installed");
    return;
  }

  fs.mkdirSync(binDir, { recursive: true });

  try {
    if (!fs.existsSync(vendorTarball)) {
      throw new Error(
        "Bundled binary tarball not found in npm package. Rebuild the npm package with vendor tarballs."
      );
    }

    console.log(
      `Installing bundled superdoc-benchmark v${VERSION} for darwin-${binaryArch}...`
    );
    extractTarball(vendorTarball);

    if (!fs.existsSync(binaryPath)) {
      throw new Error("Binary was not found after extraction");
    }

    fs.chmodSync(binaryPath, 0o755);
    console.log("superdoc-benchmark installed successfully");
  } catch (err) {
    console.error(`Failed to install binary: ${err.message}`);
    console.error(
      `Expected bundled tarball: vendor/superdoc-benchmark-darwin-${binaryArch}.tar.gz`
    );
    console.error("\nYou can install from source instead:");
    console.error(
      "  git clone https://github.com/superdoc-dev/superdoc-visual-benchmarks"
    );
    console.error("  cd superdoc-visual-benchmarks && uv run superdoc-benchmark");
    process.exit(1);
  }
}

download();
