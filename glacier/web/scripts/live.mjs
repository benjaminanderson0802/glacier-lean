#!/usr/bin/env node
// Start a real local engine and Vite UI together. By default the engine gets a
// disposable home so this development session cannot touch the user's data.
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import net from 'node:net'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const backend = path.join(root, 'glacier/backend')
const web = path.join(root, 'glacier/web')
const pythonNames = process.platform === 'win32' ? ['Scripts/python.exe', 'Scripts/python'] : ['bin/python']
const pythonCandidates = [
  process.env.GLACIER_PYTHON,
  ...pythonNames.map(name => path.join(os.homedir(), 'w/glacier-lean/.venv', name)),
  ...pythonNames.map(name => path.join(root, '.venv', name)),
  ...pythonNames.map(name => path.join('/workspaces/glacier-lean/.venv', name)),
].filter(Boolean)
const python = pythonCandidates.find(candidate => existsSync(candidate))
if (!python) {
  console.error('Could not find the Glacier backend venv. Set GLACIER_PYTHON or install ~/w/glacier-lean/.venv.')
  process.exit(1)
}

async function freePort() {
  const server = net.createServer()
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
  const port = server.address().port
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return port
}

const homeOwned = !process.env.GLACIER_HOME
const home = process.env.GLACIER_HOME || mkdtempSync(path.join(os.tmpdir(), 'glacier-live-'))
const backendPort = Number(process.env.GLACIER_API_PORT) || await freePort()
const uiPort = Number(process.env.GLACIER_UI_PORT) || await freePort()
const api = `http://127.0.0.1:${backendPort}`
const ui = `http://127.0.0.1:${uiPort}`
const childEnv = { ...process.env, GLACIER_HOME: home, GLACIER_DEV: '1', GLACIER_DEV_ORIGINS: ui,
  GIT_AUTHOR_NAME: process.env.GIT_AUTHOR_NAME || 'Glacier Live',
  GIT_AUTHOR_EMAIL: process.env.GIT_AUTHOR_EMAIL || 'glacier-live@localhost',
  GIT_COMMITTER_NAME: process.env.GIT_COMMITTER_NAME || 'Glacier Live',
  GIT_COMMITTER_EMAIL: process.env.GIT_COMMITTER_EMAIL || 'glacier-live@localhost' }
// Always use the token in this home, not a caller's unrelated install token.
delete childEnv.GLACIER_TOKEN

const procs = []
let stopping
function start(command, args, cwd, env = childEnv) {
  const proc = spawn(command, args, { cwd, env, stdio: 'inherit', detached: process.platform !== 'win32' })
  proc.once('exit', (code, signal) => {
    if (!stopping) {
      console.error(`${path.basename(command)} stopped (${signal || code}); shutting down the live session.`)
      void stop()
    }
  })
  procs.push(proc)
  return proc
}
async function waitForBackend() {
  const deadline = Date.now() + 60000
  while (Date.now() < deadline) {
    try {
      if ((await fetch(`${api}/api/health`)).ok) {
        // Trigger token creation, then wait until the proxy can read it.
        await fetch(`${api}/api/environments`)
        if (readFileSync(path.join(home, '.engine-token'), 'utf8').trim()) return
      }
    } catch { /* backend is still starting */ }
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`Timed out waiting for the real backend at ${api}`)
}

async function stop() {
  if (stopping) return stopping
  stopping = (async () => {
    for (const proc of [...procs].reverse()) {
      if (proc.exitCode !== null || proc.signalCode !== null) continue
      try { process.kill(process.platform === 'win32' ? proc.pid : -proc.pid, 'SIGTERM') } catch { /* already gone */ }
    }
    await new Promise(resolve => setTimeout(resolve, 500))
    for (const proc of procs) {
      if (proc.exitCode !== null || proc.signalCode !== null) continue
      try { process.kill(process.platform === 'win32' ? proc.pid : -proc.pid, 'SIGKILL') } catch { /* already gone */ }
    }
    if (homeOwned) rmSync(home, { recursive: true, force: true })
  })()
  return stopping
}

process.once('SIGINT', () => { void stop().finally(() => process.exit(0)) })
process.once('SIGTERM', () => { void stop().finally(() => process.exit(0)) })

try {
  start(python, ['-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', String(backendPort)], backend)
  await waitForBackend()
  const vite = path.join(web, 'node_modules/vite/bin/vite.js')
  start(process.execPath, [vite, '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'], web,
    { ...childEnv, GLACIER_API: api })
  console.log(`Glacier real backend: ${api}`)
  console.log(`Glacier dev screen:   ${ui}`)
  console.log(`Development data:     ${homeOwned ? '(temporary, removed on exit)' : home}`)
} catch (error) {
  console.error(error)
  await stop()
  process.exitCode = 1
}
