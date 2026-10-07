import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend (FastAPI) runs on :8000; override with GLACIER_API for the mock server.
const target = process.env.GLACIER_API ?? 'http://localhost:8000'
const proxy = { '/api': { target, changeOrigin: true, ws: true } }

export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? '0.1.0') },
  server: { proxy },
  preview: { proxy },
  build: { chunkSizeWarningLimit: 1500 },
})
