import type { JsonSchema } from "./types";

export class ModelParamsState {
  values: Record<string, unknown> = {};
  overrides: Record<string, unknown> = {};

  get activeValues(): Record<string, unknown> {
    return { ...this.values, ...this.overrides };
  }
}

export class JedisonData {
  schema?: JsonSchema;
  params: ModelParamsState = new ModelParamsState();
}
