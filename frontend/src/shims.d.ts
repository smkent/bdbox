// Pure ambient declarations (no imports — this file must remain a global script,
// not a module, so that `declare module` blocks create ambient module declarations
// rather than augmentations).

// Global store types (referenced by the alpinejs Stores interface below and by app.ts)
type RunStatusStore = {
  state: "idle" | "running" | "ok" | "error";
  elapsedMs: string;
  wsState: "connecting" | "connected" | "disconnected";
  retryIn: number;
  runElapsedS: number;
};

type ModelInfoStore = {
  file: string | null;
  module: string | null;
  cls: string | null;
};

// CSS imports handled by esbuild
declare module "*.css" {
  const content: string;
  export default content;
}

// Jedison — no published types
type JedisonInstance = {
  destroy(): void;
  setValue(value: unknown): void;
  on(
    event: string,
    handler: (
      instance: { path: string; getValue(): unknown },
      initiator: string,
    ) => void,
  ): void;
};

declare module "jedison" {
  const jedison: {
    Create: new (options: {
      container: HTMLElement;
      theme: object;
      schema: unknown;
      data: unknown;
      objectAdd?: boolean;
    }) => JedisonInstance;
    Theme: new () => object;
  };
  export default jedison;
}

// Alpine.js — no published types
declare module "alpinejs" {
  interface Stores {
    runStatus: RunStatusStore;
    modelInfo: ModelInfoStore;
  }

  interface Alpine {
    store<K extends keyof Stores>(name: K): Stores[K];
    store<K extends keyof Stores>(name: K, value: Stores[K]): void;
    initTree(el: HTMLElement): void;
    start(): void;
  }

  const alpine: Alpine;
  export default alpine;
}

// Window globals
interface Window {
  __BDBOX__: { viewerPort: number };
  Alpine: unknown;
}
