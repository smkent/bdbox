const RECONNECT_DELAY_MS = 2000;

export function connectWs() {
  const ws = new WebSocket(`ws://${window.location.host}/ws`);

  ws.addEventListener("message", ({ data }) => {
    const msg = JSON.parse(data);
    window.dispatchEvent(new CustomEvent(`bdbox:${msg.type}`, { detail: msg }));
  });

  ws.addEventListener("close", () => {
    setTimeout(connectWs, RECONNECT_DELAY_MS);
  });

  ws.addEventListener("error", () => {
    ws.close();
  });
}
