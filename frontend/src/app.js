import { GoldenLayout } from "golden-layout";
import Alpine from "alpinejs";
import Jedison from "jedison";
import "golden-layout/dist/css/goldenlayout-base.css";
import "golden-layout/dist/css/themes/goldenlayout-dark-theme.css";
import "./app.css";
import { connectWs, sendWs } from "./ws.js";

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

// Params panel state
let paramsFormEl = null;
let jedison = null;
let currentValues = {};
let paramOverrides = {};
let latestSchema = null;

function initJedison(detail) {
  if (jedison) {
    jedison.destroy();
    jedison = null;
  }

  const schemaData = detail.schema || {};
  currentValues = detail.current_values || {};
  paramOverrides = {};
  paramsFormEl.innerHTML = "";

  // Controls bar: preset buttons + reset
  const controls = document.createElement("div");
  controls.className = "params-controls";
  const presets = schemaData["x-presets"] || [];
  presets.forEach(({ name, description }) => {
    const btn = document.createElement("button");
    btn.className = "params-preset-btn";
    btn.textContent = name;
    if (description) btn.title = description;
    btn.addEventListener("click", () =>
      sendWs({ type: "select_preset", preset: name }),
    );
    controls.appendChild(btn);
  });
  const resetBtn = document.createElement("button");
  resetBtn.className = "params-reset-btn";
  resetBtn.textContent = "Reset";
  resetBtn.addEventListener("click", () => sendWs({ type: "reset_params" }));
  controls.appendChild(resetBtn);
  paramsFormEl.appendChild(controls);

  // Jedison form
  const jedContainer = document.createElement("div");
  paramsFormEl.appendChild(jedContainer);

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
    sendWs({ type: "update_param", field: topKey, value });
  });
}

function registerComponents(layout) {
  layout.registerComponentFactoryFunction("viewer", (container) => {
    const { viewerPort } = window.__BDBOX__;
    const iframe = document.createElement("iframe");
    iframe.src = `http://localhost:${viewerPort}/viewer`;
    Object.assign(iframe.style, {
      width: "100%",
      height: "100%",
      border: "none",
    });
    container.element.appendChild(iframe);
  });

  layout.registerComponentFactoryFunction("params", (container) => {
    const div = document.createElement("div");
    div.className = "params-panel";
    div.innerHTML = `
      <div x-data class="status-bar">
        <span x-show="$store.runStatus.state === 'idle'" class="status-idle">Idle</span>
        <span x-show="$store.runStatus.state === 'running'" class="status-running">Running…</span>
        <span x-show="$store.runStatus.state === 'ok'" class="status-ok">Done (<span x-text="$store.runStatus.elapsedMs"></span>ms)</span>
        <span x-show="$store.runStatus.state === 'error'" class="status-error">Error</span>
      </div>
      <div class="params-form"></div>
    `;
    container.element.appendChild(div);
    Alpine.initTree(div);

    paramsFormEl = div.querySelector(".params-form");
    if (latestSchema) {
      initJedison(latestSchema);
    }
  });

  layout.registerComponentFactoryFunction("console", (container) => {
    const div = document.createElement("div");
    div.className = "console-panel";
    const pre = document.createElement("pre");
    pre.className = "console-output";
    div.appendChild(pre);
    container.element.appendChild(div);

    window.addEventListener("bdbox:run_start", () => {
      pre.textContent = "";
    });
    window.addEventListener("bdbox:console", ({ detail }) => {
      const span = document.createElement("span");
      span.className = `console-${detail.stream}`;
      span.textContent = detail.text;
      pre.appendChild(span);
      pre.scrollTop = pre.scrollHeight;
    });
  });
}

function initLayout() {
  const container = document.getElementById("layout");
  const layout = new GoldenLayout(container);

  registerComponents(layout);

  const saved = localStorage.getItem(STORAGE_KEY);
  let loaded = false;
  if (saved) {
    try {
      layout.loadLayout(JSON.parse(saved));
      loaded = true;
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  if (!loaded) {
    layout.loadLayout(DEFAULT_LAYOUT);
  }

  layout.on("stateChanged", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.saveLayout()));
  });

  new ResizeObserver((entries) => {
    const { width, height } = entries[0].contentRect;
    layout.updateSize(width, height);
  }).observe(container);
}

function initIframeDragFix() {
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

function initWs() {
  window.addEventListener("bdbox:schema", ({ detail }) => {
    latestSchema = detail;
    if (paramsFormEl) {
      initJedison(detail);
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
  });

  window.addEventListener("bdbox:run_ok", ({ detail }) => {
    const store = Alpine.store("runStatus");
    store.state = "ok";
    store.elapsedMs = detail.elapsed_ms;
    if (detail.current_values) {
      currentValues = detail.current_values;
      // Sync form when no pending overrides (e.g. after reset)
      if (jedison && Object.keys(paramOverrides).length === 0) {
        jedison.setValue(currentValues);
      }
    }
  });

  window.addEventListener("bdbox:run_error", () => {
    Alpine.store("runStatus").state = "error";
  });

  connectWs();
}

Alpine.store("runStatus", {
  state: "idle",
  elapsedMs: "",
});

document.addEventListener("DOMContentLoaded", () => {
  initLayout();
  initIframeDragFix();
  initWs();
});

window.Alpine = Alpine;
Alpine.start();
