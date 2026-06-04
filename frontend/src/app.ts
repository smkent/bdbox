import { GoldenLayout, ComponentContainer } from "golden-layout";
import type { LayoutConfig } from "golden-layout";
import Alpine from "alpinejs";
import Jedison from "jedison";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "golden-layout/dist/css/goldenlayout-base.css";
import "golden-layout/dist/css/themes/goldenlayout-dark-theme.css";
import "@xterm/xterm/css/xterm.css";
import "./app.css";
import { connectWs, sendWs } from "./ws.js";
import { BrowserMessage } from "./protocol.js";
import type { SchemaMessage } from "./protocol.js";

const LAYOUT_VERSION = 1;
const STORAGE_KEY = `bdbox-layout-v${LAYOUT_VERSION}`;

const DEFAULT_LAYOUT = {
  root: {
    type: "row",
    content: [
      {
        type: "component",
        componentType: "viewer",
        title: "Viewer",
        size: "70%",
        isClosable: false,
        header: { popout: false },
      },
      {
        type: "column",
        size: "30%",
        content: [
          {
            type: "component",
            componentType: "params",
            title: "Parameters",
            size: "60%",
            isClosable: false,
            header: { popout: false },
          },
          {
            type: "component",
            componentType: "console",
            title: "Console",
            size: "40%",
            isClosable: false,
            header: { popout: false },
          },
        ],
      },
    ],
  },
};

// The viewer iframe lives outside GoldenLayout's DOM so maximize/restore
// doesn't reload it. Repositioned to track container.element on each frame.
let viewerIframe: HTMLIFrameElement | null = null;
let viewerContainerEl: HTMLElement | null = null;

function positionViewerIframe(): void {
  if (!viewerIframe || !viewerContainerEl) return;

  // Hide if a non-viewer panel is maximised (would otherwise float above it)
  const maximisedEl = document.querySelector(".lm_maximised");
  if (maximisedEl && !maximisedEl.contains(viewerContainerEl)) {
    viewerIframe.style.display = "none";
    return;
  }

  const rect = viewerContainerEl.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    viewerIframe.style.display = "none";
    return;
  }

  Object.assign(viewerIframe.style, {
    display: "block",
    left: `${rect.left}px`,
    top: `${rect.top}px`,
    width: `${rect.width}px`,
    height: `${rect.height}px`,
  });
}

// Params panel state
let paramsFormEl: HTMLElement | null = null;
let jedison: JedisonInstance | null = null;
let currentValues: Record<string, unknown> = {};
let paramOverrides: Record<string, unknown> = {};
let latestSchema: SchemaMessage | null = null;
let lastSessionId: string | null = null;

function initJedison(detail: SchemaMessage): void {
  if (!(detail.schema && detail.schema.properties && detail.schema.required)) {
    return;
  }

  if (jedison) {
    jedison.destroy();
    jedison = null;
  }

  const schemaData = detail.schema;
  currentValues = detail.current_values;
  paramOverrides = {};
  paramsFormEl!.innerHTML = "";

  // Controls bar: preset buttons + reset
  const controls = document.createElement("div");
  controls.className = "params-controls";
  const presets = schemaData["x-presets"] ?? [];
  presets.forEach(({ name, description }) => {
    const btn = document.createElement("button");
    btn.className = "params-preset-btn";
    btn.textContent = name;
    if (description) btn.title = description;
    btn.addEventListener("click", () =>
      sendWs(BrowserMessage.selectPreset(name)),
    );
    controls.appendChild(btn);
  });
  const resetBtn = document.createElement("button");
  resetBtn.className = "params-reset-btn";
  resetBtn.textContent = "Reset";
  resetBtn.addEventListener("click", () =>
    sendWs(BrowserMessage.resetParams()),
  );
  controls.appendChild(resetBtn);
  paramsFormEl!.appendChild(controls);

  // Jedison form
  const jedContainer = document.createElement("div");
  paramsFormEl!.appendChild(jedContainer);

  const schema = {
    type: "object",
    "x-titleHidden": true,
    properties: schemaData.properties,
    required: schemaData.required,
  };

  jedison = new Jedison.Create({
    container: jedContainer,
    theme: new Jedison.Theme(),
    schema,
    data: { ...currentValues, ...paramOverrides },
    objectAdd: false,
  });

  jedison.on("instance-change", (instance, initiator) => {
    if (initiator !== "user") return;
    const parts = instance.path.split("/");
    if (parts.length !== 2) return;
    const topKey = parts[1];
    const value = instance.getValue();
    paramOverrides = { ...paramOverrides, [topKey]: value };
    sendWs(BrowserMessage.updateParam(topKey, value));
  });
}

function registerComponents(layout: GoldenLayout): void {
  layout.registerComponentFactoryFunction(
    "viewer",
    (container: ComponentContainer) => {
      const { viewerPort } = window.__BDBOX__;
      viewerContainerEl = container.element;

      if (!viewerIframe) {
        viewerIframe = document.createElement("iframe");
        viewerIframe.src = `http://localhost:${viewerPort}/viewer`;
        Object.assign(viewerIframe.style, {
          position: "fixed",
          border: "none",
          display: "none",
          zIndex: "45",
        });
        document.body.appendChild(viewerIframe);
      }

      requestAnimationFrame(positionViewerIframe);
      return undefined;
    },
  );

  layout.registerComponentFactoryFunction(
    "params",
    (container: ComponentContainer) => {
      const div = document.createElement("div");
      div.className = "params-panel";
      div.innerHTML = `
      <div x-data="{ get modelName() { const i = $store.modelInfo; const b = i.module ?? i.file; return b && i.cls ? b + ' · ' + i.cls : i.cls ?? b ?? null; } }" class="status-bar">
        <span class="status-model-name" x-show="modelName" x-text="modelName" :title="modelName"></span>
      </div>
      <div class="params-form"></div>
    `;
      container.element.appendChild(div);
      Alpine.initTree(div);

      paramsFormEl = div.querySelector(".params-form");
      if (latestSchema) {
        initJedison(latestSchema);
      }
      return undefined;
    },
  );

  layout.registerComponentFactoryFunction(
    "console",
    (container: ComponentContainer) => {
      const div = document.createElement("div");
      div.className = "console-panel";

      div.innerHTML = `
      <div class="status-bar">
        <div class="status-run" x-data="{ formatElapsed(s) { const m = Math.floor(s / 60) % 60, h = Math.floor(s / 3600) % 24, d = Math.floor(s / 86400); const p = []; if (d) p.push(d + 'd'); if (h) p.push(h + 'h'); if (m) p.push(m + 'm'); p.push((s % 60) + 's'); return p.join(' '); } }">
          <span x-show="$store.runStatus.wsState === 'connecting'" class="status-connecting"><span class="status-spinner"></span>Connecting…</span>
          <span x-show="$store.runStatus.wsState === 'disconnected'" class="status-disconnected">Disconnected (retry in <span x-text="$store.runStatus.retryIn"></span>s)</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'idle'" class="status-idle">Idle</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'running'" class="status-running"><span class="status-spinner"></span>Running…<span x-show="$store.runStatus.runElapsedS >= 2"> (<span x-text="formatElapsed($store.runStatus.runElapsedS)"></span>)</span></span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'ok'" class="status-ok">Done (<span x-text="$store.runStatus.elapsedMs"></span>)</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'error'" class="status-error">Error</span>
        </div>
      </div>
      <div class="console-terminal"></div>
    `;
      container.element.appendChild(div);
      Alpine.initTree(div);

      const terminalEl = div.querySelector(".console-terminal") as HTMLElement;

      const terminal = new Terminal({
        convertEol: true,
        disableStdin: true,
        scrollback: 1000,
        theme: { background: "#1a1a1a", foreground: "#ccc" },
        fontFamily: "monospace",
        fontSize: 12,
      });
      const fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.open(terminalEl);
      fitAddon.fit();

      const sendSize = (): void =>
        sendWs(BrowserMessage.terminalSize(terminal.cols, terminal.rows));

      const fit = (): void => {
        fitAddon.fit();
        sendSize();
      };
      new ResizeObserver(fit).observe(terminalEl);
      container.on("resize", fit);

      window.addEventListener("bdbox:ws_open", sendSize);
      window.addEventListener("bdbox:run_start", () => terminal.clear());
      window.addEventListener("bdbox:clear_console", () => terminal.clear());
      window.addEventListener("bdbox:console", ({ detail }) => {
        terminal.write(detail.text);
      });
      return undefined;
    },
  );
}

function initLayout(): void {
  const container = document.getElementById("layout") as HTMLElement;
  const layout = new GoldenLayout(container);

  registerComponents(layout);

  const saved = localStorage.getItem(STORAGE_KEY);
  let loaded = false;
  if (saved) {
    try {
      layout.loadLayout(JSON.parse(saved) as LayoutConfig);
      loaded = true;
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  if (!loaded) {
    layout.loadLayout(DEFAULT_LAYOUT as unknown as LayoutConfig);
  }

  layout.on("stateChanged", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.saveLayout()));
    requestAnimationFrame(positionViewerIframe);
  });

  new ResizeObserver((entries) => {
    const { width, height } = entries[0].contentRect;
    layout.updateSize(width, height);
    requestAnimationFrame(positionViewerIframe);
  }).observe(container);
}

function initIframeDragFix(): void {
  document.addEventListener("mousedown", () => {
    document.querySelectorAll("iframe").forEach((f) => {
      f.style.pointerEvents = "none";
    });
  });
  document.addEventListener("mouseup", () => {
    document.querySelectorAll("iframe").forEach((f) => {
      f.style.pointerEvents = "";
    });
  });
}

function initWs(): void {
  window.addEventListener("bdbox:hello", ({ detail }) => {
    if (detail.session_id !== lastSessionId) {
      const store = Alpine.store("runStatus");
      store.state = "idle";
      store.elapsedMs = "";
      if (tickInterval) {
        clearInterval(tickInterval);
        tickInterval = null;
      }
      window.dispatchEvent(new CustomEvent("bdbox:clear_console"));
      lastSessionId = detail.session_id;
    }
  });

  window.addEventListener("bdbox:schema", ({ detail }) => {
    if (detail.model_running) {
      const store = Alpine.store("runStatus");
      store.state = "running";
      if (tickInterval) clearInterval(tickInterval);
      runStartedAt = detail.model_run_started
        ? new Date(detail.model_run_started).getTime()
        : Date.now();
      store.runElapsedS = 0;
      tickInterval = setInterval(() => {
        store.runElapsedS = Math.round((Date.now() - runStartedAt!) / 1000);
      }, 1000);
    }
    if (detail.model_info) {
      const info = Alpine.store("modelInfo");
      info.file = detail.model_info.file ?? null;
      info.module = detail.model_info.module ?? null;
      info.cls = detail.model_info.cls ?? null;
    }
    if (
      detail.schema !== undefined &&
      detail.schema !== null &&
      detail.schema.properties &&
      detail.schema.required
    ) {
      latestSchema = detail;
      if (paramsFormEl) {
        initJedison(detail);
      }
    }
  });

  window.addEventListener("bdbox:param_overrides", ({ detail }) => {
    paramOverrides = detail.param_overrides;
    if (jedison) {
      jedison.setValue({ ...currentValues, ...paramOverrides });
    }
  });

  window.addEventListener("bdbox:run_start", () => {
    const store = Alpine.store("runStatus");
    store.state = "running";
    store.elapsedMs = "";
    if (tickInterval) clearInterval(tickInterval);
    runStartedAt = Date.now();
    store.runElapsedS = 0;
    tickInterval = setInterval(() => {
      store.runElapsedS = Math.round((Date.now() - runStartedAt!) / 1000);
    }, 1000);
  });

  window.addEventListener("bdbox:run_ok", ({ detail }) => {
    const store = Alpine.store("runStatus");
    store.state = "ok";
    store.elapsedMs = detail.elapsed_ms;
    store.runElapsedS = 0;
    if (tickInterval) {
      clearInterval(tickInterval);
      tickInterval = null;
    }
    if (detail.current_values && Object.keys(paramOverrides).length === 0) {
      currentValues = detail.current_values;
      if (jedison) {
        jedison.setValue(currentValues);
      }
    }
  });

  window.addEventListener("bdbox:run_error", () => {
    const store = Alpine.store("runStatus");
    store.state = "error";
    store.runElapsedS = 0;
    if (tickInterval) {
      clearInterval(tickInterval);
      tickInterval = null;
    }
  });

  let tickInterval: ReturnType<typeof setInterval> | null = null;
  let retryAt: number | null = null;
  let runStartedAt: number | null = null;

  window.addEventListener("bdbox:ws_connecting", () => {
    if (tickInterval) {
      clearInterval(tickInterval);
      tickInterval = null;
    }
    retryAt = null;
    Alpine.store("runStatus").wsState = "connecting";
  });
  window.addEventListener("bdbox:ws_open", () => {
    Alpine.store("runStatus").wsState = "connected";
  });
  window.addEventListener("bdbox:ws_close", ({ detail }) => {
    const store = Alpine.store("runStatus");
    store.wsState = "disconnected";
    retryAt = Date.now() + detail.retryInMs;
    store.retryIn = Math.round(detail.retryInMs / 1000);
    tickInterval = setInterval(() => {
      store.retryIn = Math.max(0, Math.round((retryAt! - Date.now()) / 1000));
      if (store.retryIn <= 0) {
        clearInterval(tickInterval!);
        tickInterval = null;
      }
    }, 1000);
  });

  connectWs();
}

Alpine.store("runStatus", {
  state: "idle" as RunStatusStore["state"],
  elapsedMs: "",
  wsState: "connecting" as RunStatusStore["wsState"],
  retryIn: 0,
  runElapsedS: 0,
});

Alpine.store("modelInfo", {
  file: null,
  module: null,
  cls: null,
});

document.addEventListener("DOMContentLoaded", () => {
  initLayout();
  initIframeDragFix();
  initWs();
});

window.Alpine = Alpine;
Alpine.start();
