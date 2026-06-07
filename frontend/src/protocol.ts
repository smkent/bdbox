import type { JsonSchema } from "./types";

// Browser to Server message types

export interface TerminalInfo {
  rows?: number;
  cols: number;
}

export interface ClientInfoMessage {
  type: "client.info";
  terminal: TerminalInfo;
}

export interface ModelResetParamsMessage {
  type: "model.reset_params";
}

export interface ModelSetParamMessage {
  type: "model.set_param";
  field: string;
  value: unknown;
}

export interface ModelSetPresetMessage {
  type: "model.set_preset";
  preset: string;
}

export type BrowserMessage =
  | ClientInfoMessage
  | ModelResetParamsMessage
  | ModelSetParamMessage
  | ModelSetPresetMessage;

export const BrowserMessage = {
  clientInfo: (terminalInfo: TerminalInfo): ClientInfoMessage => ({
    type: "client.info",
    terminal: terminalInfo,
  }),
  modelResetParams: (): ModelResetParamsMessage => ({
    type: "model.reset_params",
  }),
  modelSetParam: (field: string, value: unknown): ModelSetParamMessage => ({
    type: "model.set_param",
    field,
    value,
  }),
  modelSetPreset: (preset: string): ModelSetPresetMessage => ({
    type: "model.set_preset",
    preset,
  }),
} as const;

// Server to browser message types

export interface VersionInfo {
  bdbox: string;
}

export interface ModelDisplayInfo {
  filename: string | null;
  module_name: string | null;
  class_name: string | null;
}

export interface ConnectedMessage {
  type: "hello";
  session_id: string;
  version: VersionInfo;
}

export interface ModelConsoleMessage {
  type: "model.console";
  text: string;
}

export interface ModelDetailsMessage {
  type: "model.details";
  schema?: JsonSchema | null;
  current_values?: Record<string, unknown>;
  model_info?: ModelDisplayInfo | null;
  param_overrides?: Record<string, unknown>;
}

export interface ModelRunStatusMessage {
  type: "model.status";
  status: "running" | "done" | "error";
  started_at?: string | null;
  elapsed_ms?: number;
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
  | ModelConsoleMessage
  | ModelDetailsMessage
  | ModelRunStatusMessage;
