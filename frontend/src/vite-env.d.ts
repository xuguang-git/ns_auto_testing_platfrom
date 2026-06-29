/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ALLOW_INSECURE_LOGIN_FALLBACK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
