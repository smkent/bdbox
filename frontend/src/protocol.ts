// Outgoing messages (browser → server)

export type TerminalSizeMessage = {
  type: "terminal_size";
  cols: number;
  rows?: number;
};

export type UpdateParamMessage = {
  type: "update_param";
  field: string;
  value: unknown;
};

export type SelectPresetMessage = {
  type: "select_preset";
  preset: string;
};

export type ResetParamsMessage = {
  type: "reset_params";
};

export type OutgoingMessage =
  | TerminalSizeMessage
  | UpdateParamMessage
  | SelectPresetMessage
  | ResetParamsMessage;

export const OutgoingMessage = {
  terminalSize: (cols: number, rows?: number): TerminalSizeMessage => ({
    type: "terminal_size",
    cols,
    rows,
  }),
  updateParam: (field: string, value: unknown): UpdateParamMessage => ({
    type: "update_param",
    field,
    value,
  }),
  selectPreset: (preset: string): SelectPresetMessage => ({
    type: "select_preset",
    preset,
  }),
  resetParams: (): ResetParamsMessage => ({ type: "reset_params" }),
} as const;

// Incoming messages (server → browser)

export type ConsoleMessage = {
  type: "console";
  text: string;
  stream: "stdout";
};

export type ModelDisplayInfo = {
  file: string | null;
  module: string | null;
  cls: string | null;
};

export type JsonSchema = {
  type: string;
  properties?: Record<string, unknown>;
  required?: string[];
  "x-presets"?: Array<{ name: string; description?: string }>;
};

interface ServerMessage {
  session_id: string;
}

export interface SchemaMessage extends ServerMessage {
  type: "schema";
  schema: JsonSchema | null;
  current_values: Record<string, unknown>;
  model_running: boolean | null;
  model_run_started: string | null;
  model_info: ModelDisplayInfo | null;
}

export interface ParamOverridesMessage extends ServerMessage {
  type: "param_overrides";
  param_overrides: Record<string, unknown>;
}

export interface RunStartMessage extends ServerMessage {
  type: "run_start";
  params: Record<string, unknown>;
}

export interface RunOKMessage extends ServerMessage {
  type: "run_ok";
  elapsed_ms: string;
  current_values: Record<string, unknown>;
}

export interface RunErrorMessage extends ServerMessage {
  type: "run_error";
  elapsed_ms: string;
}

export type IncomingMessage =
  | ConsoleMessage
  | SchemaMessage
  | ParamOverridesMessage
  | RunStartMessage
  | RunOKMessage
  | RunErrorMessage;
