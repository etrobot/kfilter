/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE?: string
  readonly VITE_API_BASE_URL?: string
  // Add other environment variables as needed
  readonly PROD: boolean
  readonly DEV: boolean
  readonly MODE: 'development' | 'production' | 'test'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
