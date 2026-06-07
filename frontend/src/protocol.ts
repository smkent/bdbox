import type { JsonSchema } from "./types";
import { ModelParamsState } from "./classes";

// Browser to Server message types

export interface BrowserMessage {
  readonly type: string;
}

export class TerminalInfo {
  constructor(
    public rows?: number,
    public cols: number = 80,
  ) {}
}

export class ClientInfoMessage implements BrowserMessage {
  public readonly type = "client.info";
  constructor(public terminal: TerminalInfo) {}
}

export class ModelResetParamsMessage implements BrowserMessage {
  public readonly type = "model.reset_params";
}

export class ModelSetParamMessage implements BrowserMessage {
  public readonly type = "model.set_param";
  constructor(
    public field: string,
    public value: unknown,
  ) {}
}

export class ModelSetPresetMessage implements BrowserMessage {
  public readonly type = "model.set_preset";
  constructor(public preset: string) {}
}

// Server to browser message types

export interface VersionInfo {
  bdbox: string;
  protocol: number;
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
  model_info?: ModelDisplayInfo | null;
  params?: ModelParamsState | null;
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
