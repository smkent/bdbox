import { GoldenLayout, ComponentContainer } from "golden-layout";
import type { LayoutConfig } from "golden-layout";
import { WebSocketManager } from "./websocket";
import { ClientInfoMessage, TerminalInfo } from "./protocol";
import { OCPCADViewer } from "./ocp-cad-viewer";
import { WebConsole } from "./console";
import { Params } from "./params";

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

export class Layout {
  // The viewer iframe lives outside GoldenLayout's DOM so maximize/restore
  // doesn't reload it. Repositioned to track container.element on each frame.
  private webSocketManager: WebSocketManager;
  private params: Params;
  private viewer: OCPCADViewer = new OCPCADViewer(window.__BDBOX__.viewerPort);
  private webconsole: WebConsole = new WebConsole();
  private container: HTMLElement;
  private goldenLayout: GoldenLayout;

  constructor(webSocketManager: WebSocketManager) {
    this.webSocketManager = webSocketManager;
    this.params = new Params(webSocketManager);
    this.container = document.getElementById("layout") as HTMLElement;
    this.goldenLayout = new GoldenLayout(this.container);
    document.addEventListener("DOMContentLoaded", () => this.init());
  }

  private init(): void {
    this.registerComponents();

    const saved = localStorage.getItem(STORAGE_KEY);
    const layout = this.goldenLayout;
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
      requestAnimationFrame(() => this.viewer.reposition());
    });

    new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      layout.updateSize(width, height);
      requestAnimationFrame(() => this.viewer.reposition());
    }).observe(this.container);

    window.addEventListener("bdbox.server:model.details", ({ detail }) => {
      this.params.update(detail);
    });
  }

  private registerComponents(): void {
    this.goldenLayout.registerComponentFactoryFunction(
      "viewer",
      (container: ComponentContainer) =>
        this.viewer.register(container.element),
    );

    this.goldenLayout.registerComponentFactoryFunction(
      "params",
      (container: ComponentContainer) =>
        this.params.register(container.element),
    );

    this.goldenLayout.registerComponentFactoryFunction(
      "console",
      (container: ComponentContainer) => {
        const onResize = () => {
          const { rows, cols } = this.webconsole.size;
          this.webSocketManager.send(
            new ClientInfoMessage(new TerminalInfo(rows, cols)),
          );
        };
        this.webconsole.register(container.element, onResize);
        container.on("resize", () => this.webconsole.resize());
        window.addEventListener("bdbox:ws.open", onResize);
        return undefined;
      },
    );
  }
}
