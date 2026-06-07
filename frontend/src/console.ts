import Alpine from "alpinejs";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";

export class WebConsole {
  private onResize: (() => void) | null = null;
  private containerEl: HTMLElement | null = null;
  private terminal: Terminal;
  private terminalEl: HTMLElement;
  private div: HTMLElement;
  private fitAddon: FitAddon = new FitAddon();
  private resizeObserver: ResizeObserver;

  constructor() {
    this.div = this.createDiv();
    this.terminalEl = this.div.querySelector(
      ".console-terminal",
    ) as HTMLElement;
    this.terminal = this.createTerminal();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.terminalEl);
  }

  private createDiv(): HTMLElement {
    const div = document.createElement("div");
    div.className = "console-panel";
    div.innerHTML = `
      <div class="status-bar">
        <div class="status-run" x-data="{ formatElapsed(s) { const m = Math.floor(s / 60) % 60, h = Math.floor(s / 3600) % 24, d = Math.floor(s / 86400); const p = []; if (d) p.push(d + 'd'); if (h) p.push(h + 'h'); if (m) p.push(m + 'm'); p.push((s % 60) + 's'); return p.join(' '); } }">
          <span x-show="$store.runStatus.wsState === 'connecting'" class="status-connecting"><span class="status-spinner"></span>Connecting…</span>
          <span x-show="$store.runStatus.wsState === 'disconnected'" class="status-disconnected">Disconnected (retry in <span x-text="$store.runStatus.retryIn"></span>s)</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'idle'" class="status-idle">Idle</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'running'" class="status-running"><span class="status-spinner"></span>Running…<span x-show="$store.runStatus.runElapsedS >= 2"> (<span x-text="formatElapsed($store.runStatus.runElapsedS)"></span>)</span></span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'done'" class="status-ok">Done (<span x-text="$store.runStatus.elapsedMs"></span>)</span>
          <span x-show="$store.runStatus.wsState === 'connected' && $store.runStatus.state === 'error'" class="status-error">Error (<span x-text="$store.runStatus.elapsedMs"></span>)</span>
        </div>
      </div>
      <div class="console-terminal"></div>
    `;
    Alpine.initTree(div);
    return div;
  }

  private createTerminal(): Terminal {
    const terminal = new Terminal({
      convertEol: true,
      disableStdin: true,
      scrollback: 1000,
      theme: { background: "#1a1a1a", foreground: "#ccc" },
      fontFamily: "monospace",
      fontSize: 12,
    });
    terminal.loadAddon(this.fitAddon);
    terminal.open(this.terminalEl);
    this.fitAddon.fit();

    window.addEventListener("bdbox:model.clear_console", () =>
      terminal.clear(),
    );
    window.addEventListener("bdbox.server:model.console", ({ detail }) =>
      terminal.write(detail.text),
    );
    return terminal;
  }

  get size(): { rows?: number; cols: number } {
    return {
      rows: this.terminal.rows,
      cols: this.terminal.cols,
    };
  }

  resize(): void {
    this.fitAddon.fit();
    this.onResize?.();
  }

  register(container: HTMLElement, onResize: () => void): void {
    this.containerEl = container;
    this.onResize = onResize;
    this.containerEl.appendChild(this.div);
  }
}
