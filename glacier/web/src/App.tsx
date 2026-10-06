import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background, Controls, MarkerType, ReactFlow, ReactFlowProvider, addEdge, applyEdgeChanges, applyNodeChanges,
  type Connection, type Edge, type EdgeChange, type NodeChange,
} from '@xyflow/react'
import {
  ApiError, api, slugify, subscribeEvents,
  type EnvSummary, type NodeTypeInfo, type Environment, type NodeKind, type RunEvent, type RunState, type RunSummary,
} from './api.ts'
import { GlacierNode, type GNode } from './GlacierNode.tsx'
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
  const [conversationChooser, setConversationChooser] = useState(false)
  const [wsUp, setWsUp] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)
  const [catalog, setCatalog] = useState<NodeTypeInfo[]>([])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try { const saved = localStorage.getItem('glacier-theme'); if (saved === 'light' || saved === 'dark') return saved } catch { /* storage may be unavailable */ }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('glacier-theme', theme) } catch { /* theme still works in this session */ }
  }, [theme])
  const typeInfo = useCallback((k: string) => catalog.find(t => t.type === k), [catalog])
  const flowNodeTypes = useMemo(() => Object.fromEntries(catalog.map(t => [t.type, GlacierNode])), [catalog])

  const envIdRef = useRef(envId)
  envIdRef.current = envId
  const activeRunIdRef = useRef<string | null>(null)
  activeRunIdRef.current = activeRun?.run_id ?? null

  // ---------- loading ----------
  const refreshEnvs = useCallback(() => api.listEnvs().then(setEnvs).catch(e => setMsg(String(e))), [])
  useEffect(() => { refreshEnvs() }, [refreshEnvs])
  useEffect(() => { api.nodeTypes().then(setCatalog).catch(e => setMsg(String(e))) }, [])

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
    if (envId === id) { setTab('canvas'); return }
    if (dirty && envId && !window.confirm('Discard unsaved changes?')) return
    loadEnv(id, name)
  }

  const createEnv = () => {
    const name = newName.trim()
    if (!name) return
    if (dirty && envId && !window.confirm('Discard unsaved changes?')) return
    const all = [...envs, ...unsaved].map(e => e.id)
    let id = slugify(name)
    for (let i = 2; all.includes(id); i++) id = `${slugify(name)}-${i}`
    setUnsaved(u => [...u, { id, name }])
    setCreating(false); setNewName('')
    setEnvId(id); setEnvName(name); setNodes([]); setEdges([]); setDirty(true)
    setSelected(null); setActiveRun(null); setLastCommit(''); setRuns([]); setMsg('Your flow is ready. Add a step to begin.'); setTab('canvas')
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
      const pair = src ? typeInfo(src.type)?.branches ?? undefined : undefined
      if (pair) label = es.some(e => e.source === c.source && e.label === pair[0]) ? pair[1] : pair[0]
      const id = nextId('e', es.map(e => e.id))
      return addEdge({ ...c, id, ...edgeStyle(label) }, es)
    })
    setDirty(true)
  }, [nodes, typeInfo])

  const addNode = (kind: NodeKind) => {
    const id = nextId('n', nodes.map(n => n.id))
    const i = nodes.length
    const config = Object.fromEntries((typeInfo(kind)?.fields ?? []).map(f => [f.key, f.default]))
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
      const updated = await api.getRun(run_id)
      setActiveRun(r => r?.run_id === run_id ? updated : r)
      setTimeout(() => api.getRun(run_id).then(r => setActiveRun(cur => (cur?.run_id === run_id ? r : cur))).catch(() => {}), 300)
    } catch (e) { setMsg(String(e)) }
  }

  // ---------- derived ----------
  const displayNodes = useMemo(() => nodes.map(n => ({
    ...n, data: { ...n.data, label: typeInfo(n.type)?.label ?? n.type, description: typeInfo(n.type)?.description,
      summary: (typeInfo(n.type)?.fields ?? []).map(f => n.data.config[f.key]).find(Boolean),
      state: activeRun ? (activeRun.node_states[n.id] ?? 'pending') : undefined },
  })), [nodes, activeRun, typeInfo])

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
    if (dirty && !window.confirm('Discard unsaved changes?')) return
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
      <header className="topbar"><div className="top-cell brand-cell"><span className="pixel-mark">▣</span> GLACIER</div><div className="top-cell top-title">YOUR WORKSPACE <span>Make a plan, then decide when it’s ready.</span></div><div className="top-cell top-theme"><button className="theme-toggle" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>{theme === 'light' ? '☾ Dark' : '☼ Light'}</button></div></header>
      <aside className="left">
        <div className="brand"><span className="brand-mark" aria-hidden="true">▣</span> Glacier<span className="brand-caption">YOUR LITTLE WORK WORLD</span></div>
        <div className="workspace-label"><span className="workspace-avatar">G</span><div>Your place<small>Everything you are working on</small></div></div>
        <div className="section-head"><span>Your flows</span><span>{allEnvs.length}</span></div>
        <div className="list flow-list" data-testid="env-list">
          {allEnvs.map(e => <button key={e.id} className={`list-item${e.id === envId ? ' active' : ''}`} data-testid={`env-${e.id}`} onClick={() => selectEnv(e.id, e.name)}>
            <span className="flow-symbol" aria-hidden="true">◇</span><span className="flow-title">{e.name}</span>{unsaved.some(u => u.id === e.id) && <span className="unsaved-dot" title="Not saved yet" />}
          </button>)}
          {!allEnvs.length && <p className="muted small">Your flows will live here. Start with one small task.</p>}
        </div>
        {creating ? <form className="new-env" onSubmit={ev => { ev.preventDefault(); createEnv() }}>
          <label className="field"><span>Give your flow a name</span><input autoFocus data-testid="new-env-name" placeholder="e.g. Weekly summary" value={newName} onChange={e => setNewName(e.target.value)} /></label>
          <div className="row"><button type="submit" className="primary" disabled={!newName.trim()} data-testid="new-env-create">Create flow</button><button type="button" className="ghost" data-testid="new-env-cancel" onClick={() => setCreating(false)}>Cancel</button></div>
        </form> : <button className="new-flow block" data-testid="new-env" onClick={() => setCreating(true)}>＋ New flow</button>}
        {envId && <>
          <div className="section-head history-heading"><span>Run history</span><button className="ghost" data-testid="runs-refresh" onClick={() => refreshRuns(envId)}>Refresh</button></div>
          <div className="list history-list" data-testid="run-list">
            {!runs.length && <p className="muted small">Once you run this flow, its activity appears here.</p>}
            {runs.map(r => <button key={r.run_id} className={`list-item run-item${activeRun?.run_id === r.run_id ? ' active' : ''}`} data-testid={`run-${r.run_id}`} data-status={r.status} onClick={() => openRun(r.run_id)}>
              <span className={`badge status-${r.status}`}>{r.status}</span>
              <span className="run-time">{r.started_at ? new Date(r.started_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'Time unavailable'}</span>
              <span className="run-id">{r.run_id}</span>
            </button>)}
          </div>
        </>}
        <div className="sidebar-bottom">
          <div className="future-link"><span>Claims & proposals</span><span className="soon">Coming soon</span><small>Problems and paid options that need you.</small></div>
        </div>
      </aside>

      <main className="center">
        <header className="page-header"><div className="eyebrow">{tab === 'vault' ? 'MEMORY · COMING SOON' : 'BUILD A FLOW'}</div><h1>{tab === 'vault' ? 'Memory' : (envName || 'Your flow')}</h1><p>{tab === 'vault' ? 'A simple list of things Glacier has saved.' : 'Put a few clear steps together. You stay in charge.'}</p><span className="header-emblem" aria-hidden="true">▦</span></header>
        <nav className="tabs" aria-label="Workspace views">
          <button className={`tab${tab === 'canvas' ? ' active' : ''}`} data-testid="tab-canvas" aria-pressed={tab === 'canvas'} onClick={() => setTab('canvas')}>◇ Build</button>
          <button className="tab future-tab" disabled>Run <span className="soon">Coming soon</span></button>
          <button className={`tab${tab === 'vault' ? ' active' : ''}`} data-testid="tab-vault" aria-pressed={tab === 'vault'} onClick={() => setTab('vault')}>▤ Memory</button>
        </nav>
        {tab === 'vault' ? <VaultView /> : !envId ? <div className="empty"><span className="empty-art" aria-hidden="true">◇<span>···</span>◇<span>···</span>◈</span><div className="eyebrow">ONE STEP AT A TIME</div><h2>Make room for what matters.</h2><p>A flow is a series of steps that work together.<br />Create one, add your steps, and follow its progress here.</p><button className="primary" onClick={() => setCreating(true)}>Create your first flow →</button></div> : <>
          <div className="flow-toolbar">
            <div className="flow-name"><label htmlFor="flow-name">FLOW NAME</label><input id="flow-name" data-testid="env-name" disabled={!!activeRun} value={envName} onChange={e => { setEnvName(e.target.value); setDirty(true) }} /></div>
            <span className={`save-state${dirty ? ' is-dirty' : ''}`}>{dirty ? <span data-testid="dirty">● Unsaved changes</span> : '✓ All changes saved'}</span>
            <button data-testid="save" disabled={busy || !!activeRun} onClick={() => save()}>Save</button><button className="primary" data-testid="run" disabled={busy || nodes.length === 0 || activeRun?.status === 'running' || activeRun?.status === 'waiting'} onClick={run}>▷ Run flow</button>
          </div>
          <div className="palette-wrap"><div className="palette-title">YOUR STEP PIECES<span>Choose one to add it</span></div><div className="palette" data-testid="palette">{catalog.map(t => { const worker = t.label.toLowerCase().includes('worker'); return <button key={t.type} className="pal" data-testid={`palette-${t.type}`} title={t.description} disabled={!!activeRun} onClick={() => addNode(t.type)}><span aria-hidden="true">＋</span> <span className="pal-label">{worker ? 'Worker' : t.label}</span>{worker && <span className="sr-only">{t.label}</span>}</button> })}</div></div>
          <div className="canvas-wrap">
            {activeRun && <div className="run-box" data-testid="run-box">
              <div className="section-head"><span>Flow progress</span><span className={`badge status-${activeRun.status}`} data-testid="run-status">{activeRun.status}</span></div>
              <details><summary>Run details</summary><code data-testid="active-run-id">{activeRun.run_id}</code></details><p className="muted small">Live status from Glacier.</p>
              <button data-testid="clear-run" onClick={() => setActiveRun(null)}>← Back to editing</button>
              {selNode?.type === 'flow' && /sub-run [\w-]+ of /.test(activeRun.outputs[selNode.id] ?? '') && <button data-testid="open-subrun" onClick={() => openSubRun(activeRun.outputs[selNode.id])}>Open sub-flow run</button>}
            </div>}
            {activeRun && waitingNode && activeRun.status === 'waiting' && <div className="approval-banner" data-testid="approval-banner" role="status"><div><span className="approval-label">Your decision is needed</span><span className="approval-prompt" data-testid="approval-prompt">{waitingNode.data.config.prompt}</span></div><button className="ok" data-testid="approve" onClick={() => decide(true)}>Approve</button><button className="danger" data-testid="reject" onClick={() => decide(false)}>Reject</button></div>}
            <div className="canvas" data-testid="canvas">
              <ReactFlow<GNode, Edge> nodes={displayNodes} edges={displayEdges} nodeTypes={flowNodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_, n) => setSelected({ kind: 'node', id: n.id })} onEdgeClick={(_, e) => setSelected({ kind: 'edge', id: e.id })} onPaneClick={() => setSelected(null)} nodesDraggable={!activeRun} nodesConnectable={!activeRun} deleteKeyCode={activeRun ? null : ['Backspace', 'Delete']} colorMode={theme} proOptions={{ hideAttribution: true }}>
                <Background gap={24} color="var(--dots)" /><Controls showInteractive={false} />
              </ReactFlow>
              {!nodes.length && <div className="canvas-guide"><span>01</span><h2>Start with a single step.</h2><p>Choose a step above, then select it to set it up.</p></div>}
              <div className="canvas-caption">{nodes.length} steps · {edges.length} connections<span>Drag a step to move it</span></div>
            </div>
            {activeRun && selNode && <div className="term-panel" data-testid="terminal-panel"><div className="term-head"><span>Step output · <b data-testid="terminal-node">{selNode.id}</b> · {typeInfo(selNode.type)?.label ?? selNode.type} · {activeRun.node_states[selNode.id] ?? 'pending'}</span><button className="ghost" data-testid="terminal-close" onClick={() => setSelected(null)}>Close</button></div><TerminalPanel text={activeRun.outputs[selNode.id] ?? ''} /></div>}
          </div>
          {tab === 'canvas' && selNode && <div className="inspector" data-testid="inspector">
            <div className="section-head"><span>{typeInfo(selNode.type)?.label ?? selNode.type} settings</span><span>{typeInfo(selNode.type)?.description}</span></div>
            {(typeInfo(selNode.type)?.fields ?? []).map(f => <label className="field" key={f.key}><span>{f.label}{f.optional ? ' (optional)' : ''}</span>
              {f.picker === 'environment' ? <select data-testid={`field-${f.key}`} disabled={!!activeRun} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)}><option value="">choose…</option>{allEnvs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select>
                : f.options ? <select data-testid={`field-${f.key}`} disabled={!!activeRun} value={selNode.data.config[f.key] || f.default} onChange={e => setConfig(selNode.id, f.key, e.target.value)}>{f.options.map(o => <option key={o} value={o}>{o}</option>)}</select>
                : f.multiline ? <textarea rows={f.key === 'prompt' ? 6 : 3} data-testid={`field-${f.key}`} disabled={!!activeRun} placeholder={f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />
                : <input data-testid={`field-${f.key}`} disabled={!!activeRun} placeholder={f.placeholder} value={selNode.data.config[f.key] ?? ''} onChange={e => setConfig(selNode.id, f.key, e.target.value)} />}</label>)}
            <button className="danger" data-testid="delete-selected" disabled={!!activeRun} onClick={deleteSelected}>Delete step</button>
          </div>}
          {tab === 'canvas' && selEdge && <div className="inspector edge-editor" data-testid="edge-inspector">
            <div className="section-head"><span>Connection · {selEdge.source} → {selEdge.target}</span></div>
            {selEdgeSrc && typeInfo(selEdgeSrc.type)?.branches ? <label className="field"><span>Branch</span><select data-testid="edge-label" disabled={!!activeRun} value={typeof selEdge.label === 'string' ? selEdge.label : ''} onChange={e => setEdgeLabel(selEdge.id, e.target.value)}>{(typeInfo(selEdgeSrc.type)?.branches ?? []).map(l => <option key={l} value={l}>{l}</option>)}</select></label> : <div className="muted small">The next step follows this connection.</div>}
            <button className="danger" data-testid="delete-selected" disabled={!!activeRun} onClick={deleteSelected}>Delete connection</button>
          </div>}
          <footer className="save-footer"><span>Saved version <code data-testid="last-commit">{lastCommit || '—'}</code></span><details><summary>Flow details</summary><code data-testid="env-id">{envId}</code></details></footer>
        </>}
      </main>
      {msg && <div className="workspace-message msg" role="status" data-testid="message">{msg}</div>}

      <aside className="right" aria-label="Messages">
        <div className="messages-head"><div><span className="eyebrow">TALK IT THROUGH</span><h2>Messages</h2></div><button className="chooser-trigger" onClick={() => setConversationChooser(!conversationChooser)} aria-expanded={conversationChooser}>☷</button></div>
        {conversationChooser ? <div className="conversation-chooser"><span className="pixel-face" aria-hidden="true">▣</span><h3>Conversations</h3><button className="conversation-row active" onClick={() => setConversationChooser(false)}><span>▣</span><span>Glacier<small>Your helpful guide</small></span><b>›</b></button><div className="future-note"><span className="soon">Coming soon</span><p>More ways to talk with Glacier are on the way.</p></div></div> : <div className="glacier-thread"><button className="conversation-current" onClick={() => setConversationChooser(true)}><span className="pixel-face" aria-hidden="true">▣</span><span>Glacier<small>Your helpful guide</small></span><b>⌄</b></button><div className="thread-empty"><span aria-hidden="true">✦</span><h3>Start with Glacier</h3><p>Tell Glacier what you want to get done. Chat is on the way.</p><span className="soon">Coming soon</span></div><label className="composer"><span>Write a message…</span><button disabled aria-label="Send message">↑</button></label><p className="plain-note">Nothing will happen until you choose to run a flow.</p></div>}
      </aside>
      <footer className="bottombar"><div className={`footer-status ${wsUp ? 'connected' : ''}`} data-testid="ws-status" data-connected={wsUp} role="status"><span className="ws-dot" />{wsUp ? 'Connected' : 'Reconnecting…'}</div><div className="footer-center">Your flows, your choice<span>Cost per run <b>Coming soon</b> · Claims & proposals <b>Coming soon</b></span></div><div className="footer-version"><span>Memory graph · Coming soon</span></div></footer>
    </div>
  )
}
