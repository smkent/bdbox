import type { ServerMessage, BrowserMessage } from "./protocol.js";

const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

let _ws: WebSocket | null = null;
let retryCount = 0;

function getRetryDelay(): number {
  return Math.min(BASE_DELAY_MS * 2 ** retryCount, MAX_DELAY_MS);
}

export function sendWs(msg: BrowserMessage): void {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify(msg));
  }
}

export function connectWs(): void {
  window.dispatchEvent(new CustomEvent("bdbox:ws_connecting"));
  _ws = new WebSocket(`ws://${window.location.host}/ws`);

  _ws.addEventListener("open", () => {
    retryCount = 0;
    window.dispatchEvent(new CustomEvent("bdbox:ws_open"));
  });

  _ws.addEventListener("message", ({ data }) => {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(data) as ServerMessage;
    } catch {
      return;
    }
    window.dispatchEvent(new CustomEvent(`bdbox:${msg.type}`, { detail: msg }));
  });

  _ws.addEventListener("close", () => {
    _ws = null;
    const delay = getRetryDelay();
    retryCount++;
    window.dispatchEvent(
      new CustomEvent("bdbox:ws_close", { detail: { retryInMs: delay } }),
    );
    setTimeout(connectWs, delay);
  });

  _ws.addEventListener("error", () => {
    _ws!.close();
  });
}
