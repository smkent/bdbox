import { GroupPanelPartInitParameters, IContentRenderer } from "dockview";

export class OCPCADViewer implements IContentRenderer {
  private readonly _element: HTMLElement;
  private readonly iframe: HTMLIFrameElement;

  constructor(private port: number) {
    this._element = document.createElement("div");
    Object.assign(this._element.style, { width: "100%", height: "100%" });

    this.iframe = document.createElement("iframe");
    Object.assign(this.iframe.style, {
      width: "100%",
      height: "100%",
      border: "none",
    });
    this.iframe.src = `http://localhost:${this.port}/viewer`;
    this._element.appendChild(this.iframe);

    window.addEventListener("bdbox.server:hello", ({ detail }) => {
      if (detail.viewer_port) {
        this.setPort(detail.viewer_port);
      }
    });
  }

  get element(): HTMLElement {
    return this._element;
  }

  init(parameters: GroupPanelPartInitParameters): void {
    const update = (isActive: boolean) => {
      this.iframe.style.pointerEvents = isActive ? "inherit" : "none";
    };
    update(parameters.api.isActive);
    parameters.api.onDidActiveChange((event) => update(event.isActive));
  }

  setPort(port: number): void {
    if (port !== this.port) {
      this.iframe.src = `http://localhost:${port}/viewer`;
    }
    this.port = port;
  }
}
