import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type ProxyOptions } from 'vite'

// Backend (FastAPI) runs on :8000; override with GLACIER_API for the mock server.
const target = process.env.GLACIER_API ?? 'http://localhost:8000'

// The engine requires its per-install token. In the browser dev setup the proxy adds it, read from GLACIER_TOKEN
// or <GLACIER_HOME or ~/.glacier>/.engine-token. The mock server ignores it.
function engineToken(): string {
  if (process.env.GLACIER_TOKEN) return process.env.GLACIER_TOKEN
  const file = path.join(process.env.GLACIER_HOME ?? path.join(os.homedir(), '.glacier'), '.engine-token')
  try { return fs.readFileSync(file, 'utf8').trim() } catch { return '' }
}
const api: ProxyOptions = {
  target, changeOrigin: true, ws: true,
  configure: p => {
    const add = (req: { setHeader: (k: string, v: string) => void }) => { const t = engineToken(); if (t) req.setHeader('Authorization', `Bearer ${t}`) }
    p.on('proxyReq', add)
    p.on('proxyReqWs', add)
  },
}
const proxy = { '/api': api }

export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? '0.1.0') },
  server: { proxy },
  preview: { proxy },
  build: { chunkSizeWarningLimit: 1500 },
})
