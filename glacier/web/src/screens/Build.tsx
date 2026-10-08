import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background, Controls, MiniMap, MarkerType, ReactFlow, ReactFlowProvider, addEdge, applyEdgeChanges, applyNodeChanges, EdgeText,
  type Connection, type Edge, type EdgeChange, type NodeChange, useReactFlow,
} from '@xyflow/react'
import {
  ApiError, ago, api, memory, settingsApi, slugify, splitOptions, subscribeEvents, type MemCommit,
  type EnvSummary, type NodeTypeInfo, type Environment, type NodeKind, type RunEvent, type RunState, type RunSummary,
} from '../api.ts'
import { GlacierNode, nodeTypes as baseNodeTypes, type GNode } from './GlacierNode.tsx'
import { TerminalPanel } from './TerminalPanel.tsx'
import { VaultView } from './VaultView.tsx'
import { tok } from '../ui/tok.ts'
import { takeDraft } from '../draft.ts'
import { getLanguage, t } from '../i18n/index.ts'
import { SIMPLE_STEP_TYPES, useLayout } from '../layout.ts'
import dagre from '@dagrejs/dagre'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'
import './build.css'

type Selection = { kind: 'node' | 'edge'; id: string } | null

const nextId = (prefix: string, ids: string[]) => {
  let max = 0
  for (const id of ids) {
    const m = id.match(new RegExp(`^${prefix}(\\d+)$`))
    if (m) max = Math.max(max, Number(m[1]))
  }
  return `${prefix}${max + 1}`
}

const edgeStyle = (label: string) => ({
  type: 'pixel',
  label: label || undefined,
  markerEnd: { type: MarkerType.ArrowClosed, color: tok('--g-line') },
  className: label ? `edge-${label}` : undefined,
})

function PixelEdge({ id, sourceX, sourceY, targetX, targetY, markerEnd, style, selected, label }: import('@xyflow/react').EdgeProps) {
  const middle = Math.round((sourceX + targetX) / 2)
  const vertical = Math.abs(targetY - sourceY) > Math.abs(targetX - sourceX)
  const labelX = Math.round((sourceX + targetX) / 2 + (vertical ? 20 : 0))
  const labelY = Math.round((sourceY + targetY) / 2 + (vertical ? 0 : -16))
  const d = `M ${sourceX} ${sourceY} H ${middle} V ${targetY} H ${targetX}`
  return <>
    <path id={id} d={d} className={`react-flow__edge-path${selected ? ' selected' : ''}`} markerEnd={markerEnd} style={style} />
    {label && <EdgeText x={labelX} y={labelY} label={label} labelShowBg />}
  </>
}

function httpAddressError(address: string, allowedSites: string): string {
  const value = address.trim()
  if (!value) return ''
  let parsed: URL
  try { parsed = new URL(value) } catch { return t('http.badAddress') }
  if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname || parsed.username || parsed.password || parsed.hash || /\{secret:/i.test(value)) return t('http.badAddress')
  const host = parsed.hostname.toLowerCase().replace(/\.$/, '')
  const allowed = allowedSites.split(',').map(s => s.trim().toLowerCase().replace(/\.$/, '')).filter(Boolean)
  if (!allowed.some(site => host === site || host.endsWith(`.${site}`))) return t('http.siteNotAllowed', { host })
  return ''
}

const HTTP_LABELS: Record<string, string> = {
  method: 'http.method', url: 'http.address', allowed_sites: 'http.allowedSites', headers: 'http.headers',
  body: 'http.body', body_type: 'http.bodyFormat', timeout: 'http.timeout', expect_status: 'http.expectedStatus',
  allow_private_network: 'http.privateNetwork',
}
const HTTP_PLACEHOLDERS: Record<string, string> = {
  url: 'http.addressPlaceholder', allowed_sites: 'http.allowedSitesPlaceholder',
  headers: 'http.headersPlaceholder', body: 'http.bodyPlaceholder', expect_status: 'http.expectedStatusPlaceholder',
}
const httpOptionLabel = (field: string, value: string) => {
  const key = field === 'method' ? `http.method.${value.toLowerCase()}`
    : field === 'body_type' ? `http.bodyFormat.${value.toLowerCase()}`
      : field === 'allow_private_network' ? `http.privateNetwork.${value.toLowerCase()}` : ''
  return key ? t(key) : value
}

function HttpResult({ text, elapsed }: { text: string; elapsed?: number }) {
  const match = text.match(/^Status: (\d{3})\s*\n\n([\s\S]*)$/)
  if (!match) return null
  const body = match[2].slice(0, 2000)
  return <div className="http-result" data-testid="http-result-summary">
    <span>{t('http.responseStatus', { status: match[1] })}</span>
    <span>{t('http.responseTime', { time: elapsed === undefined ? t('http.timeUnavailable') : `${elapsed} ms` })}</span>
    <pre data-testid="http-result-body">{body}{match[2].length > 2000 ? t('http.responseTrimmed') : ''}</pre>
  </div>
}

function toFlow(env: Environment): { nodes: GNode[]; edges: Edge[] } {
  return {
    nodes: env.nodes.map(n => ({ id: n.id, type: n.type, position: n.position ?? { x: 0, y: 0 }, data: { config: { ...n.config } } })),
    edges: env.edges.map(e => ({ id: e.id, source: e.source, target: e.target, ...edgeStyle(e.label ?? '') })),
  }
}

function fromFlow(id: string, name: string, nodes: GNode[], edges: Edge[]): Environment {
  return {
    id, name,
    nodes: nodes.map(n => ({
      id: n.id, type: n.type as NodeKind, config: { ...n.data.config },
      position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
    })),
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, label: typeof e.label === 'string' ? e.label : '' })),
  }
}

type BuildProps = { initialEnv?: string; initialRun?: string; newName?: string; onStatus?: (s: string) => void }

export default function BuildScreen(props: BuildProps) {
  return <ReactFlowProvider><Shell {...props} /></ReactFlowProvider>
}

function Shell({ initialEnv, initialRun, newName: newNameProp, onStatus }: BuildProps) {
  const reactFlow = useReactFlow<GNode, Edge>()
  const [envs, setEnvs] = useState<EnvSummary[]>([])
  const [unsaved, setUnsaved] = useState<EnvSummary[]>([])
  const [envId, setEnvId] = useState<string | null>(null)
  const [envName, setEnvName] = useState('')
  const [nodes, setNodes] = useState<GNode[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [dirty, setDirty] = useState(false)
  const [lastCommit, setLastCommit] = useState('')
  const [msg, setMsg] = useState('')
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [activeRun, setActiveRun] = useState<RunState | null>(null)
  const [selected, setSelected] = useState<Selection>(null)
  const [undoStack, setUndoStack] = useState<Array<{ nodes: GNode[]; edges: Edge[] }>>([])
  const [tab, setTab] = useState<'canvas' | 'vault'>('canvas')
  const [wsUp, setWsUp] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)
  const [catalog, setCatalog] = useState<NodeTypeInfo[]>([])
  const [secretNames, setSecretNames] = useState<string[]>([])
  const [httpTimings, setHttpTimings] = useState<Record<string, number>>({})
  const httpStarts = useRef<Record<string, number>>({})
  const typeInfo = useCallback((k: string) => catalog.find(t => t.type === k), [catalog])
  const layout = useLayout()
  const [moreFields, setMoreFields] = useState(false)
  const [deleteUndo, setDeleteUndo] = useState<UndoAction | null>(null)
  const [flowRemoved, setFlowRemoved] = useState(false)
  /** Branch labels a node's outgoing edges can carry: a fixed pair, or the node's own options (Decide). */
  const branchLabels = useCallback((n: GNode | undefined): string[] | null => {
    const t = n ? typeInfo(n.type as string) : undefined
    if (!n || !t) return null
    if (t.branches) return t.branches
    return t.branches_from === 'options' ? splitOptions(n.data.config.options) : null
  }, [typeInfo])
  const flowNodeTypes = useMemo(() => ({ ...baseNodeTypes, ...Object.fromEntries(catalog.map(t => [t.type, GlacierNode])) }), [catalog])
  const flowEdgeTypes = useMemo(() => ({ pixel: PixelEdge }), [])

  // Refit after the terminal row opens so the reduced canvas still shows every node.
  useEffect(() => {
    if (!activeRun || !selected || tab !== 'canvas') return
    const frame = requestAnimationFrame(() => { void reactFlow.fitView({ padding: 0.2, duration: 0 }) })
    return () => cancelAnimationFrame(frame)
  }, [activeRun?.run_id, selected?.id, tab, reactFlow])

  /** Fields of the flow the builder does not edit (goal, acceptance checks, isolate, ...): kept on save. */
  const extras = useRef<Record<string, unknown>>({})
  const envIdRef = useRef(envId)
  envIdRef.current = envId
  const activeRunIdRef = useRef<string | null>(null)
  activeRunIdRef.current = activeRun?.run_id ?? null

  // ---------- loading ----------
  const refreshEnvs = useCallback(() => api.listEnvs().then(setEnvs).catch(e => setMsg(String(e))), [])
  useEffect(() => { refreshEnvs() }, [refreshEnvs])
  useEffect(() => { api.nodeTypes().then(setCatalog).catch(e => setMsg(String(e))) }, [])
  useEffect(() => { settingsApi.secrets().then(setSecretNames).catch(() => setSecretNames([])) }, [])

  const refreshRuns = useCallback((id: string) => {
    api.listRuns(id).then(r => { if (envIdRef.current === id) setRuns(r) }).catch(e => setMsg(String(e)))
  }, [])

  const loadEnv = useCallback(async (id: string, fallbackName?: string) => {
    setFlowRemoved(false); setDeleteUndo(null)
    setEnvId(id); setSelected(null); setActiveRun(null); setLastCommit(''); setMsg(''); setRuns([]); setTab('canvas')
    try {
      const env = await api.getEnv(id)
      const { id: _i, name: _n, nodes: _no, edges: _e, ...rest } = env as Environment & Record<string, unknown>
      void _i; void _n; void _no; void _e
      extras.current = rest
      const f = toFlow(env)
      setEnvName(env.name); setNodes(f.nodes); setEdges(f.edges); setDirty(false)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setEnvName(fallbackName ?? id); setNodes([]); setEdges([]); setDirty(true)
      } else setMsg(String(e))
    }
    refreshRuns(id)
  }, [refreshRuns])

  // Saved versions of this flow (every Save is a version; Restore makes an earlier one current again).
  const [versions, setVersions] = useState<MemCommit[]>([])
  const [confirmRestore, setConfirmRestore] = useState('')
  const loadVersions = useCallback((id: string) => {
    memory.history(`environments/${id}.json`).then(v => setVersions(v.slice(0, 8))).catch(() => setVersions([]))
  }, [])
  useEffect(() => { setConfirmRestore(''); if (envId) loadVersions(envId); else setVersions([]) }, [envId, lastCommit, loadVersions])
  const restoreVersion = async (commit: string) => {
    if (!envId) return
    try {
      const r = await api.restoreEnv(envId, commit)
      setConfirmRestore('')
      await loadEnv(envId)
      setMsg(t('build.restoredVersion', { commit, newCommit: r.new_commit }))
      loadVersions(envId)
    } catch (e) { setMsg(String(e).replace(/^Error: /, '')) }
  }

  const selectEnv = (id: string, name?: string) => {
    if (dirty && envId && envId !== id && !window.confirm(t('build.discardUnsaved'))) return
    loadEnv(id, name)
  }

  const createEnv = (nameArg?: string) => {
    const name = (nameArg ?? newName).trim()
    if (!name) return
    const all = [...envs, ...unsaved].map(e => e.id)
    let id = slugify(name)
    for (let i = 2; all.includes(id); i++) id = `${slugify(name)}-${i}`
    setUnsaved(u => [...u, { id, name }])
    setCreating(false); setNewName('')
    const d = takeDraft()
    const { id: _i, name: _n, nodes: _no, edges: _e, ...rest } = (d ?? {}) as Record<string, unknown>
    void _i; void _n; void _no; void _e
    extras.current = d ? rest : {}
    const f = d ? toFlow({ ...d, id, name }) : { nodes: [], edges: [] }
    setEnvId(id); setEnvName(name); setNodes(f.nodes); setEdges(f.edges); setDirty(true)
    setSelected(null); setActiveRun(null); setLastCommit(''); setRuns([]); setMsg(d ? t('build.proposedLoaded') : t('build.newFlowInfo')); setTab('canvas')
  }

  // ---------- live events ----------
  const refetchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const runsTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => subscribeEvents((ev: RunEvent) => {
    if (ev.run_id === activeRunIdRef.current) {
      const timingKey = `${ev.run_id}:${ev.node_id}`
      if (ev.state === 'running') httpStarts.current[timingKey] = Date.now()
      else if (['done', 'failed', 'skipped'].includes(ev.state) && httpStarts.current[timingKey]) {
        const elapsed = Math.max(0, Date.now() - httpStarts.current[timingKey])
        setHttpTimings(t => ({ ...t, [timingKey]: elapsed }))
        try { sessionStorage.setItem(`glacier-http-time:${timingKey}`, String(elapsed)) } catch { /* timing remains available in this editor */ }
        delete httpStarts.current[timingKey]
      }
      setActiveRun(r => {
        if (!r || r.run_id !== ev.run_id) return r
        return {
          ...r,
          node_states: { ...r.node_states, [ev.node_id]: ev.state },
          outputs: ev.output !== undefined ? { ...r.outputs, [ev.node_id]: ev.output } : r.outputs,
          waiting_on: ev.state === 'waiting' ? ev.node_id : r.waiting_on === ev.node_id ? null : r.waiting_on,
          status: ev.state === 'waiting' ? 'waiting' : r.status === 'waiting' && r.waiting_on === ev.node_id ? 'running' : r.status,
        }
      })
      // the event has no run status; re-read the authoritative run state shortly after
      clearTimeout(refetchTimer.current)
      const rid = ev.run_id
      refetchTimer.current = setTimeout(() => {
        api.getRun(rid).then(r => setActiveRun(cur => (cur?.run_id === rid ? r : cur))).catch(() => {})
      }, 150)
    }
    if (ev.env_id === envIdRef.current) {
      clearTimeout(runsTimer.current)
      const eid = ev.env_id
      runsTimer.current = setTimeout(() => refreshRuns(eid), 200)
    }
  }, setWsUp), [refreshRuns])

  // ---------- canvas editing ----------
  const onNodesChange = useCallback((changes: NodeChange<GNode>[]) => {
    setNodes(ns => applyNodeChanges(changes, ns))
    if (changes.some(c => c.type === 'remove' || c.type === 'add' || (c.type === 'position' && !c.dragging && c.position))) setDirty(true)
    if (changes.some(c => c.type === 'remove' && selected?.kind === 'node' && c.id === selected.id)) setSelected(null)
  }, [selected])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges(es => applyEdgeChanges(changes, es))
    if (changes.some(c => c.type === 'remove' || c.type === 'add')) setDirty(true)
    if (changes.some(c => c.type === 'remove' && selected?.kind === 'edge' && c.id === selected.id)) setSelected(null)
  }, [selected])

  const onConnect = useCallback((c: Connection) => {
    setEdges(es => {
      const src = nodes.find(n => n.id === c.source)
      let label = ''
      const labels = branchLabels(src)
      if (labels?.length) label = labels.find(l => !es.some(e => e.source === c.source && e.label === l)) ?? labels[0]
      const id = nextId('e', es.map(e => e.id))
      return addEdge({ ...c, id, ...edgeStyle(label) }, es)
    })
    setDirty(true)
  }, [nodes, branchLabels])

  const addNode = (kind: NodeKind) => {
    const id = nextId('n', nodes.map(n => n.id))
    const config = Object.fromEntries((typeInfo(kind)?.fields ?? []).map(f => [f.key, f.default]))
    const selectedNode = nodes.find(n => n.id === selected?.id)
    const selectedIncoming = selectedNode && edges.find(e => e.target === selectedNode.id)
    const incomingParent = selectedIncoming && nodes.find(n => n.id === selectedIncoming.source)
    const parent = selectedNode && incomingParent && branchLabels(incomingParent)?.length
      ? incomingParent : selectedNode
    const x = parent ? parent.position.x + 260 : (nodes.length ? Math.max(...nodes.map(n => n.position.x)) + 260 : 60)
    const y = parent && parent.id !== selectedNode?.id ? parent.position.y + (edges.filter(e => e.source === parent.id).length * 140)
      : parent ? parent.position.y : 60
    const node: GNode = { id, type: kind, position: { x: Math.round(x / 20) * 20, y: Math.round(y / 20) * 20 }, data: { config }, selected: true }
    setNodes(ns => [...ns.map(n => ({ ...n, selected: false })), node])
    setEdges(es => {
      if (!parent) return es.map(e => ({ ...e, selected: false }))
      const labels = branchLabels(parent)
      const label = labels?.find(value => !es.some(e => e.source === parent.id && e.label === value)) ?? ''
      return [...es.map(e => ({ ...e, selected: false })), { id: nextId('e', es.map(e => e.id)), source: parent.id, target: id, ...edgeStyle(label) }]
    })
    setSelected({ kind: 'node', id })
    setDirty(true)
  }

  const setConfig = (id: string, key: string, value: string) => {
    setNodes(ns => ns.map(n => (n.id === id ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: value } } } : n)))
    setDirty(true)
  }

  const setEdgeLabel = (id: string, label: string) => {
    setEdges(es => es.map(e => (e.id === id ? { ...e, ...edgeStyle(label) } : e)))
    setDirty(true)
  }

  const deleteSelected = () => {
    if (!selected) return
    setUndoStack(stack => [...stack.slice(-19), { nodes, edges }])
    if (selected.kind === 'node') {
      setNodes(ns => ns.filter(n => n.id !== selected.id))
      setEdges(es => es.filter(e => e.source !== selected.id && e.target !== selected.id))
    } else setEdges(es => es.filter(e => e.id !== selected.id))
    setSelected(null); setDirty(true)
  }

  const undo = useCallback(() => {
    const previous = undoStack.at(-1)
    if (!previous) return
    setNodes(previous.nodes); setEdges(previous.edges); setSelected(null); setDirty(true)
    setUndoStack(stack => stack.slice(0, -1))
  }, [undoStack])

  const autoLayout = useCallback(() => {
    const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
    graph.setGraph({ rankdir: 'LR', nodesep: 48, ranksep: 88, marginx: 40, marginy: 40 })
    nodes.forEach(node => graph.setNode(node.id, { width: 210, height: 90 }))
    edges.forEach(edge => graph.setEdge(edge.source, edge.target))
    dagre.layout(graph)
    setNodes(current => current.map(node => {
      const p = graph.node(node.id)
      return { ...node, position: { x: Math.round((p.x - 105) / 20) * 20, y: Math.round((p.y - 45) / 20) * 20 } }
    }))
    setDirty(true)
    requestAnimationFrame(() => { void reactFlow.fitView({ padding: 0.18 }) })
  }, [nodes, edges, reactFlow])

  const nudgeOverlaps = useCallback((draggedId: string, position: { x: number; y: number }) => {
    setNodes(current => current.map(node => {
      if (node.id === draggedId) return node
      const dx = node.position.x - position.x, dy = node.position.y - position.y
      if (Math.abs(dx) >= 220 || Math.abs(dy) >= 110) return node
      const direction = dx === 0 ? 1 : Math.sign(dx)
      return { ...node, position: { x: Math.round((position.x + direction * 240) / 20) * 20, y: Math.round(node.position.y / 20) * 20 } }
    }))
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target?.matches('input,textarea,select,[contenteditable="true"]')) return
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); undo(); return }
      if ((event.key === 'Delete' || event.key === 'Backspace') && selected) { event.preventDefault(); deleteSelected() }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selected, undo, nodes, edges])

  // ---------- save / run / approve ----------
  const save = async (): Promise<boolean> => {
    if (!envId) return false
    setBusy(true)
    try {
      const r = await api.saveEnv({ ...extras.current, ...fromFlow(envId, envName || envId, nodes, edges) })
      setLastCommit(r.commit); setDirty(false); setMsg(t('build.saved'))
      setUnsaved(u => u.filter(e => e.id !== envId))
      refreshEnvs()
      return true
    } catch (e) { setMsg(String(e)); return false } finally { setBusy(false) }
  }

  const run = async () => {
    if (!envId) return
    if (dirty && !(await save())) return
    setBusy(true)
    try {
      const { run_id } = await api.runEnv(envId)
      const pending: RunState = {
        run_id, env_id: envId, status: 'running', outputs: {}, waiting_on: null,
        node_states: Object.fromEntries(nodes.map(n => [n.id, 'pending' as const])),
      }
      setActiveRun(pending)
      activeRunIdRef.current = run_id
      setMsg(t('build.lastRunStarted', { id: run_id }))
      api.getRun(run_id).then(r => setActiveRun(cur => (cur?.run_id === run_id ? r : cur))).catch(() => {})
      refreshRuns(envId)
    } catch (e) { setMsg(String(e)) } finally { setBusy(false) }
  }

  const openRun = (runId: string) => {
    api.getRun(runId).then(r => { setActiveRun(r); setTab('canvas') }).catch(e => setMsg(String(e)))
  }

  // Open the flow / run / new flow named in the address (#/automations/build/<env>/<run>, #/automations/new/<name>).
  const booted = useRef('')
  useEffect(() => {
    const key = `${initialEnv}|${initialRun}|${newNameProp}`
    if (booted.current === key) return
    booted.current = key
    if (newNameProp) createEnv(newNameProp)
    else if (initialEnv && initialEnv !== envIdRef.current) loadEnv(initialEnv).then(() => { if (initialRun) openRun(initialRun) })
    else if (initialRun) openRun(initialRun)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialEnv, initialRun, newNameProp])
  useEffect(() => { onStatus?.(msg ? msg.slice(0, 90) : t('build.ready')) }, [msg, onStatus])

  const decide = async (approved: boolean) => {
    if (!activeRun?.waiting_on) return
    const { run_id, waiting_on } = activeRun
    try {
      await api.approve(run_id, waiting_on, approved)
      setActiveRun(r => (r && r.run_id === run_id ? { ...r, waiting_on: null, status: 'running' } : r))
      setTimeout(() => api.getRun(run_id).then(r => setActiveRun(cur => (cur?.run_id === run_id ? r : cur))).catch(() => {}), 300)
    } catch (e) { setMsg(String(e)) }
  }

  // ---------- derived ----------
  const displayNodes = useMemo(() => nodes.map(n => ({
    ...n, data: { ...n.data, state: activeRun ? (activeRun.node_states[n.id] ?? 'pending') : undefined },
  })), [nodes, activeRun])

  // edges that close a cycle (target can reach source) are loop-back edges: drawn animated
  const displayEdges = useMemo(() => {
    const out = new Map<string, string[]>()
    for (const e of edges) out.set(e.source, [...(out.get(e.source) ?? []), e.target])
    const reaches = (from: string, to: string) => {
      const seen = new Set<string>(), stack = [from]
      while (stack.length) {
        const n = stack.pop()!
        if (n === to) return true
        if (seen.has(n)) continue
        seen.add(n); stack.push(...(out.get(n) ?? []))
      }
      return false
    }
    return edges.map(e => {
      const back = reaches(e.target, e.source)
      const cls = [typeof e.label === 'string' && e.label ? `edge-${e.label}` : '', back ? 'edge-loopback' : ''].filter(Boolean).join(' ')
      return { ...e, animated: back, className: cls || undefined }
    })
  }, [edges])

  const openSubRun = async (output: string) => {
    const m = output.match(/sub-run ([\w-]+) of ([\w-]+)/)
    if (!m) return
    if (dirty && !window.confirm(t('build.discardUnsaved'))) return
    await loadEnv(m[2])
    openRun(m[1])
  }

  const selNode = selected?.kind === 'node' ? nodes.find(n => n.id === selected.id) : undefined
  const selEdge = selected?.kind === 'edge' ? edges.find(e => e.id === selected.id) : undefined
  const selEdgeSrc = selEdge ? nodes.find(n => n.id === selEdge.source) : undefined
  const waitingNode = activeRun?.waiting_on ? nodes.find(n => n.id === activeRun.waiting_on) : undefined
  const allEnvs = [...envs, ...unsaved.filter(u => !envs.some(e => e.id === u.id))]

  return (
    <div className="app">
      {/* ---------- left ---------- */}
      <aside className="left">
        <div className="build-head"><a className="ghost-link" href="#/automations">{t('build.allFlows')}</a><span className="live-label">{wsUp ? t('build.live') : t('build.offline')}</span><span className={`ws-dot ${wsUp ? 'up' : ''}`} data-testid="ws-status" data-connected={wsUp} title={wsUp ? t('build.liveConnected') : t('build.liveDisconnected')} /></div>
        <div className="section-head"><span>{t('build.flows')}</span></div>
        <div className="list" data-testid="env-list">
          {allEnvs.map(e => (
            <button key={e.id} className={`list-item${e.id === envId ? ' active' : ''}`} data-testid={`env-${e.id}`} onClick={() => selectEnv(e.id, e.name)}>
              {e.name}{unsaved.some(u => u.id === e.id) && <span className="tag">{t('build.unsaved')}</span>}
            </button>
          ))}
          {allEnvs.length === 0 && <div className="muted">{t('build.noFlows')}</div>}
        </div>
        {creating ? (
          <form className="new-env" onSubmit={ev => { ev.preventDefault(); createEnv() }}>
            <input autoFocus data-testid="new-env-name" placeholder={t('build.flowName')} value={newName} onChange={e => setNewName(e.target.value)} />
            <div className="row">
              <button type="submit" className="primary" data-testid="new-env-create">{t('build.create')}</button>
              <button type="button" className="ghost" data-testid="new-env-cancel" onClick={() => setCreating(false)}>{t('build.cancel')}</button>
            </div>
          </form>
        ) : (
          <button className="primary block" data-testid="new-env" onClick={() => setCreating(true)}>{t('build.newFlow')}</button>
        )}

        {envId && (
          <>
            <div className="section-head">
              <span>{t('build.runs')}</span>
              <button className={`ghost${getLanguage() === 'es' ? ' es-run-refresh' : ''}`} data-testid="runs-refresh" onClick={() => refreshRuns(envId)}>{t('build.refresh')}</button>
            </div>
            <div className="list" data-testid="run-list">
              {runs.length === 0 && <div className="muted">{t('build.noRuns')}</div>}
              {runs.map(r => (
                <button key={r.run_id} className={`list-item run-item${activeRun?.run_id === r.run_id ? ' active' : ''}`} data-testid={`run-${r.run_id}`} data-status={r.status} onClick={() => openRun(r.run_id)}>
                  <span className={`badge status-${r.status}`}>{r.status}</span>
                  <span className="run-id">{r.run_id}</span>
                  <span className="run-time">{r.started_at ? new Date(r.started_at).toLocaleTimeString() : ''}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </aside>

      {/* ---------- center ---------- */}
      <main className="center">
        <div className="tabs">
          <button className={`tab${tab === 'canvas' ? ' active' : ''}`} data-testid="tab-canvas" onClick={() => setTab('canvas')}>{t('build.canvas')}</button>
          <button className={`tab${tab === 'vault' ? ' active' : ''}`} data-testid="tab-vault" onClick={() => setTab('vault')}>{t('build.notes')}</button>
          {tab === 'canvas' && envId && (
            <div className="canvas-tools">
              <button className="ghost" onClick={autoLayout} data-testid="auto-layout">{t('build.autoLayout')}</button>
              <button className="ghost" onClick={undo} disabled={!undoStack.length} data-testid="undo">{t('build.undo')}</button>
            </div>
          )}
          {tab === 'canvas' && envId && (
            <div className="palette" data-testid="palette">
              {catalog.filter(item => layout !== 'simple' || SIMPLE_STEP_TYPES.has(item.type)).map(item => (
                <button key={item.type} className={`pal pal-${item.type}`} data-testid={`palette-${item.type}`} title={item.type === 'http_request' ? t('http.description') : item.description} onClick={() => addNode(item.type)}>+ {item.type === 'http_request' ? t('http.title') : item.label}</button>
              ))}
            </div>
          )}
        </div>

        {tab === 'vault' ? <VaultView /> : !envId ? (
          <div className="empty">{t('build.pickFlow')}</div>
        ) : (
          <div className="canvas-wrap">
            {activeRun && waitingNode && activeRun.status === 'waiting' && (
              <div className="approval-banner" data-testid="approval-banner">
                <span className="approval-label">{t('build.waitingApproval', { id: waitingNode.id })}</span>
                <span className="approval-prompt" data-testid="approval-prompt">{waitingNode.data.config.prompt}</span>
                <button className="ok" data-testid="approve" onClick={() => decide(true)}>{t('build.approve')}</button>
                <button className="danger" data-testid="reject" onClick={() => decide(false)}>{t('build.reject')}</button>
              </div>
            )}
            <div className="canvas" data-testid="canvas">
              <ReactFlow<GNode, Edge>
                key={envId}
                nodes={displayNodes}
                edges={displayEdges}
                nodeTypes={flowNodeTypes}
                edgeTypes={flowEdgeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={(_, n) => setSelected({ kind: 'node', id: n.id })}
                onEdgeClick={(_, e) => setSelected({ kind: 'edge', id: e.id })}
                onPaneClick={() => setSelected(null)}
                deleteKeyCode={['Backspace', 'Delete']}
                snapToGrid
                snapGrid={[20, 20]}
                onNodeDragStop={(_, node) => { nudgeOverlaps(node.id, node.position); setDirty(true) }}
                fitView
                fitViewOptions={{ padding: 0.18 }}
                colorMode="dark"
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={16} size={1} color={tok('--g-ice4')} />
                <Controls showInteractive={false} />
                <MiniMap nodeColor={tok('--g-accent-dim')} maskColor={tok('--g-bg')} />
              </ReactFlow>
            </div>
            {activeRun && selNode && (
              <div className="term-panel" data-testid="terminal-panel">
                <div className="term-head">
                  <span>{t('build.outputStatus', { id: selNode.id, type: selNode.type, status: activeRun.node_states[selNode.id] ?? 'pending' })}</span>
                  <button className="ghost" data-testid="terminal-close" onClick={() => setSelected(null)}>{t('build.close')}</button>
                </div>
                {selNode.type === 'http_request' && <HttpResult text={activeRun.outputs[selNode.id] ?? ''} elapsed={httpTimings[`${activeRun.run_id}:${selNode.id}`]} />}
                <TerminalPanel text={activeRun.outputs[selNode.id] ?? ''} />
              </div>
            )}
          </div>
        )}
      </main>

      {/* ---------- right ---------- */}
      <aside className="right">
        {envId ? (
          <>
            <div className="section-head"><span>{t('build.flow')}</span>{dirty && <span className="tag" data-testid="dirty">{t('build.unsaved')}</span>}</div>
            <label className="field">
              <span>{t('build.name')}</span>
              <input data-testid="env-name" value={envName} onChange={e => { setEnvName(e.target.value); setDirty(true) }} />
            </label>
            {layout !== 'simple' && <div className="field"><span>{t('build.id')}</span><code data-testid="env-id">{envId}</code></div>}
            <div className="row">
              <button className="primary" data-testid="save" disabled={busy || flowRemoved} onClick={() => save()}>{t('build.save')}</button>
              <button className="run" data-testid="run" disabled={busy || flowRemoved || nodes.length === 0} onClick={run}>{t('build.run')}</button>
            </div>
            {!flowRemoved && <DeleteAction label={t('automations.deleteFlow')} impact={t('delete.flowImpact')} testid="builder-delete-flow"
              onDelete={async () => {
                const result = await api.deleteEnv(envId)
                setFlowRemoved(true)
                return { title: t('delete.removed'), run: async () => { await api.undoDeleteEnv(envId, result.commit); setFlowRemoved(false); await loadEnv(envId); refreshEnvs() } }
              }}
              onDeleted={action => setDeleteUndo(action ?? null)} onError={e => setMsg(String(e))} />}
            {flowRemoved && <DeleteUndo action={deleteUndo} onDone={() => setDeleteUndo(null)} onError={e => setMsg(String(e))} />}
            <div className="field" style={layout === 'simple' ? { display: 'none' } : undefined}>
              <span>{t('build.lastSaveCommit')}</span>
              <code data-testid="last-commit">{lastCommit || '-'}</code>
            </div>
            {versions.length > 1 && (
              <div data-testid="versions">
                <div className="section-head"><span>{t('build.savedVersions')}</span></div>
                <div className="list">
                  {versions.map((v, i) => (
                    <div key={v.commit} className="list-item" data-testid={`version-${i}`} style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
                      <span>{i === 0 ? t('build.current') : ago(v.date) || v.date.slice(0, 16)} <span className="muted small">· {v.author} · {v.commit}</span></span>
                      {i > 0 && (confirmRestore === v.commit
                        ? <span className="row"><button className="primary" data-testid={`version-restore-yes-${i}`} onClick={() => restoreVersion(v.commit)}>{t('build.restoreIt')}</button><button className="ghost" onClick={() => setConfirmRestore('')}>{t('build.cancel')}</button></span>
                        : <button className="ghost" data-testid={`version-restore-${i}`} disabled={dirty} title={dirty ? t('build.saveOrDiscard') : t('build.restoreTitle')} onClick={() => setConfirmRestore(v.commit)}>{t('build.restore')}</button>)}
                    </div>
                  ))}
                </div>
                <div className="muted small">{t('build.restoreDescription')}</div>
              </div>
            )}
            {msg && <div className="msg" data-testid="message">{msg}</div>}

            {activeRun && (
              <div className="run-box" data-testid="run-box">
                <div className="section-head">
                  <span>{t('build.run')}</span>
                  <button className="ghost" data-testid="clear-run" onClick={() => setActiveRun(null)}>{t('build.backToEdit')}</button>
                </div>
                <div className="field"><span>{t('build.id')}</span><code data-testid="active-run-id">{activeRun.run_id}</code></div>
                <div className="field"><span>{t('build.status')}</span><span className={`badge status-${activeRun.status}`} data-testid="run-status">{activeRun.status}</span></div>
                <div className="muted small">{t('build.clickNode')}</div>
                {selNode?.type === 'flow' && /sub-run [\w-]+ of /.test(activeRun.outputs[selNode.id] ?? '') && (
                  <button className="ghost" data-testid="open-subrun" onClick={() => openSubRun(activeRun.outputs[selNode.id])}>{t('build.openSubrun')}</button>
                )}
              </div>
            )}

            {selNode && (
              <div className="inspector" data-testid="inspector">
                <div className="section-head"><span>{layout === 'simple' ? (typeInfo(selNode.type)?.label ?? selNode.type) : t('build.node', { id: selNode.id, type: selNode.type })}</span>
                  {layout === 'simple' && <button className="ghost" data-testid="more-fields" onClick={() => setMoreFields(m => !m)}>{moreFields ? t('build.fewerSettings') : t('build.moreSettings')}</button>}</div>
                {(typeInfo(selNode.type)?.fields ?? []).filter(f => layout !== 'simple' || moreFields || !f.optional || (selNode.data.config[f.key] ?? '') !== '').map(f => (
                  <label className="field" key={f.key}>
                    <span>{selNode.type === 'http_request' && HTTP_LABELS[f.key] ? t(HTTP_LABELS[f.key]) : f.label}{f.optional ? t('build.optional') : ''}</span>
                    {f.picker === 'environment'
                      ? <select data-testid={`field-${f.key}`} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)}>
                          <option value="">{t('build.choose')}</option>
                          {allEnvs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                        </select>
                      : f.options
                      ? <select data-testid={`field-${f.key}`} value={selNode.data.config[f.key] || f.default} onChange={e => setConfig(selNode.id, f.key, e.target.value)}>
                          {f.options.map(o => <option key={o} value={o}>{selNode.type === 'http_request' ? httpOptionLabel(f.key, o) : o}</option>)}
                        </select>
                      : f.multiline
                      ? <textarea rows={f.key === 'prompt' ? 6 : f.key === 'body' ? 5 : 3} data-testid={`field-${f.key}`} placeholder={selNode.type === 'http_request' && HTTP_PLACEHOLDERS[f.key] ? t(HTTP_PLACEHOLDERS[f.key]) : f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />
                      : <input data-testid={`field-${f.key}`} placeholder={selNode.type === 'http_request' && HTTP_PLACEHOLDERS[f.key] ? t(HTTP_PLACEHOLDERS[f.key]) : f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />}
                    {selNode.type === 'http_request' && f.key === 'allowed_sites' && <div className="muted small">{t('http.allowedSitesHelp')}</div>}
                    {selNode.type === 'http_request' && f.key === 'url' && httpAddressError(selNode.data.config.url ?? '', selNode.data.config.allowed_sites ?? '') &&
                      <div className="http-validation" data-testid="http-url-error">{httpAddressError(selNode.data.config.url ?? '', selNode.data.config.allowed_sites ?? '')}</div>}
                    {selNode.type === 'http_request' && f.key === 'headers' && <div className="http-secret-row">
                      <span className="muted small">{t('http.secretPickerHelp')}</span>
                      <select data-testid="http-secret-picker" value="" aria-label={t('http.secretPicker')} onChange={e => {
                        const name = e.target.value
                        if (!name) return
                        const before = selNode.data.config.headers ?? ''
                        const addition = `Authorization: Bearer {secret:${name}}`
                        setConfig(selNode.id, 'headers', before ? `${before.replace(/\s+$/, '')}\n${addition}` : addition)
                      }}>
                        <option value="">{t('http.secretPicker')}</option>
                        {secretNames.map(name => <option key={name} value={name}>{name}</option>)}
                      </select>
                    </div>}
                  </label>
                ))}
                {layout === 'full' && <pre className="muted small" data-testid="node-raw" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify({ id: selNode.id, type: selNode.type, config: selNode.data.config }, null, 2)}</pre>}
                <button className="danger" data-testid="delete-selected" onClick={deleteSelected}>{t('build.deleteNode')}</button>
              </div>
            )}

            {selEdge && (
              <div className="inspector" data-testid="edge-inspector">
                <div className="section-head"><span>{t('build.edge', { id: selEdge.id, source: selEdge.source, target: selEdge.target })} {selEdge.source} → {selEdge.target}</span></div>
                {branchLabels(selEdgeSrc)?.length ? (
                  <label className="field">
                    <span>{t('build.branch')}</span>
                    <select data-testid="edge-label" value={typeof selEdge.label === 'string' ? selEdge.label : ''} onChange={e => setEdgeLabel(selEdge.id, e.target.value)}>
                      {(branchLabels(selEdgeSrc) ?? []).map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </label>
                ) : <div className="muted small">{t('build.unlabelled')}</div>}
                <button className="danger" data-testid="delete-selected" onClick={deleteSelected}>{t('build.deleteEdge')}</button>
              </div>
            )}
          </>
        ) : <div className="muted">{t('build.noSelection')}</div>}
      </aside>
    </div>
  )
}
