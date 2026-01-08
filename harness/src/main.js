/**
 * SuperDoc Benchmark Harness
 *
 * A minimal test harness for rendering Word documents in SuperDoc with automated
 * screenshot capture. This harness is controlled by Python via Playwright to enable
 * pixel-perfect visual comparison between Word and SuperDoc renderings.
 *
 * The harness exposes global state variables that the Python code monitors:
 * - __superdocReady: SuperDoc instance initialized and ready
 * - __superdocLayoutStable: Layout has settled after last update
 * - __superdocLayoutUpdatedAt: Timestamp of last layout change
 * - __superdocLayoutVersion: Incremental version number for layout changes
 * - __superdocFontsReady: Document fonts have loaded
 * - __superdocForceLayout: Function to trigger layout recalculation
 *
 * @module benchmark-harness
 */

import { SuperDoc } from "superdoc";
import "superdoc/style.css";
import "./style.css";

/** @type {SuperDoc|null} */
let editor = null;

/** @type {HTMLInputElement} */
const fileInput = document.getElementById("fileInput");

/** @type {HTMLElement} */
const status = document.getElementById("status");

/** @type {Object} */
const layoutState = {
  lastUpdatedAt: 0,
  version: 0,
  stable: false,
  timer: null,
};

/**
 * Schedule layout stability check after a debounce delay.
 */
const markLayoutStableSoon = () => {
  if (layoutState.timer) {
    clearTimeout(layoutState.timer);
  }
  layoutState.timer = setTimeout(() => {
    setLayoutStable(true);
  }, 300);
};

/**
 * Set layout stability state and update global flag for Playwright monitoring.
 */
const setLayoutStable = (isStable) => {
  layoutState.stable = isStable;
  window.__superdocLayoutStable = isStable;
};

/**
 * Mark that a layout update has occurred.
 */
const markLayoutUpdated = () => {
  layoutState.lastUpdatedAt = Date.now();
  layoutState.version += 1;
  window.__superdocLayoutUpdatedAt = layoutState.lastUpdatedAt;
  window.__superdocLayoutVersion = layoutState.version;
  setLayoutStable(false);
  markLayoutStableSoon();
};

/**
 * Update the status display text.
 */
const updateStatus = (text) => {
  if (status) {
    status.textContent = text;
  }
};

/**
 * Destroy the current SuperDoc editor instance.
 */
const destroyEditor = () => {
  if (editor?.destroy) {
    editor.destroy();
  }
  editor = null;
};

/**
 * Force a layout recalculation.
 */
const forceLayout = () => {
  const presentation = editor?.activeEditor?.presentationEditor;
  if (!presentation?.setZoom) return;
  const zoom = presentation.getLayoutOptions?.().zoom ?? 1;
  presentation.setZoom(zoom);
  markLayoutUpdated();
};

/**
 * Bind event listeners to SuperDoc layout engine updates.
 */
const bindLayoutEvents = () => {
  const presentation = editor?.activeEditor?.presentationEditor;
  if (!presentation?.onLayoutUpdated) return;
  presentation.onLayoutUpdated(markLayoutUpdated);
  presentation.onLayoutError?.(markLayoutUpdated);
  markLayoutUpdated();
};

/**
 * Wait for document fonts to load.
 */
const waitForFonts = async () => {
  window.__superdocFontsReady = false;
  if (!document.fonts?.ready) {
    window.__superdocFontsReady = true;
    forceLayout();
    return;
  }
  try {
    await document.fonts.ready;
  } catch {
    // ignore font readiness errors
  }
  window.__superdocFontsReady = true;
  forceLayout();
};

/**
 * Initialize the SuperDoc editor with a document file.
 */
const initEditor = (file) => {
  destroyEditor();
  window.__superdocReady = false;
  window.__superdocLayoutStable = false;
  window.__superdocLayoutUpdatedAt = 0;
  window.__superdocLayoutVersion = 0;

  editor = new SuperDoc({
    selector: "#superdoc",
    document: file,
    documentMode: "viewing",
    pagination: true,
    useLayoutEngine: true,
    rulers: false,
    disableContextMenu: true,
    modules: {
      comments: true,
      toolbar: false,
      slashMenu: false,
      ai: false,
      collaboration: false,
    },
    layoutEngineOptions: {
      zoom: 1,
      virtualization: { enabled: false },
      layoutMode: "vertical",
      debugLabel: "benchmark-harness",
    },
    onReady: () => {
      window.__superdocReady = true;
      bindLayoutEvents();
      waitForFonts();
      updateStatus("Ready");
    },
  });
  window.__superdocInstance = editor;
};

// Event listener for file input changes
fileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  updateStatus(`Loading ${file.name}...`);
  initEditor(file);
});

// Initialize global state for Playwright monitoring
window.__superdocBenchmarkHarness = true;
window.__superdocLayoutStable = false;
window.__superdocLayoutUpdatedAt = 0;
window.__superdocLayoutVersion = 0;
window.__superdocFontsReady = false;
window.__superdocForceLayout = () => forceLayout();
updateStatus("Idle");
