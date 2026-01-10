"use strict";

const { execSync } = require("child_process");

function isLifecycleFromPublish() {
  const argv = process.env.npm_config_argv;
  if (argv) {
    try {
      const parsed = JSON.parse(argv);
      const original = parsed.original || [];
      if (original[0] === "publish") {
        return true;
      }
      if (original[0] === "run" || original[0] === "run-script") {
        return false;
      }
    } catch {
      // Fall through to npm_command check.
    }
  }

  return process.env.npm_command === "publish";
}

if (isLifecycleFromPublish()) {
  process.exit(0);
}

execSync("npm publish --access public", { stdio: "inherit" });
