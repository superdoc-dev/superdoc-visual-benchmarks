import path from "path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { nodePolyfills } from "vite-plugin-node-polyfills";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const harnessRoot = path.resolve(__dirname, "harness");
const port = Number.parseInt(process.env.SUPERDOC_BENCHMARK_PORT || "9106", 10);
const superdocPackage = process.env.SUPERDOC_BENCHMARK_PACKAGE || "superdoc";
const cacheSlug = superdocPackage.replace(/[^a-zA-Z0-9._-]/g, "_");
const cacheDir = path.resolve(__dirname, `node_modules/.vite-benchmark-${cacheSlug}`);

export default defineConfig({
  root: harnessRoot,
  plugins: [vue(), nodePolyfills()],
  cacheDir,
  resolve: {
    alias: {
      superdoc: superdocPackage,
    },
    extensions: [".mjs", ".js", ".ts", ".jsx", ".tsx", ".json"],
  },
  server: {
    port,
    strictPort: false,
    host: "127.0.0.1",
    fs: {
      allow: [__dirname],
    },
  },
});
