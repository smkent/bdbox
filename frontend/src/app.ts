import "golden-layout/dist/css/goldenlayout-base.css";
import "golden-layout/dist/css/themes/goldenlayout-dark-theme.css";
import "@xterm/xterm/css/xterm.css";
import "./app.css";
import { WebSocketManager } from "./websocket";
import { EventManager } from "./events";
import { Layout } from "./layout";
import { UIState } from "./ui-state";

class App {
  private webSocketManager: WebSocketManager = new WebSocketManager();
  private eventManager: EventManager = new EventManager();
  private layout: Layout;
  private uiState: UIState = new UIState();

  constructor() {
    this.layout = new Layout(this.webSocketManager);
    this.webSocketManager.connect();
  }
}

window.App = new App();
