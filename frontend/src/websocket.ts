import type { ServerMessage, BrowserMessage } from "./protocol";

const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private retryCount: number = 0;

  get retryDelay(): number {
    return Math.min(BASE_DELAY_MS * 2 ** this.retryCount, MAX_DELAY_MS);
  }

  public send(msg: BrowserMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  public connect(): void {
    window.dispatchEvent(new CustomEvent("bdbox:ws.connecting"));
    this.ws = new WebSocket(`ws://${window.location.host}/ws`);

    this.ws.addEventListener("open", () => {
      this.retryCount = 0;
      window.dispatchEvent(new CustomEvent("bdbox:ws.open"));
    });

    this.ws.addEventListener("message", ({ data }) => {
      let msg: ServerMessage;
      try {
        msg = JSON.parse(data as string) as ServerMessage;
      } catch {
        return;
      }
      window.dispatchEvent(
        new CustomEvent(`bdbox.server:${msg.type}`, { detail: msg }),
      );
    });

    this.ws.addEventListener("close", () => {
      this.ws = null;
      const delay = this.retryDelay;
      this.retryCount++;
      window.dispatchEvent(
        new CustomEvent("bdbox:ws.close", { detail: { retryInMs: delay } }),
      );
      setTimeout(() => this.connect(), delay);
    });

    this.ws.addEventListener("error", () => this.ws!.close());
  }
}
