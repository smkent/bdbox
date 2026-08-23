import {
  createDockview,
  DockviewApi,
  SerializedDockview,
  themeDark,
} from "dockview";
import { WebSocketManager } from "./websocket";
import { OCPCADViewer } from "./ocp-cad-viewer";
import { WebConsole } from "./console";
import { Params } from "./params";
import { PlainTab } from "./plain-tab";
import { MaximizeAction } from "./maximize-action";

const LAYOUT_VERSION = 1;
const STORAGE_KEY = `bdbox-layout-v${LAYOUT_VERSION}`;

export class Layout {
  private params: Params;
  private viewer: OCPCADViewer = new OCPCADViewer(window.__BDBOX__.viewerPort);
  private webconsole: WebConsole;
  private container: HTMLElement;
  private api!: DockviewApi;

  constructor(webSocketManager: WebSocketManager) {
    this.params = new Params(webSocketManager);
    this.webconsole = new WebConsole(webSocketManager);
    this.container = document.getElementById("layout") as HTMLElement;
    document.addEventListener("DOMContentLoaded", () => this.init());
  }

  private init(): void {
    this.api = createDockview(this.container, {
      theme: themeDark,
      disableAutoResizing: true,
      defaultTabComponent: "plain",
      createTabComponent: () => new PlainTab(),
      createRightHeaderActionComponent: () => new MaximizeAction(),
      createComponent: (options) => {
        switch (options.name) {
          case "viewer":
            return this.viewer;
          case "params":
            return this.params;
          case "console":
            return this.webconsole;
          default:
            throw new Error(`Unknown component: ${options.name}`);
        }
      },
    });
    this.api.layout(this.container.clientWidth, this.container.clientHeight);

    new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      this.api.layout(width, height);
    }).observe(this.container);

    if (!this.loadSavedLayout()) {
      this.setDefaultLayout();
    }

    const persistLayout = () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.api.toJSON()));
    };
    this.api.onDidLayoutChange(persistLayout);
    this.api.onDidMaximizedGroupChange(persistLayout);

    window.addEventListener("bdbox.server:model.details", ({ detail }) => {
      this.params.setModelDetails(detail);
    });
  }

  private loadSavedLayout(): boolean {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        this.api.fromJSON(JSON.parse(saved) as SerializedDockview);
        return true;
      } catch (error) {
        console.error("Failed to restore saved layout:", error);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    return false;
  }

  private setDefaultLayout(): void {
    this.api.addPanel({
      id: "viewer",
      component: "viewer",
      title: "Viewer",
      renderer: "always",
    });
    this.api.addPanel({
      id: "params",
      component: "params",
      title: "Parameters",
      position: { referencePanel: "viewer", direction: "right" },
      initialWidth: Math.round(this.container.clientWidth * 0.3),
    });
    this.api.addPanel({
      id: "console",
      component: "console",
      title: "Console",
      position: { referencePanel: "params", direction: "below" },
      initialHeight: Math.round(this.container.clientHeight * 0.4),
    });
  }
}
