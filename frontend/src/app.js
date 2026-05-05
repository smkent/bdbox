import { GoldenLayout } from "golden-layout";
import Alpine from "alpinejs";
import "golden-layout/dist/css/goldenlayout-base.css";
import "golden-layout/dist/css/themes/goldenlayout-dark-theme.css";
import "./app.css";
import { connectWs } from "./ws.js";

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
  window.addEventListener("bdbox:run_start", () => {
    const store = Alpine.store("runStatus");
    store.state = "running";
    store.elapsedMs = "";
  });
  window.addEventListener("bdbox:run_ok", ({ detail }) => {
    const store = Alpine.store("runStatus");
    store.state = "ok";
    store.elapsedMs = detail.elapsed_ms;
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
