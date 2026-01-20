#!/usr/bin/env node
"use strict";

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const BIN_CACHE = path.join(__dirname, "..", ".bin-cache");

function main() {
  const binaryPath = path.join(BIN_CACHE, "superdoc-benchmark", "superdoc-benchmark");

  if (!fs.existsSync(binaryPath)) {
    console.error("Binary not found. Try reinstalling:");
    console.error(
      "  npm uninstall -g @superdoc-dev/visual-benchmarks && npm install -g @superdoc-dev/visual-benchmarks"
    );
    process.exit(1);
  }

  const child = spawn(binaryPath, process.argv.slice(2), {
    stdio: "inherit",
    env: process.env,
  });

  child.on("error", (err) => {
    console.error(`Failed to run superdoc-benchmark: ${err.message}`);
    process.exit(1);
  });

  child.on("exit", (code) => {
    process.exit(code ?? 0);
  });
}

main();
