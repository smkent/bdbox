import Alpine from "alpinejs";
import Jedison from "jedison";
import { JedisonData, ModelParamsState } from "./classes";
import { WebSocketManager } from "./websocket";
import {
  ModelDetailsMessage,
  ModelResetParamsMessage,
  ModelSetParamMessage,
  ModelSetPresetMessage,
} from "./protocol";

export class Params {
  private webSocketManager: WebSocketManager;
  private div: HTMLElement;
  private paramsFormEl: HTMLElement;
  private jedison: JedisonInstance | null = null;
  private jedisonData: JedisonData = new JedisonData();

  constructor(webSocketManager: WebSocketManager) {
    this.webSocketManager = webSocketManager;
    this.div = this.createDiv();
    this.paramsFormEl = this.div.querySelector(".params-form") as HTMLElement;
  }

  private createDiv(): HTMLElement {
    const div = document.createElement("div");
    div.className = "params-panel";
    div.innerHTML = `
      <div x-data="{ get modelName() { const i = $store.modelInfo; const b = i.module ?? i.file; return b && i.cls ? b + ' · ' + i.cls : i.cls ?? b ?? null; } }" class="status-bar">
        <span class="status-model-name" x-show="modelName" x-text="modelName" :title="modelName"></span>
      </div>
      <div class="params-form"></div>
    `;
    Alpine.initTree(div);
    return div;
  }

  register(container: HTMLElement): void {
    container.appendChild(this.div);
    this.display();
  }

  update(detail: ModelDetailsMessage): void {
    let schemaChanged = false;
    if (detail.schema && detail.schema.properties && detail.schema.required) {
      this.jedisonData.schema = detail.schema;
      this.jedisonData.params = new ModelParamsState();
      schemaChanged = true;
    }
    if (detail.params) {
      this.jedisonData.params = Object.assign(
        new ModelParamsState(),
        detail.params,
      );
    }
    if (schemaChanged) {
      this.display();
    } else if (this.jedison && detail.params) {
      this.display({ schemaChanged: false });
    }
  }

  private display({
    schemaChanged = true,
  }: { schemaChanged?: boolean } = {}): void {
    if (
      !(
        this.paramsFormEl &&
        this.jedisonData.schema?.properties &&
        this.jedisonData.schema?.required
      )
    ) {
      return;
    }

    if (!this.jedisonData.params) {
      return;
    }

    if (!schemaChanged) {
      if (this.jedison) {
        this.jedison.setValue(this.jedisonData.params.activeValues);
      }
      return;
    }

    if (this.jedison) {
      this.jedison.destroy();
      this.jedison = null;
    }

    this.paramsFormEl.innerHTML = "";

    // Controls bar: preset buttons + reset
    const controls = document.createElement("div");
    controls.className = "params-controls";
    const presets = this.jedisonData.schema["x-presets"] ?? [];
    presets.forEach(({ name, description }) => {
      const btn = document.createElement("button");
      btn.className = "params-preset-btn";
      btn.textContent = name;
      if (description) btn.title = description;
      btn.addEventListener("click", () =>
        this.webSocketManager.send(new ModelSetPresetMessage(name)),
      );
      controls.appendChild(btn);
    });
    const resetBtn = document.createElement("button");
    resetBtn.className = "params-reset-btn";
    resetBtn.textContent = "Reset";
    resetBtn.addEventListener("click", () =>
      this.webSocketManager.send(new ModelResetParamsMessage()),
    );
    controls.appendChild(resetBtn);
    this.paramsFormEl.appendChild(controls);

    // Jedison form
    const jedContainer = document.createElement("div");
    this.paramsFormEl.appendChild(jedContainer);

    const schema = {
      type: "object",
      "x-titleHidden": true,
      properties: this.jedisonData.schema.properties,
      required: this.jedisonData.schema.required,
    };

    this.jedison = new Jedison.Create({
      container: jedContainer,
      theme: new Jedison.Theme(),
      schema,
      data: this.jedisonData.params.activeValues,
      objectAdd: false,
    });

    this.jedison.on("instance-change", (instance, initiator) => {
      if (initiator !== "user") return;
      const parts = instance.path.split("/");
      if (parts.length !== 2) return;
      const topKey = parts[1];
      const value = instance.getValue();
      this.jedisonData.params.overrides = {
        ...this.jedisonData.params.overrides,
        [topKey]: value,
      };
      this.webSocketManager.send(new ModelSetParamMessage(topKey, value));
    });
  }
}
