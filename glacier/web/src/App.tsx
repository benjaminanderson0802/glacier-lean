import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background, Controls, MarkerType, ReactFlow, ReactFlowProvider, addEdge, applyEdgeChanges, applyNodeChanges,
  type Connection, type Edge, type EdgeChange, type NodeChange,
} from '@xyflow/react'
import {
  ApiError, BRANCHING, CONFIG_FIELDS, NODE_KINDS, api, slugify, subscribeEvents,
  type EnvSummary, type Environment, type NodeKind, type RunEvent, type RunState, type RunSummary,
} from './api.ts'
import { nodeTypes, type GNode } from './GlacierNode.tsx'
import { TerminalPanel } from './TerminalPanel.tsx'
import { VaultView } from './VaultView.tsx'

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
  label: label || undefined,
  markerEnd: { type: MarkerType.ArrowClosed, color: '#7fa6b8' },
  className: label ? `edge-${label}` : undefined,
})

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

export default function App() {
  return <ReactFlowProvider><Shell /></ReactFlowProvider>
}

function Shell() {
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
  const [tab, setTab] = useState<'canvas' | 'vault'>('canvas')
  const [wsUp, setWsUp] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)

  const envIdRef = useRef(envId)
  envIdRef.current = envId
  const activeRunIdRef = useRef<string | null>(null)
  activeRunIdRef.current = activeRun?.run_id ?? null

  // ---------- loading ----------
  const refreshEnvs = useCallback(() => api.listEnvs().then(setEnvs).catch(e => setMsg(String(e))), [])
  useEffect(() => { refreshEnvs() }, [refreshEnvs])

  const refreshRuns = useCallback((id: string) => {
    api.listRuns(id).then(r => { if (envIdRef.current === id) setRuns(r) }).catch(e => setMsg(String(e)))
  }, [])

  const loadEnv = useCallback(async (id: string, fallbackName?: string) => {
    setEnvId(id); setSelected(null); setActiveRun(null); setLastCommit(''); setMsg(''); setRuns([]); setTab('canvas')
    try {
      const env = await api.getEnv(id)
      const f = toFlow(env)
      setEnvName(env.name); setNodes(f.nodes); setEdges(f.edges); setDirty(false)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setEnvName(fallbackName ?? id); setNodes([]); setEdges([]); setDirty(true)
      } else setMsg(String(e))
    }
    refreshRuns(id)
  }, [refreshRuns])

  const selectEnv = (id: string, name?: string) => {
    if (dirty && envId && envId !== id && !window.confirm('Discard unsaved changes?')) return
    loadEnv(id, name)
  }

  const createEnv = () => {
    const name = newName.trim()
    if (!name) return
    const all = [...envs, ...unsaved].map(e => e.id)
    let id = slugify(name)
    for (let i = 2; all.includes(id); i++) id = `${slugify(name)}-${i}`
    setUnsaved(u => [...u, { id, name }])
    setCreating(false); setNewName('')
    setEnvId(id); setEnvName(name); setNodes([]); setEdges([]); setDirty(true)
    setSelected(null); setActiveRun(null); setLastCommit(''); setRuns([]); setMsg('New environment - add nodes, then Save.'); setTab('canvas')
  }

  // ---------- live events ----------
  const refetchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const runsTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => subscribeEvents((ev: RunEvent) => {
    if (ev.run_id === activeRunIdRef.current) {
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
      if (src && BRANCHING.includes(src.type as NodeKind)) {
        label = es.some(e => e.source === c.source && e.label === 'yes') ? 'no' : 'yes'
      }
      const id = nextId('e', es.map(e => e.id))
      return addEdge({ ...c, id, ...edgeStyle(label) }, es)
    })
    setDirty(true)
  }, [nodes])

  const addNode = (kind: NodeKind) => {
    const id = nextId('n', nodes.map(n => n.id))
    const i = nodes.length
    const config = Object.fromEntries(CONFIG_FIELDS[kind].map(f => [f.key, f.def]))
    const node: GNode = { id, type: kind, position: { x: 60 + (i % 3) * 240, y: 60 + Math.floor(i / 3) * 160 }, data: { config }, selected: true }
    setNodes(ns => [...ns.map(n => ({ ...n, selected: false })), node])
    setEdges(es => es.map(e => ({ ...e, selected: false })))
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
    if (selected.kind === 'node') {
      setNodes(ns => ns.filter(n => n.id !== selected.id))
      setEdges(es => es.filter(e => e.source !== selected.id && e.target !== selected.id))
    } else setEdges(es => es.filter(e => e.id !== selected.id))
    setSelected(null); setDirty(true)
  }

  // ---------- save / run / approve ----------
  const save = async (): Promise<boolean> => {
    if (!envId) return false
    setBusy(true)
    try {
      const r = await api.saveEnv(fromFlow(envId, envName || envId, nodes, edges))
      setLastCommit(r.commit); setDirty(false); setMsg('Saved.')
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
      setMsg(`Run ${run_id} started.`)
      api.getRun(run_id).then(r => setActiveRun(cur => (cur?.run_id === run_id ? r : cur))).catch(() => {})
      refreshRuns(envId)
    } catch (e) { setMsg(String(e)) } finally { setBusy(false) }
  }

  const openRun = (runId: string) => {
    api.getRun(runId).then(r => { setActiveRun(r); setTab('canvas') }).catch(e => setMsg(String(e)))
  }

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

  const selNode = selected?.kind === 'node' ? nodes.find(n => n.id === selected.id) : undefined
  const selEdge = selected?.kind === 'edge' ? edges.find(e => e.id === selected.id) : undefined
  const selEdgeSrc = selEdge ? nodes.find(n => n.id === selEdge.source) : undefined
  const waitingNode = activeRun?.waiting_on ? nodes.find(n => n.id === activeRun.waiting_on) : undefined
  const allEnvs = [...envs, ...unsaved.filter(u => !envs.some(e => e.id === u.id))]

  return (
    <div className="app">
      {/* ---------- left ---------- */}
      <aside className="left">
        <div className="brand"><span className="brand-mark">◆</span> Glacier <span className={`ws-dot ${wsUp ? 'up' : ''}`} data-testid="ws-status" data-connected={wsUp} title={wsUp ? 'live events connected' : 'live events disconnected'} /></div>
        <div className="section-head"><span>Environments</span></div>
        <div className="list" data-testid="env-list">
          {allEnvs.map(e => (
            <button key={e.id} className={`list-item${e.id === envId ? ' active' : ''}`} data-testid={`env-${e.id}`} onClick={() => selectEnv(e.id, e.name)}>
              {e.name}{unsaved.some(u => u.id === e.id) && <span className="tag">unsaved</span>}
            </button>
          ))}
          {allEnvs.length === 0 && <div className="muted">No environments yet.</div>}
        </div>
        {creating ? (
          <form className="new-env" onSubmit={ev => { ev.preventDefault(); createEnv() }}>
            <input autoFocus data-testid="new-env-name" placeholder="Environment name" value={newName} onChange={e => setNewName(e.target.value)} />
            <div className="row">
              <button type="submit" className="primary" data-testid="new-env-create">Create</button>
              <button type="button" className="ghost" data-testid="new-env-cancel" onClick={() => setCreating(false)}>Cancel</button>
            </div>
          </form>
        ) : (
          <button className="primary block" data-testid="new-env" onClick={() => setCreating(true)}>+ New environment</button>
        )}

        {envId && (
          <>
            <div className="section-head">
              <span>Runs</span>
              <button className="ghost" data-testid="runs-refresh" onClick={() => refreshRuns(envId)}>Refresh</button>
            </div>
            <div className="list" data-testid="run-list">
              {runs.length === 0 && <div className="muted">No runs yet.</div>}
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
          <button className={`tab${tab === 'canvas' ? ' active' : ''}`} data-testid="tab-canvas" onClick={() => setTab('canvas')}>Canvas</button>
          <button className={`tab${tab === 'vault' ? ' active' : ''}`} data-testid="tab-vault" onClick={() => setTab('vault')}>Vault</button>
          {tab === 'canvas' && envId && (
            <div className="palette" data-testid="palette">
              {NODE_KINDS.map(k => (
                <button key={k} className={`pal pal-${k}`} data-testid={`palette-${k}`} onClick={() => addNode(k)}>+ {k}</button>
              ))}
            </div>
          )}
        </div>

        {tab === 'vault' ? <VaultView /> : !envId ? (
          <div className="empty">Pick an environment on the left, or create a new one.</div>
        ) : (
          <div className="canvas-wrap">
            {activeRun && waitingNode && activeRun.status === 'waiting' && (
              <div className="approval-banner" data-testid="approval-banner">
                <span className="approval-label">Waiting for approval on {waitingNode.id}:</span>
                <span className="approval-prompt" data-testid="approval-prompt">{waitingNode.data.config.prompt}</span>
                <button className="ok" data-testid="approve" onClick={() => decide(true)}>Approve</button>
                <button className="danger" data-testid="reject" onClick={() => decide(false)}>Reject</button>
              </div>
            )}
            <div className="canvas" data-testid="canvas">
              <ReactFlow<GNode, Edge>
                nodes={displayNodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={(_, n) => setSelected({ kind: 'node', id: n.id })}
                onEdgeClick={(_, e) => setSelected({ kind: 'edge', id: e.id })}
                onPaneClick={() => setSelected(null)}
                deleteKeyCode={['Backspace', 'Delete']}
                colorMode="dark"
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={20} color="#1b2733" />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
            {activeRun && selNode && (
              <div className="term-panel" data-testid="terminal-panel">
                <div className="term-head">
                  <span>Output of <b data-testid="terminal-node">{selNode.id}</b> ({selNode.type}) - {activeRun.node_states[selNode.id] ?? 'pending'}</span>
                  <button className="ghost" data-testid="terminal-close" onClick={() => setSelected(null)}>Close</button>
                </div>
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
            <div className="section-head"><span>Environment</span>{dirty && <span className="tag" data-testid="dirty">unsaved</span>}</div>
            <label className="field">
              <span>Name</span>
              <input data-testid="env-name" value={envName} onChange={e => { setEnvName(e.target.value); setDirty(true) }} />
            </label>
            <div className="field"><span>Id</span><code data-testid="env-id">{envId}</code></div>
            <div className="row">
              <button className="primary" data-testid="save" disabled={busy} onClick={() => save()}>Save</button>
              <button className="run" data-testid="run" disabled={busy || nodes.length === 0} onClick={run}>Run</button>
            </div>
            <div className="field">
              <span>Last save commit</span>
              <code data-testid="last-commit">{lastCommit || '-'}</code>
            </div>
            {msg && <div className="msg" data-testid="message">{msg}</div>}

            {activeRun && (
              <div className="run-box" data-testid="run-box">
                <div className="section-head">
                  <span>Run</span>
                  <button className="ghost" data-testid="clear-run" onClick={() => setActiveRun(null)}>Back to edit</button>
                </div>
                <div className="field"><span>Id</span><code data-testid="active-run-id">{activeRun.run_id}</code></div>
                <div className="field"><span>Status</span><span className={`badge status-${activeRun.status}`} data-testid="run-status">{activeRun.status}</span></div>
                <div className="muted small">Click a node to see its output.</div>
              </div>
            )}

            {selNode && (
              <div className="inspector" data-testid="inspector">
                <div className="section-head"><span>Node {selNode.id} · {selNode.type}</span></div>
                {CONFIG_FIELDS[selNode.type as NodeKind].map(f => (
                  <label className="field" key={f.key}>
                    <span>{f.label}{f.optional ? ' (optional)' : ''}</span>
                    {f.key === 'template'
                      ? <textarea rows={3} data-testid={`field-${f.key}`} placeholder={f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />
                      : <input data-testid={`field-${f.key}`} placeholder={f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />}
                  </label>
                ))}
                <button className="danger" data-testid="delete-selected" onClick={deleteSelected}>Delete node</button>
              </div>
            )}

            {selEdge && (
              <div className="inspector" data-testid="edge-inspector">
                <div className="section-head"><span>Edge {selEdge.id}: {selEdge.source} → {selEdge.target}</span></div>
                {selEdgeSrc && BRANCHING.includes(selEdgeSrc.type as NodeKind) ? (
                  <label className="field">
                    <span>Branch</span>
                    <select data-testid="edge-label" value={typeof selEdge.label === 'string' ? selEdge.label : ''} onChange={e => setEdgeLabel(selEdge.id, e.target.value)}>
                      <option value="yes">yes</option>
                      <option value="no">no</option>
                    </select>
                  </label>
                ) : <div className="muted small">Unlabelled edge (runs in order).</div>}
                <button className="danger" data-testid="delete-selected" onClick={deleteSelected}>Delete edge</button>
              </div>
            )}
          </>
        ) : <div className="muted">No environment selected.</div>}
      </aside>
    </div>
  )
}
