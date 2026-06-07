import Alpine from "alpinejs";

export class UIState {
  constructor() {
    this.init();
  }

  public init(): void {
    Alpine.store("runStatus", {
      state: "idle",
      elapsedMs: null,
      wsState: "connecting",
      retryIn: 0,
      runElapsedS: 0,
    });

    Alpine.store("modelInfo", {
      file: null,
      module: null,
      cls: null,
    });

    window.Alpine = Alpine;
    Alpine.start();
  }
}
