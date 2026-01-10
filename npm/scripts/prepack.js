"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..");
const distDir = path.join(repoRoot, "dist");
const vendorDir = path.join(__dirname, "..", "vendor");
const tarballs = ["superdoc-benchmark-darwin-arm64.tar.gz"];

function requireTarballs() {
  const missing = tarballs.filter(
    (name) => !fs.existsSync(path.join(distDir, name))
  );
  if (missing.length > 0) {
    throw new Error(
      `Missing tarballs in dist/: ${missing.join(", ")}. Build the arm64 artifact before publishing.`
    );
  }

  return tarballs;
}

function copyTarballs(names) {
  fs.rmSync(vendorDir, { recursive: true, force: true });
  fs.mkdirSync(vendorDir, { recursive: true });

  for (const name of names) {
    const src = path.join(distDir, name);
    const dst = path.join(vendorDir, name);
    fs.copyFileSync(src, dst);
    console.log(`Bundled ${name}`);
  }
}

try {
  const names = requireTarballs();
  copyTarballs(names);
} catch (err) {
  console.error(String(err.message || err));
  process.exit(1);
}
