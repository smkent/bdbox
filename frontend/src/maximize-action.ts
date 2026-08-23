import { IGroupHeaderProps, IHeaderActionsRenderer } from "dockview";

const MAXIMIZE_ICON = `
  <svg viewBox="0 0 9 9" width="11" height="11" fill="currentColor" aria-hidden="true">
    <rect x="0" y="0" width="9" height="2"/>
    <rect x="0" y="2" width="1" height="6"/>
    <rect x="8" y="2" width="1" height="6"/>
    <rect x="0" y="8" width="9" height="1"/>
  </svg>`;
const RESTORE_ICON = `
  <svg viewBox="0 0 9 9" width="11" height="11" fill="currentColor" aria-hidden="true">
    <rect x="1" y="7" width="7" height="2"/>
  </svg>`;

export class MaximizeAction implements IHeaderActionsRenderer {
  private readonly button: HTMLButtonElement;
  private disposable: { dispose(): void } | undefined;

  constructor() {
    this.button = document.createElement("button");
    this.button.className = "layout-maximize-button";
  }

  get element(): HTMLElement {
    return this.button;
  }

  init(params: IGroupHeaderProps): void {
    const render = () => {
      const maximized = params.api.isMaximized();
      this.button.innerHTML = maximized ? RESTORE_ICON : MAXIMIZE_ICON;
      const label = maximized ? "Restore panel" : "Maximize panel";
      this.button.title = label;
      this.button.setAttribute("aria-label", label);
    };
    render();

    this.button.addEventListener("click", () => {
      if (params.api.isMaximized()) {
        params.api.exitMaximized();
      } else {
        params.api.maximize();
      }
    });

    this.disposable = params.containerApi.onDidMaximizedGroupChange(render);
  }

  dispose(): void {
    this.disposable?.dispose();
  }
}
