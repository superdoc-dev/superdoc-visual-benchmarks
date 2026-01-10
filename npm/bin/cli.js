#!/usr/bin/env node
"use strict";

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");
const http = require("http");
const https = require("https");
const readline = require("readline");

const PACKAGE_NAME = "@superdoc-dev/visual-benchmarks";
const CURRENT_VERSION = require("../package.json").version;
const BIN_CACHE = path.join(__dirname, "..", ".bin-cache");
const USER_CACHE_DIR = (() => {
  const home = os.homedir();
  if (!home) return BIN_CACHE;
  const base =
    process.env.XDG_CACHE_HOME ||
    (process.platform === "darwin"
      ? path.join(home, "Library", "Caches")
      : path.join(home, ".cache"));
  return path.join(base, "superdoc-benchmark");
})();
const CACHE_FILE = path.join(USER_CACHE_DIR, "update-check.json");
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;
const REGISTRY = (process.env.npm_config_registry || "https://registry.npmjs.org")
  .replace(/\/$/, "");
const PACKAGE_NAME_ENCODED = encodeURIComponent(PACKAGE_NAME);

function getLatestVersion() {
  return new Promise((resolve, reject) => {
    const url = `${REGISTRY}/${PACKAGE_NAME_ENCODED}/latest`;
    const client = url.startsWith("http:") ? http : https;
    const req = client.get(
      url,
      { headers: { Accept: "application/json" } },
      (res) => {
        if (!res || res.statusCode < 200 || res.statusCode >= 300) {
          res.resume();
          reject(new Error("Failed to fetch npm metadata"));
          return;
        }

        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(data).version);
          } catch {
            reject(new Error("Failed to parse npm response"));
          }
        });
      }
    );

    req.setTimeout(2000, () => {
      req.destroy(new Error("npm registry request timed out"));
    });
    req.on("error", reject);
  });
}

function shouldCheckForUpdate() {
  try {
    if (!fs.existsSync(CACHE_FILE)) return true;
    const cache = JSON.parse(fs.readFileSync(CACHE_FILE, "utf8"));
    return Date.now() - cache.lastCheck > CHECK_INTERVAL_MS;
  } catch {
    return true;
  }
}

function cacheUpdateCheck(latestVersion) {
  try {
    fs.mkdirSync(USER_CACHE_DIR, { recursive: true });
    fs.writeFileSync(
      CACHE_FILE,
      JSON.stringify({ lastCheck: Date.now(), latestVersion }),
      "utf8"
    );
  } catch {
    // Ignore cache write failures
  }
}

function compareVersions(a, b) {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if (pa[i] > pb[i]) return 1;
    if (pa[i] < pb[i]) return -1;
  }
  return 0;
}

function isGlobalInstall() {
  try {
    const globalRoot = execSync("npm root -g", {
      stdio: ["ignore", "pipe", "ignore"],
    })
      .toString()
      .trim();
    return __dirname.startsWith(globalRoot);
  } catch {
    return false;
  }
}

function promptForUpdate(latestVersion) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stderr,
  });

  return new Promise((resolve) => {
    console.error(
      `\nA new version of ${PACKAGE_NAME} is available: ${latestVersion} (current: ${CURRENT_VERSION})`
    );
    rl.question("   Would you like to update now? (Y/n) ", (answer) => {
      rl.close();
      resolve(answer.toLowerCase() !== "n");
    });
  });
}

function performUpdate() {
  console.error(`\n   Updating ${PACKAGE_NAME}...`);
  try {
    execSync(`npm update -g ${PACKAGE_NAME}`, { stdio: "inherit" });
    console.error("\n   Updated successfully. Please re-run your command.\n");
    process.exit(0);
  } catch {
    console.error(
      `\n   Update failed. Run manually: npm update -g ${PACKAGE_NAME}\n`
    );
  }
}

async function checkForUpdates() {
  if (process.env.SUPERDOC_BENCHMARK_SKIP_UPDATE_CHECK === "1") return;
  if (!process.stdin.isTTY || !process.stderr.isTTY) return;
  if (!shouldCheckForUpdate()) return;

  try {
    const latestVersion = await getLatestVersion();
    cacheUpdateCheck(latestVersion);

    if (compareVersions(latestVersion, CURRENT_VERSION) > 0) {
      if (!isGlobalInstall()) {
        console.error(
          `\nA new version of ${PACKAGE_NAME} is available: ${latestVersion} (current: ${CURRENT_VERSION})`
        );
        console.error(
          "   Update with your package manager (e.g., npm update @superdoc-dev/visual-benchmarks).\n"
        );
        return;
      }

      const shouldUpdate = await promptForUpdate(latestVersion);
      if (shouldUpdate) {
        performUpdate();
      } else {
        console.error(
          "   Skipped. Run `npm update -g @superdoc-dev/visual-benchmarks` anytime.\n"
        );
      }
    }
  } catch {
    // Silently ignore update check failures
  }
}

async function main() {
  await checkForUpdates();

  const binaryPath = path.join(BIN_CACHE, "superdoc-benchmark");

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
