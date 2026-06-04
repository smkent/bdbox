import type {
  ConnectedMessage,
  ConsoleMessage,
  ParamOverridesMessage,
  RunErrorMessage,
  RunOKMessage,
  RunStartMessage,
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
    "bdbox:param_overrides": CustomEvent<ParamOverridesMessage>;
    "bdbox:run_start": CustomEvent<RunStartMessage>;
    "bdbox:run_ok": CustomEvent<RunOKMessage>;
    "bdbox:run_error": CustomEvent<RunErrorMessage>;
  }
}

export {};
