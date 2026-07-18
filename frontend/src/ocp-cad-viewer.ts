export class OCPCADViewer {
  private iframe: HTMLIFrameElement;
  private containerEl: HTMLElement | null = null;

  constructor(private port: number) {
    this.iframe = this.createIframe();
  }

  private createIframe(): HTMLIFrameElement {
    const iframe = document.createElement("iframe");
    iframe.src = `http://localhost:${this.port}/viewer`;
    Object.assign(iframe.style, {
      position: "fixed",
      border: "none",
      display: "none",
      zIndex: "45",
    });
    document.addEventListener("mousedown", () => {
      iframe.style.pointerEvents = "none";
    });
    document.addEventListener("mouseup", () => {
      iframe.style.pointerEvents = "";
    });
    document.body.appendChild(iframe);
    window.addEventListener("bdbox.server:hello", ({ detail }) => {
      if (detail.viewer_port) {
        this.setPort(detail.viewer_port);
      }
    });
    return iframe;
  }

  register(container: HTMLElement): void {
    this.containerEl = container;
    this.reposition();
  }

  setPort(port: number): void {
    if (port !== this.port) {
      this.iframe.src = `http://localhost:${port}/viewer`;
    }
    this.port = port;
  }

  reposition(): void {
    if (!this.containerEl) {
      return;
    }

    // Hide if a non-viewer panel is maximised (would otherwise float above it)
    const maximisedEl = document.querySelector(".lm_maximised");
    if (maximisedEl && !maximisedEl.contains(this.containerEl)) {
      this.iframe.style.display = "none";
      return;
    }

    const rect = this.containerEl.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
      this.iframe.style.display = "none";
      return;
    }

    Object.assign(this.iframe.style, {
      display: "block",
      left: `${rect.left}px`,
      top: `${rect.top}px`,
      width: `${rect.width}px`,
      height: `${rect.height}px`,
    });
  }
}
