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
export interface Environment { id: string; name: string; nodes: EnvNode[]; edges: EnvEdge[]; enabled?: boolean }
export interface EnvSummary { id: string; name: string; enabled?: boolean }
export interface RunSummary { run_id: string; env_id: string; status: RunStatus; started_at: string }
export interface RunTrigger { type: string; node_id?: string; file?: string }
export interface RunState {
  run_id: string
  env_id: string
  status: RunStatus
  node_states: Record<string, NodeState>
  outputs: Record<string, string>
  waiting_on: string | null
  /** Present on GET /api/runs/{id}: per-step usage, acceptance checks, overall verdict, approval question. */
  usage?: Record<string, { model: string | null; route: string | null; tokens_in: number | null; tokens_out: number | null; cost_usd: number | null }>
  verification?: { check: number; kind: string; passed: boolean; evidence: string }[]
  verified?: boolean | null
  waiting_prompt?: string
  trigger?: RunTrigger
}
/** Plain-language explanation of a run (GET /api/runs/{id}/explain). */
export interface RunExplanation { summary: string; steps: { node_id: string; label: string; state: NodeState; sentence: string }[]; verified: boolean | null; needs_you: string | null }
export interface RunEvent { run_id: string; env_id: string; node_id: string; state: NodeState; output?: string }
/** Live memory event (docs/CONTRACT.md): a note was created, updated or deleted. */
export interface MemoryEvent { type: 'memory'; path: string; change: 'created' | 'updated' | 'deleted'; author: string; run_id: string }

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
/** Desktop app sets window.__GLACIER_TOKEN__ (the per-install engine token). In the browser dev setup the Vite proxy adds it. */
const TOKEN: string = (globalThis as { __GLACIER_TOKEN__?: string }).__GLACIER_TOKEN__ ?? ''
const auth = (h: Record<string, string> = {}): Record<string, string> => (TOKEN ? { ...h, Authorization: `Bearer ${TOKEN}` } : h)

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: auth(body === undefined ? {} : { 'Content-Type': 'application/json' }),
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
  restoreEnv: (id: string, commit: string) => req<{ restored: boolean; new_commit: string }>('POST', `/api/environments/${enc(id)}/restore`, { commit }),
  listRuns: (envId: string) => req<RunSummary[]>('GET', `/api/runs?env_id=${enc(envId)}`),
  getRun: (runId: string) => req<RunState>('GET', `/api/runs/${enc(runId)}`),
  approve: (runId: string, nodeId: string, approved: boolean) =>
    req<{ ok: boolean }>('POST', `/api/runs/${enc(runId)}/approve`, { node_id: nodeId, approved }),
  listNotes: () => req<string[]>('GET', '/api/vault/notes'),
  getNote: (path: string) => req<{ path: string; body: string }>('GET', `/api/vault/note?path=${enc(path)}`),
  home: () => req<HomeSummary>('GET', '/api/home'),
  runChanges: (runId: string) => req<{ path: string; commit: string; author: string; repo: string }[]>('GET', `/api/runs/${enc(runId)}/changes`),
  explain: (runId: string) => req<RunExplanation>('GET', `/api/runs/${enc(runId)}/explain`),
  undoRun: (runId: string) => req<Record<string, unknown>>('POST', `/api/runs/${enc(runId)}/undo`),
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
    ws = new WebSocket(`${BASE.startsWith('https') ? 'wss' : BASE ? 'ws' : proto}://${host}/api/events`, TOKEN ? ['glacier-events', TOKEN] : ['glacier-events'])
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
export interface MemNoteFull { path: string; body: string; meta: Record<string, unknown>; links_out: string[]; links_in: string[]; links_out_status?: { target: string; status: string; display: string }[] }
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
  rename: (from: string, to: string) => req<{ path: string; commit: string }>('POST', '/api/memory/rename', { from, to }),
}

// ---------- System (/api/system/*) ----------
export interface SystemCheck {
  cpu_cores: number | null; memory_gb: number | null; disk_free_gb: number | null; ollama_models: string[]
  tools: Record<string, { found: boolean; version: string }>
  recommended: { mode: string; local_model: string; max_parallel_runs: number }
  messages: string[]
}
export interface EffectiveSettings { mode: string; local_model: string; max_parallel_runs: number; ask_route?: 'codex' | 'local' | 'unavailable'; ask_route_reason?: string }
export const system = {
  check: () => req<SystemCheck>('GET', '/api/system/check'),
  settings: () => req<EffectiveSettings>('GET', '/api/system/settings'),
}

// ---------- Assistant chat (POST /api/assistant/chat, server-sent AG-UI events) ----------
export interface ProposalCheck { kind?: string; cmd?: string; rubric?: string; question?: string; schema?: unknown }
export interface ChatProposal { id: string; explanation?: string; run_existing?: boolean; flow?: { id?: string; name?: string; goal?: string; nodes?: unknown[]; edges?: unknown[]; acceptance?: ProposalCheck[] }; [k: string]: unknown }
export type ChatEvent =
  | { type: 'text'; delta: string }
  | { type: 'proposal'; proposal: ChatProposal }
  | { type: 'error'; message: string }
  | { type: 'done' }

export async function chat(message: string, conversationId: string | null, onEvent: (e: ChatEvent) => void): Promise<void> {
  const res = await fetch(BASE + '/api/assistant/chat', {
    method: 'POST', headers: auth({ 'Content-Type': 'application/json' }),
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
// ---------- Past Ask conversations (GET/POST /api/assistant/conversations*) ----------
export interface ConversationItem { id: string; title: string; updated: string; messages: number }
export interface ConversationFull { id: string; title: string; messages: { who: 'you' | 'glacier'; text: string; at: string }[] }
export const conversationsApi = {
  list: (q = '') => req<ConversationItem[]>('GET', `/api/assistant/conversations${q.trim() ? `?q=${enc(q.trim())}` : ''}`),
  get: (id: string) => req<ConversationFull>('GET', `/api/assistant/conversations/${enc(id)}`),
  rename: (id: string, title: string) => req<{ id: string; title: string; commit: string }>('POST', `/api/assistant/conversations/${enc(id)}/rename`, { title }),
}
export const applyProposal = (id: string, approve: boolean, runNow = false) =>
  req<{ discarded?: boolean; flow_id?: string; run_id?: string; commit?: string; status?: string }>('POST', `/api/assistant/proposals/${enc(id)}/apply`, runNow ? { approve, run_now: true } : { approve })

// ---------- Claims (GET/POST /api/claims*) ----------
export interface ClaimSummary { id: string; kind: string; summary: string; status: string; assigned_to: string | null; updated: string }
export interface ClaimFull { meta: Record<string, string | number | null> & { id: string; kind?: string; summary?: string; status?: string; updated?: string; run_id?: string }; body: string }
export const claimsApi = {
  list: (status?: string) => req<ClaimSummary[]>('GET', `/api/claims${status ? `?status=${enc(status)}` : ''}`),
  get: (id: string) => req<ClaimFull>('GET', `/api/claims/${enc(id)}`),
  decide: (id: string, action: 'approve' | 'reject' | 'research_more', option = '') => req<{ status: string }>('POST', `/api/claims/${enc(id)}/decision`, { action, option }),
  rerun: (id: string) => req<{ run_id: string; env_id: string }>('POST', `/api/claims/${enc(id)}/rerun`),
}
/** Split a claim body into its "## Heading" sections. */
export function sections(body: string): Record<string, string> {
  const out: Record<string, string> = {}
  let cur = ''
  for (const line of body.split('\n')) {
    const m = line.match(/^##\s+(.+)$/)
    if (m) { cur = m[1].trim(); out[cur] = ''; continue }
    if (cur) out[cur] += line + '\n'
  }
  for (const k of Object.keys(out)) out[k] = out[k].trim()
  return out
}

// ---------- Templates (GET /api/templates) ----------
export interface TemplateItem { id: string; name: string; description: string; author?: string; license?: string; review_status: string; installable: boolean; template?: Environment & { description?: string; tags?: string[] } }
export const templatesApi = { list: () => req<TemplateItem[]>('GET', '/api/templates') }

// ---------- Memory map, add, cleanup ----------
export interface GraphNode { id: string; title: string; kind: 'note' | 'run' | 'flow' | 'claim' | string; author: string }
export interface GraphEdge { source: string; target: string; kind: 'wrote' | 'link' | string }
export interface HygieneProposal { id: string; kind: 'merge' | 'archive' | string; paths: string[]; reason: string }
export const memoryMore = {
  graph: (limit?: number) => req<{ nodes: GraphNode[]; edges: GraphEdge[] }>('GET', `/api/memory/graph${limit ? `?limit=${limit}` : ''}`),
  hygiene: () => req<HygieneProposal[]>('GET', '/api/memory/hygiene'),
  scan: () => req<HygieneProposal[]>('POST', '/api/memory/hygiene/scan'),
  decide: (id: string, approve: boolean) => req<{ id: string; status: string; commit?: string }>('POST', `/api/memory/hygiene/${enc(id)}`, { approve }),
}

/** Multipart upload helpers (file drop and chat-export import). */
async function upload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(BASE + path, { method: 'POST', body: form, headers: auth() })
  if (!res.ok) {
    let detail = res.statusText
    try { const j = await res.json(); detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j) } catch { /* not json */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}
export const addToMemory = {
  file: (file: File, project?: string) => { const f = new FormData(); f.append('file', file); if (project) f.append('project', project); return upload<Record<string, unknown>>('/api/files', f) },
  chatExport: (source: 'chatgpt' | 'claude', file: File) => { const f = new FormData(); f.append('source', source); f.append('file', file); return upload<Record<string, number>>('/api/imports', f) },
  projects: () => req<{ name: string }[] | string[]>('GET', '/api/projects'),
  imports: () => req<{ source: string; last_import: string | null; added: number; updated: number; unchanged: number }[]>('GET', '/api/imports'),
  refreshImports: () => req<Record<string, Record<string, number>>>('POST', '/api/imports/refresh'),
}

// ---------- Coding sessions (read-only mirror of Codex / OpenCode) ----------
export interface CodingSession { id: string; tool: string; source?: string; started: string | null; updated: string | null; title: string; cwd: string; active: boolean }
export interface SessionEvent { type: string; text: string; timestamp?: string | null }
export const sessionsApi = {
  list: () => req<CodingSession[]>('GET', '/api/sessions'),
  get: (id: string) => req<CodingSession & { events: SessionEvent[] }>('GET', `/api/sessions/${enc(id)}`),
  save: (id: string) => req<{ saved: boolean; path: string }>('POST', `/api/sessions/${enc(id)}/save-to-memory`),
}

// ---------- Settings: secrets, usage, data ----------
export interface CostGroup { runs: number; steps: number; tokens_in: number; tokens_out: number; cost_usd: number; route?: string; model?: string }
export interface Costs { total_usd: number; by_route: CostGroup[]; by_model: CostGroup[]; local_share: number; paid_cap_usd: number }
export interface VaultCompat { ok: boolean; notes_checked: number; problems: { path: string; kind: string; detail: string; fix_hint: string }[] }
export const settingsApi = {
  secrets: () => req<string[]>('GET', '/api/secrets'),
  setSecret: (name: string, value: string) => req<{ saved: boolean }>('PUT', `/api/secrets/${enc(name)}`, { value }),
  deleteSecret: (name: string) => req<{ deleted: boolean }>('DELETE', `/api/secrets/${enc(name)}`),
  costs: (days = 30) => req<Costs>('GET', `/api/costs?days=${days}`),
  compat: () => req<VaultCompat>('GET', '/api/memory/compat'),
}

// ---------- First-run starter setup ----------
export interface StarterProposal {
  applied: boolean
  mode: 'low' | 'standard'; local_model: string; reason: string
  coding_agents_found: { id: string; name: string; found: boolean; version: string; usable_as_step: boolean }[]
  suggested_automations: { template_id: string; name: string; why: string; requires_local_model: boolean }[]
  missing_but_useful: { name: string; why: string; license: string; download_page: string }[]
}
export const starterApi = {
  get: () => req<StarterProposal>('GET', '/api/starter'),
  apply: (template_ids: string[], mode: string) => req<{ created: { template_id: string; id: string; name: string }[]; mode: string; local_model: string }>('POST', '/api/starter/apply', { template_ids, mode }),
}
