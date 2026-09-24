/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_MAP_TILE_URL?: string;
  readonly VITE_MAP_TILE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
