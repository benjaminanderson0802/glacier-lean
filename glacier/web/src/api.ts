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
}

export class ApiError extends Error {
  status: number
  constructor(status: number, msg: string) { super(msg); this.status = status }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
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
}

/** Subscribe to WS /api/events with auto-reconnect. Returns an unsubscribe function. */
export function subscribeEvents(onEvent: (e: RunEvent) => void, onStatus: (connected: boolean) => void): () => void {
  let ws: WebSocket | null = null
  let closed = false
  let timer: ReturnType<typeof setTimeout> | undefined
  const connect = () => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/api/events`)
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
