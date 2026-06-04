// Browser to Server message types

export interface TerminalSizeMessage {
  type: "terminal_size";
  cols: number;
  rows?: number;
}

export interface UpdateParamMessage {
  type: "update_param";
  field: string;
  value: unknown;
}

export interface SelectPresetMessage {
  type: "select_preset";
  preset: string;
}

export interface ResetParamsMessage {
  type: "reset_params";
}

export type BrowserMessage =
  | TerminalSizeMessage
  | UpdateParamMessage
  | SelectPresetMessage
  | ResetParamsMessage;

export const BrowserMessage = {
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

// Server to browser message types

export interface ModelDisplayInfo {
  file: string | null;
  module: string | null;
  cls: string | null;
}

export interface JsonSchema {
  type: string;
  properties?: Record<string, unknown>;
  required?: string[];
  "x-presets"?: Array<{ name: string; description?: string }>;
}

interface ServerMessageWithSessionID {
  session_id: string;
}

export interface ConsoleMessage extends ServerMessageWithSessionID {
  type: "console";
  text: string;
}

export interface SchemaMessage extends ServerMessageWithSessionID {
  type: "schema";
  schema: JsonSchema | null;
  current_values: Record<string, unknown>;
  model_running: boolean;
  model_run_started: string | null;
  model_info: ModelDisplayInfo | null;
}

export interface ParamOverridesMessage extends ServerMessageWithSessionID {
  type: "param_overrides";
  param_overrides: Record<string, unknown>;
}

export interface RunStartMessage extends ServerMessageWithSessionID {
  type: "run_start";
  params: Record<string, unknown>;
}

export interface RunOKMessage extends ServerMessageWithSessionID {
  type: "run_ok";
  elapsed_ms: string;
  current_values: Record<string, unknown>;
}

export interface RunErrorMessage extends ServerMessageWithSessionID {
  type: "run_error";
  elapsed_ms: string;
}

export type ServerMessage =
  | ConsoleMessage
  | SchemaMessage
  | ParamOverridesMessage
  | RunStartMessage
  | RunOKMessage
  | RunErrorMessage;
