declare const __APP_VERSION__: string

interface Window {
  glacierUpdater?: {
    check(): Promise<{ version: string; notes: string } | null>
    install(version: string): Promise<void>
  }
  __GLACIER_UPDATE_NOTICE__?: { version: string; notes: string }
}
