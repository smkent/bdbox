function createMouseCursor() {
  if (window !== window.top) {
    // Child frame: forward mouse events to parent with local coordinates.
    // The parent translates to page coordinates using the iframe's bounding rect.
    document.addEventListener("mousemove", (e) => {
      window.parent.postMessage(
        { type: "cursor_move", x: e.clientX, y: e.clientY },
        "*",
      );
    });
    document.addEventListener("mousedown", (e) => {
      window.parent.postMessage(
        { type: "cursor_click", x: e.clientX, y: e.clientY },
        "*",
      );
    });
    document.addEventListener("mouseup", (e) => {
      window.parent.postMessage(
        { type: "cursor_up", x: e.clientX, y: e.clientY },
        "*",
      );
    });
    return;
  }

  const cursorTime = "200ms";
  const cursor = document.createElement("div");
  cursor.style.cssText = `position: fixed; pointer-events: none; z-index: 999999; width: 20px; height: 20px; transition: left ${cursorTime} ease, top ${cursorTime} ease;`;
  cursor.innerHTML =
    '<svg viewBox="0 0 20 20" width="20" height="20" xmlns="http://www.w3.org/2000/svg"><path d="M 1 1 L 1 16 L 5 12 L 8 19 L 10 18 L 7 11 L 13 11 Z" fill="white" stroke="#222" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>';

  let clickIndicator = null;

  const moveCursor = (x, y) => {
    cursor.style.left = `${x}px`;
    cursor.style.top = `${y}px`;
    if (clickIndicator) {
      clickIndicator.style.left = `${x}px`;
      clickIndicator.style.top = `${y}px`;
    }
  };

  const showClick = (x, y) => {
    cursor.style.transition = "none";
    clickIndicator = document.createElement("div");
    clickIndicator.style.cssText = `
      left: ${x}px; top: ${y}px; position: fixed; pointer-events: none; z-index: 999998;
      width: 24px; height: 24px; border-radius: 50%;
      background-color: rgba(255, 85, 0, 0.85);
      border: 2px solid rgba(45, 15, 0, 0.85);
      opacity: 1;
      transform: translate(-50%, -50%);
    `.trim();
    document.body.appendChild(clickIndicator);
  };

  const showClickUp = (x, y) => {
    cursor.style.transition = `left ${cursorTime} ease, top ${cursorTime} ease`;
    const el = clickIndicator;
    clickIndicator = null;
    if (!el) return;
    const duration = 0.75;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    el.style.transition = `transform ${duration}s ease-out, opacity ${duration}s ease-out`;
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        el.style.transform = "translate(-50%, -50%) scale(1.8)";
        el.style.opacity = "0";
      }),
    );
    setTimeout(() => el.remove(), duration * 1000 * 3);
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.body.appendChild(cursor);
  });

  document.addEventListener("mousemove", (e) =>
    moveCursor(e.clientX, e.clientY),
  );
  document.addEventListener("mousedown", (e) =>
    showClick(e.clientX, e.clientY),
  );
  document.addEventListener("mouseup", (e) =>
    showClickUp(e.clientX, e.clientY),
  );

  window.addEventListener("message", ({ source, data }) => {
    if (
      data?.type !== "cursor_move" &&
      data?.type !== "cursor_click" &&
      data?.type !== "cursor_up"
    )
      return;
    const iframe = [...document.querySelectorAll("iframe")].find(
      (f) => f.contentWindow === source,
    );
    if (!iframe) return;
    const { left, top } = iframe.getBoundingClientRect();
    if (data.type === "cursor_move") moveCursor(left + data.x, top + data.y);
    if (data.type === "cursor_click") showClick(left + data.x, top + data.y);
    if (data.type === "cursor_up") showClickUp(left + data.x, top + data.y);
  });
}

createMouseCursor();
