import Alpine from "alpinejs";
import { VersionInfo, formatElapsedMs } from "./protocol";

export class EventManager {
  private lastSessionId: string | null = null;
  private tickInterval: ReturnType<typeof setInterval> | null = null;
  private retryAt: number | null = null;
  private runStartedAt: number | null = null;
  private lastVersion: VersionInfo | null = null;

  constructor() {
    document.addEventListener("DOMContentLoaded", () => this.init());
  }

  public init(): void {
    window.addEventListener("bdbox.server:hello", ({ detail }) => {
      if (this.lastVersion) {
        if (detail.version.bdbox !== this.lastVersion.bdbox) {
          console.log(
            `bdbox version changed from ${this.lastVersion.bdbox}` +
              ` to ${detail.version.bdbox}`,
          );
        }
        if (detail.version.protocol !== this.lastVersion.protocol) {
          console.log(
            `protocol version changed from ${this.lastVersion.protocol}` +
              ` to ${detail.version.protocol}`,
          );
        }
      }
      this.lastVersion = detail.version;
      if (detail.session_id !== this.lastSessionId) {
        const store = Alpine.store("runStatus");
        store.state = "idle";
        store.elapsedMs = null;
        if (this.tickInterval) {
          clearInterval(this.tickInterval);
          this.tickInterval = null;
        }
        window.dispatchEvent(new CustomEvent("bdbox:model.clear_console"));
        this.lastSessionId = detail.session_id;
      }
    });

    window.addEventListener("bdbox.server:model.details", ({ detail }) => {
      if (detail.model_info) {
        const info = Alpine.store("modelInfo");
        info.file = detail.model_info.filename ?? null;
        info.module = detail.model_info.module_name ?? null;
        info.cls = detail.model_info.class_name ?? null;
      }
    });

    window.addEventListener("bdbox.server:model.status", ({ detail }) => {
      const store = Alpine.store("runStatus");
      store.state = detail.status;
      store.runElapsedS = 0;
      if (this.tickInterval) {
        clearInterval(this.tickInterval);
        this.tickInterval = null;
      }
      if (detail.status === "running") {
        window.dispatchEvent(new CustomEvent("bdbox:model.clear_console"));
        store.elapsedMs = null;
        this.runStartedAt = detail.started_at
          ? new Date(detail.started_at).getTime()
          : Date.now();
        this.tickInterval = setInterval(() => {
          store.runElapsedS = Math.round(
            (Date.now() - this.runStartedAt!) / 1000,
          );
        }, 1000);
      } else if (detail.status === "done" || detail.status === "error") {
        if (detail.elapsed_ms !== undefined) {
          store.elapsedMs = formatElapsedMs(detail.elapsed_ms);
        }
      }
    });

    window.addEventListener("bdbox:ws.connecting", () => {
      if (this.tickInterval) {
        clearInterval(this.tickInterval);
        this.tickInterval = null;
      }
      this.retryAt = null;
      Alpine.store("runStatus").wsState = "connecting";
    });
    window.addEventListener("bdbox:ws.open", () => {
      Alpine.store("runStatus").wsState = "connected";
    });
    window.addEventListener("bdbox:ws.close", ({ detail }) => {
      const store = Alpine.store("runStatus");
      store.wsState = "disconnected";
      this.retryAt = Date.now() + detail.retryInMs;
      store.retryIn = Math.round(detail.retryInMs / 1000);
      this.tickInterval = setInterval(() => {
        store.retryIn = Math.max(
          0,
          Math.round((this.retryAt! - Date.now()) / 1000),
        );
        if (store.retryIn <= 0) {
          clearInterval(this.tickInterval!);
          this.tickInterval = null;
        }
      }, 1000);
    });
  }
}
