import { ITabRenderer, TabPartInitParameters } from "dockview";

export class PlainTab implements ITabRenderer {
  private readonly _element: HTMLElement;
  private readonly content: HTMLElement;

  constructor() {
    this._element = document.createElement("div");
    this._element.className = "dv-default-tab";
    this.content = document.createElement("div");
    this.content.className = "dv-default-tab-content";
    this._element.appendChild(this.content);
  }

  get element(): HTMLElement {
    return this._element;
  }

  init(parameters: TabPartInitParameters): void {
    this.content.textContent = parameters.title ?? "";
    parameters.api.onDidTitleChange((event) => {
      this.content.textContent = event.title ?? "";
    });
  }
}
