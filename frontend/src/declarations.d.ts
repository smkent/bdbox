import type {
  ConnectedMessage,
  ConsoleMessage,
  ModelRunStatusMessage,
  ModelDetailsMessage,
} from "./protocol.js";

declare global {
  interface WindowEventMap {
    "bdbox:ws_connecting": CustomEvent;
    "bdbox:ws_open": CustomEvent;
    "bdbox:ws_close": CustomEvent<{ retryInMs: number }>;
    "bdbox:clear_console": CustomEvent;
    "bdbox:console": CustomEvent<ConsoleMessage>;
    "bdbox:hello": CustomEvent<ConnectedMessage>;
    "bdbox:model_details": CustomEvent<ModelDetailsMessage>;
    "bdbox:model_status": CustomEvent<ModelRunStatusMessage>;
  }
}

export {};
