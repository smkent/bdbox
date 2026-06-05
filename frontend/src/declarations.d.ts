import type {
  ConnectedMessage,
  ModelConsoleMessage,
  ModelRunStatusMessage,
  ModelDetailsMessage,
} from "./protocol.js";

declare global {
  interface WindowEventMap {
    "bdbox:ws.connecting": CustomEvent;
    "bdbox:ws.open": CustomEvent;
    "bdbox:ws.close": CustomEvent<{ retryInMs: number }>;
    "bdbox:model.clear_console": CustomEvent;
    "bdbox.server:hello": CustomEvent<ConnectedMessage>;
    "bdbox.server:model.console": CustomEvent<ModelConsoleMessage>;
    "bdbox.server:model.details": CustomEvent<ModelDetailsMessage>;
    "bdbox.server:model.status": CustomEvent<ModelRunStatusMessage>;
  }
}

export {};
