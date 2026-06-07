export interface JsonSchema {
  type: string;
  properties?: Record<string, unknown>;
  required?: string[];
  "x-presets"?: Array<{ name: string; description?: string }>;
}
