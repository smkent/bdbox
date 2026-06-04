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

export interface VersionInfo {
  bdbox: string;
}

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

export interface ConnectedMessage {
  type: "hello";
  session_id: string;
  version: VersionInfo;
}

export interface ConsoleMessage {
  type: "console";
  text: string;
}

export interface ModelDetailsMessage {
  type: "model_details";
  schema: JsonSchema | null;
  current_values: Record<string, unknown>;
  model_running: boolean;
  model_run_started: string | null;
  model_info: ModelDisplayInfo | null;
}

export interface ParamOverridesMessage {
  type: "param_overrides";
  param_overrides: Record<string, unknown>;
}

export interface RunStartMessage {
  type: "run_start";
  params: Record<string, unknown>;
}

export interface RunOKMessage {
  type: "run_ok";
  elapsed_ms: number;
  current_values: Record<string, unknown>;
}

export interface RunErrorMessage {
  type: "run_error";
  elapsed_ms: number;
}

export function formatElapsedMs(ms: number): string {
  if (ms < 1000) return `${Math.floor(ms)}ms`;
  if (ms < 10_000) return `${(ms / 1000).toFixed(1)}s`;
  const totalS = Math.floor(ms / 1000);
  if (totalS < 60) return `${totalS}s`;
  const s = totalS % 60;
  const totalM = Math.floor(totalS / 60);
  const m = totalM % 60;
  const totalH = Math.floor(totalM / 60);
  const h = totalH % 24;
  const d = Math.floor(totalH / 24);
  const parts: string[] = [];
  if (d) parts.push(`${d}d`);
  if (h || d) parts.push(`${h}h`);
  parts.push(`${m}m`);
  parts.push(`${s}s`);
  return parts.join(" ");
}

export type ServerMessage =
  | ConnectedMessage
  | ConsoleMessage
  | ModelDetailsMessage
  | ParamOverridesMessage
  | RunStartMessage
  | RunOKMessage
  | RunErrorMessage;
