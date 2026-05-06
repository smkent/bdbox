const RECONNECT_DELAY_MS = 2000;

let _ws = null;

export function sendWs(msg) {
  if (_ws && _ws.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify(msg));
  }
}

export function connectWs() {
  _ws = new WebSocket(`ws://${window.location.host}/ws`);

  _ws.addEventListener("message", ({ data }) => {
    const msg = JSON.parse(data);
    window.dispatchEvent(new CustomEvent(`bdbox:${msg.type}`, { detail: msg }));
  });

  _ws.addEventListener("close", () => {
    _ws = null;
    setTimeout(connectWs, RECONNECT_DELAY_MS);
  });

  _ws.addEventListener("error", () => {
    _ws.close();
  });
}
