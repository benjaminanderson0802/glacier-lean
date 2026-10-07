// Typed client for the Glacier core v0 contract (docs/CONTRACT.md). All calls go to /api (proxied to :8000).

/** Node type id. The full list, labels, settings fields and branch labels come from GET /api/node-types. */
export type NodeKind = string

export type NodeState = 'pending' | 'running' | 'done' | 'failed' | 'waiting' | 'skipped'
export type RunStatus = 'running' | 'waiting' | 'done' | 'failed' | 'rejected'

export interface EnvNode {
  id: string
  type: NodeKind
  config: Record<string, string>
  position: { x: number; y: number }
}
export interface EnvEdge { id: string; source: string; target: string; label: string }
export interface Environment { id: string; name: string; nodes: EnvNode[]; edges: EnvEdge[] }
export interface EnvSummary { id: string; name: string }
export interface RunSummary { run_id: string; env_id: string; status: RunStatus; started_at: string }
export interface RunState {
  run_id: string
  env_id: string
  status: RunStatus
  node_states: Record<string, NodeState>
  outputs: Record<string, string>
  waiting_on: string | null
}
export interface RunEvent { run_id: string; env_id: string; node_id: string; state: NodeState; output?: string }

/** One settings field of a node type (from the node-type catalog). */
export interface ConfigField {
  key: string; label: string; placeholder: string; default: string
  optional?: boolean; multiline?: boolean; options?: string[]; picker?: 'environment'
}
/** One entry of GET /api/node-types. branches = the two labels its outgoing edges carry, or null. */
export interface NodeTypeInfo {
  type: NodeKind; label: string; description: string; fields: ConfigField[]; branches: [string, string] | null
  /** 'options': branch labels are this node's own comma-separated `options` setting (Decide step). */
  branches_from?: 'options'
}

/** Split a comma-separated options setting into labels (trimmed, no blanks, no duplicates). */
export function splitOptions(text: string | undefined): string[] {
  const seen = new Set<string>()
  return String(text ?? '').split(/[,\n]/).map(s => s.trim()).filter(s => s && !seen.has(s.toLowerCase()) && seen.add(s.toLowerCase()))
}

export class ApiError extends Error {
  status: number
  constructor(status: number, msg: string) { super(msg); this.status = status }
}

/** Desktop app sets window.__GLACIER_API__ (e.g. http://127.0.0.1:43123); empty = same origin. */
const BASE: string = ((globalThis as { __GLACIER_API__?: string }).__GLACIER_API__ ?? '').replace(/\/$/, '')

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = res.statusText
    try { const j = await res.json(); detail = j.detail ? JSON.stringify(j.detail) : JSON.stringify(j) } catch { /* not json */ }
    throw new ApiError(res.status, `${method} ${path} -> ${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

const enc = encodeURIComponent
export const api = {
  nodeTypes: () => req<NodeTypeInfo[]>('GET', '/api/node-types'),
  listEnvs: () => req<EnvSummary[]>('GET', '/api/environments'),
  getEnv: (id: string) => req<Environment>('GET', `/api/environments/${enc(id)}`),
  saveEnv: (env: Environment) => req<{ saved: boolean; commit: string }>('PUT', `/api/environments/${enc(env.id)}`, env),
  runEnv: (id: string) => req<{ run_id: string }>('POST', `/api/environments/${enc(id)}/run`),
  listRuns: (envId: string) => req<RunSummary[]>('GET', `/api/runs?env_id=${enc(envId)}`),
  getRun: (runId: string) => req<RunState>('GET', `/api/runs/${enc(runId)}`),
  approve: (runId: string, nodeId: string, approved: boolean) =>
    req<{ ok: boolean }>('POST', `/api/runs/${enc(runId)}/approve`, { node_id: nodeId, approved }),
  listNotes: () => req<string[]>('GET', '/api/vault/notes'),
  getNote: (path: string) => req<{ path: string; body: string }>('GET', `/api/vault/note?path=${enc(path)}`),
  home: () => req<HomeSummary>('GET', '/api/home'),
}

// ---------- Home summary (GET /api/home, docs/CONTRACT.md) ----------
export interface HomeItem { kind: 'approval' | 'claim' | 'failed_run'; title: string; detail: string; at: string; ref: { run_id?: string; node_id?: string; claim_id?: string; env_id?: string } }
export interface HomeRun { run_id: string; env_id: string; name: string; status: 'running' | 'queued' | 'waiting'; step: number; steps: number; started_at: string }
export interface HomeNote { path: string; summary: string; at: string }
export interface HomeSummary {
  /** online: null = still checking (first seconds after start). */
  local_ai: { online: boolean | null; model: string | null }
  counts: { running: number; need_you: number }
  needs_you: HomeItem[]
  running: HomeRun[]
  recent_notes: HomeNote[]
}

/** Home data. Uses GET /api/home; on an older engine without it, builds the same shape from the core endpoints. */
export async function loadHome(): Promise<HomeSummary> {
  try { return await api.home() } catch (e) { if (!(e instanceof ApiError) || e.status !== 404) throw e }
  const envs = await api.listEnvs()
  const names = Object.fromEntries(envs.map(e => [e.id, e.name]))
  const runs = (await Promise.all(envs.map(e => api.listRuns(e.id).catch(() => [] as RunSummary[])))).flat()
  const needs: HomeItem[] = runs.filter(r => r.status === 'waiting' || r.status === 'failed').map(r => ({
    kind: r.status === 'waiting' ? 'approval' : 'failed_run',
    title: r.status === 'waiting' ? 'approval waiting' : 'failed run',
    detail: names[r.env_id] ?? r.env_id, at: r.started_at, ref: { run_id: r.run_id, env_id: r.env_id },
  }))
  const active = runs.filter(r => r.status === 'running')
  const running: HomeRun[] = await Promise.all(active.map(async r => {
    const st = await api.getRun(r.run_id).catch(() => null)
    const states = st ? Object.values(st.node_states) : []
    return { run_id: r.run_id, env_id: r.env_id, name: names[r.env_id] ?? r.env_id, status: 'running', step: states.filter(s => s === 'done').length, steps: states.length, started_at: r.started_at }
  }))
  const notes = await api.listNotes().catch(() => [] as string[])
  const byNew = (a: { at: string }, b: { at: string }) => (b.at ?? '').localeCompare(a.at ?? '')
  return {
    local_ai: { online: null, model: null },
    counts: { running: running.length, need_you: needs.length },
    needs_you: needs.sort(byNew).slice(0, 20),
    running,
    recent_notes: notes.slice(0, 10).map(p => ({ path: p, summary: p.replace(/\.md$/, ''), at: '' })),
  }
}

/** "2h ago" style label for an ISO time; empty when unknown. */
export function ago(iso: string, now = Date.now()): string {
  const t = Date.parse(iso)
  if (!iso || Number.isNaN(t)) return ''
  const s = Math.max(0, Math.round((now - t) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

/** Subscribe to WS /api/events with auto-reconnect. Returns an unsubscribe function. */
export function subscribeEvents(onEvent: (e: RunEvent) => void, onStatus: (connected: boolean) => void): () => void {
  let ws: WebSocket | null = null
  let closed = false
  let timer: ReturnType<typeof setTimeout> | undefined
  const connect = () => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const host = BASE ? new URL(BASE).host : location.host
    ws = new WebSocket(`${BASE.startsWith('https') ? 'wss' : BASE ? 'ws' : proto}://${host}/api/events`)
    ws.onopen = () => onStatus(true)
    ws.onmessage = m => {
      try { onEvent(JSON.parse(String(m.data)) as RunEvent) } catch { /* ignore malformed */ }
    }
    ws.onclose = () => {
      onStatus(false)
      if (!closed) timer = setTimeout(connect, 1000)
    }
    ws.onerror = () => ws?.close()
  }
  connect()
  return () => { closed = true; clearTimeout(timer); ws?.close() }
}

export function slugify(name: string): string {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'env'
}

// ---------- Memory (docs/CONTRACT.md: /api/memory/*) ----------
export interface MemNote { path: string; title: string; author: string; updated: string; tags: string[] }
export interface MemNoteFull { path: string; body: string; meta: Record<string, unknown>; links_out: string[]; links_in: string[] }
export interface MemHit { path: string; title: string; score: number; snippet: string; fallback?: boolean }
export interface MemCommit { commit: string; author: string; date: string; message: string }
export const memory = {
  notes: () => req<MemNote[]>('GET', '/api/memory/notes'),
  note: (path: string) => req<MemNoteFull>('GET', `/api/memory/note?path=${enc(path)}`),
  search: (q: string, mode: 'keyword' | 'meaning' = 'keyword') => req<MemHit[]>('GET', `/api/memory/search?q=${enc(q)}&mode=${mode}`),
  history: (path: string) => req<MemCommit[]>('GET', `/api/memory/history?path=${enc(path)}`),
  /** Save a note written by the owner. Returns the saved version id (commit). */
  save: (path: string, body: string) => req<{ path: string; commit: string }>('PUT', '/api/memory/note', { path, body, author: 'owner' }),
  /** Restore the version before `commit` (or before the latest save). */
  undo: (path: string, commit?: string) => req<{ path: string; commit: string }>('POST', '/api/memory/undo', { path, commit }),
}

// ---------- System (/api/system/*) ----------
export interface SystemCheck {
  cpu_cores: number | null; memory_gb: number | null; disk_free_gb: number | null; ollama_models: string[]
  tools: Record<string, { found: boolean; version: string }>
  recommended: { mode: string; local_model: string; max_parallel_runs: number }
  messages: string[]
}
export const system = {
  check: () => req<SystemCheck>('GET', '/api/system/check'),
  settings: () => req<{ mode: string; local_model: string; max_parallel_runs: number }>('GET', '/api/system/settings'),
}

// ---------- Assistant chat (POST /api/assistant/chat, server-sent AG-UI events) ----------
export interface ChatProposal { id: string; explanation?: string; flow?: { id?: string; name?: string; nodes?: unknown[]; edges?: unknown[] }; [k: string]: unknown }
export type ChatEvent =
  | { type: 'text'; delta: string }
  | { type: 'proposal'; proposal: ChatProposal }
  | { type: 'error'; message: string }
  | { type: 'done' }

export async function chat(message: string, conversationId: string | null, onEvent: (e: ChatEvent) => void): Promise<void> {
  const res = await fetch(BASE + '/api/assistant/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  })
  if (!res.ok || !res.body) throw new ApiError(res.status, `POST /api/assistant/chat -> ${res.status}`)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  const args: Record<string, string> = {}
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i + 2)
      const line = chunk.split('\n').find(l => l.startsWith('data: '))
      if (!line) continue
      let ev: Record<string, string>
      try { ev = JSON.parse(line.slice(6)) } catch { continue }
      if (ev.type === 'TEXT_MESSAGE_CONTENT') onEvent({ type: 'text', delta: ev.delta })
      else if (ev.type === 'TOOL_CALL_ARGS') args[ev.toolCallId] = (args[ev.toolCallId] ?? '') + ev.delta
      else if (ev.type === 'TOOL_CALL_END') { try { onEvent({ type: 'proposal', proposal: JSON.parse(args[ev.toolCallId]) }) } catch { /* partial */ } }
      else if (ev.type === 'RUN_ERROR') onEvent({ type: 'error', message: ev.message })
      else if (ev.type === 'RUN_FINISHED') onEvent({ type: 'done' })
    }
  }
}
export const applyProposal = (id: string, approve: boolean) =>
  req<{ discarded?: boolean; flow_id?: string; run_id?: string; commit?: string }>('POST', `/api/assistant/proposals/${enc(id)}/apply`, { approve })
