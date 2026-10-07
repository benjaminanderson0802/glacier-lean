// Simple Run view of one flow (mockup panels 7 and 8): live steps, output, verification, usage; past runs with undo.
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { ago, api, subscribeEvents, type Environment, type NodeState, type NodeTypeInfo, type RunState, type RunSummary } from '../api.ts'
import { Btn, Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { StatusIcon, type StatusKind } from '../ui/Pixel.tsx'
import { go } from '../route.ts'

const NODE_ICON: Record<NodeState, StatusKind> = { pending: 'idle', running: 'run', done: 'ok', failed: 'bad', waiting: 'warn', skipped: 'idle' }
const RUN_LABEL: Record<string, { kind: StatusKind; label: string }> = {
  done: { kind: 'ok', label: 'Success' }, failed: { kind: 'bad', label: 'Failed' }, rejected: { kind: 'bad', label: 'Rejected' },
  running: { kind: 'run', label: 'Running' }, waiting: { kind: 'warn', label: 'Needs you' },
}
const when = (iso: string) => { const d = new Date(iso); return Number.isNaN(+d) ? '' : `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` }

function useFlow(envId: string) {
  const [env, setEnv] = useState<Environment | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [types, setTypes] = useState<NodeTypeInfo[]>([])
  const [err, setErr] = useState('')
  const refreshRuns = useCallback(() => api.listRuns(envId).then(r => setRuns([...r].sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? '')))).catch(e => setErr(String(e))), [envId])
  useEffect(() => {
    api.getEnv(envId).then(setEnv).catch(e => setErr(String(e)))
    api.nodeTypes().then(setTypes).catch(() => {})
    refreshRuns()
  }, [envId, refreshRuns])
  return { env, runs, types, err, setErr, refreshRuns }
}

export function RunView({ envId, runId, history }: { envId: string; runId?: string; history?: boolean }) {
  return history ? <PastRuns envId={envId} /> : <LiveRun envId={envId} runId={runId} />
}

function LiveRun({ envId, runId }: { envId: string; runId?: string }) {
  const { env, runs, types, err, setErr, refreshRuns } = useFlow(envId)
  const current = runId ?? runs[0]?.run_id
  const [run, setRun] = useState<RunState | null>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [tab, setTab] = useState<'output' | 'details'>('output')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => { if (current) api.getRun(current).then(setRun).catch(e => setErr(String(e))) }, [current, setErr])
  useEffect(() => { setRun(null); load() }, [load])
  useEffect(() => {
    let t: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(ev => { if (ev.run_id === current) { clearTimeout(t); t = setTimeout(() => { load(); refreshRuns() }, 250) } }, () => {})
    return () => { off(); clearTimeout(t) }
  }, [current, load, refreshRuns])

  const nodes = env?.nodes ?? []
  const label = (type: string) => types.find(t => t.type === type)?.label ?? type
  const active = sel ?? (run && (run.waiting_on ?? nodes.find(n => run.node_states[n.id] === 'running')?.id)) ?? nodes[0]?.id
  const activeNode = nodes.find(n => n.id === active)
  const usage = useMemo(() => {
    const u = Object.values(run?.usage ?? {})
    return {
      model: [...new Set(u.map(x => x.model).filter(Boolean))].join(', ') || '—',
      route: [...new Set(u.map(x => x.route).filter(Boolean))].join(', ') || '—',
      tokens: u.reduce((a, x) => a + (x.tokens_in ?? 0) + (x.tokens_out ?? 0), 0),
      cost: u.reduce((a, x) => a + (x.cost_usd ?? 0), 0),
    }
  }, [run])
  const done = run ? nodes.filter(n => run.node_states[n.id] === 'done').length : 0

  const start = async () => {
    setBusy(true)
    try { const r = await api.runEnv(envId); go(`automations/flow/${envId}/${r.run_id}`); refreshRuns() } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }
  const decide = async (ok: boolean) => {
    if (!run?.waiting_on) return
    try { await api.approve(run.run_id, run.waiting_on, ok); load() } catch (e) { setErr(String(e)) }
  }
  const st = run ? RUN_LABEL[run.status] : undefined

  return (
    <>
      <PageHead title={`${run?.status === 'running' ? 'Running: ' : ''}${env?.name ?? envId}`} crumb="Automations"
        sub={run ? `${st?.label ?? run.status} · step ${done}/${nodes.length}` : 'Not run yet.'}
        side={<>
          <Btn onClick={() => go(`automations/flow/${envId}/history`)} data-testid="run-history">Past runs</Btn>
          <Btn onClick={() => go(`automations/build/${envId}`)} data-testid="open-builder">Edit flow</Btn>
          <Btn primary icon="run" onClick={start} disabled={busy || nodes.length === 0} data-testid="run-start">Run</Btn>
        </>} />
      {err && <div className="g-error">{err}</div>}
      {run?.status === 'waiting' && (
        <Panel className="g-ask" testid="run-approval">
          <div className="g-ask-row"><StatusIcon kind="warn" /><span className="g-lead">{run.waiting_prompt || 'This step is waiting for your approval.'}</span>
            <Btn primary onClick={() => decide(true)} data-testid="run-approve">Approve</Btn><Btn danger onClick={() => decide(false)} data-testid="run-reject">Reject</Btn></div>
        </Panel>
      )}
      <div className="g-runview">
        <Panel title="Steps" testid="run-steps" className="g-scroll">
          <div className="g-rows">
            {nodes.map((n, i) => {
              const s = (run?.node_states[n.id] ?? 'pending') as NodeState
              return <Row key={n.id} status={NODE_ICON[s]} lead={`${i + 1}. ${label(n.type)}`} detail={Object.values(n.config).find(Boolean)?.slice(0, 60)}
                when={s} onClick={() => setSel(n.id)} className={n.id === active ? 'sel' : ''} testid={`run-step-${n.id}`} />
            })}
            {nodes.length === 0 && <Empty>This flow has no steps yet.</Empty>}
          </div>
        </Panel>
        <Panel testid="run-output" title={
          <span className="g-seg">
            <button className={`g-seg-btn${tab === 'output' ? ' active' : ''}`} onClick={() => setTab('output')}>Output</button>
            <button className={`g-seg-btn${tab === 'details' ? ' active' : ''}`} onClick={() => setTab('details')}>Details</button>
          </span>} aside={activeNode ? `${label(activeNode.type)} · ${activeNode.id}` : undefined}>
          {tab === 'output'
            ? <pre className="g-term" data-testid="run-output-text">{(active && run?.outputs[active]) || (run ? 'No output yet.' : 'Press Run to start this flow.')}</pre>
            : <dl className="g-kv">{Object.entries(activeNode?.config ?? {}).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v || '—'}</dd></Fragment>)}</dl>}
        </Panel>
        <Panel className="g-scroll" title="Verification" aside={run?.verified === true ? 'All checks passed' : run?.verified === false ? 'Not verified' : undefined} testid="run-verification">
          <div className="g-rows">
            {(run?.verification ?? []).map(c => <Row key={c.check} status={c.passed ? 'ok' : 'bad'} lead={c.kind} detail={c.evidence?.slice(0, 120)} />)}
            {run && !(run.verification ?? []).length && <Empty>{run.verified === null ? 'This flow has no checks, so results are not verified.' : 'Checks run when the flow finishes.'}</Empty>}
          </div>
        </Panel>
        <Panel title="Usage (this run)" testid="run-usage">
          <dl className="g-kv">
            <dt>Model</dt><dd>{usage.model}</dd>
            <dt>Route</dt><dd>{usage.route}</dd>
            <dt>Tokens</dt><dd>{usage.tokens.toLocaleString()}</dd>
            <dt>Cost</dt><dd data-testid="run-cost">${usage.cost.toFixed(2)}</dd>
          </dl>
        </Panel>
      </div>
    </>
  )
}

function PastRuns({ envId }: { envId: string }) {
  const { env, runs, err, setErr, refreshRuns } = useFlow(envId)
  const [changes, setChanges] = useState<Record<string, number>>({})
  const [sel, setSel] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [note, setNote] = useState('')
  useEffect(() => {
    runs.slice(0, 15).forEach(r => api.runChanges(r.run_id).then(c => setChanges(x => ({ ...x, [r.run_id]: c.length }))).catch(() => {}))
  }, [runs])
  const chosen = runs.find(r => r.run_id === (sel ?? runs[0]?.run_id))
  const undo = async () => {
    if (!chosen) return
    try { await api.undoRun(chosen.run_id); setNote('Undone. The files this run changed are back to how they were.'); setConfirm(false); refreshRuns() } catch (e) { setErr(String(e)); setConfirm(false) }
  }
  return (
    <>
      <PageHead title={`Past runs: ${env?.name ?? envId}`} crumb="Automations" sub={`${runs.length} total runs.`}
        side={<><Btn onClick={() => go(`automations/flow/${envId}`)}>Back</Btn><Btn primary icon="run" onClick={() => api.runEnv(envId).then(r => go(`automations/flow/${envId}/${r.run_id}`)).catch(e => setErr(String(e)))} data-testid="rerun">Re-run</Btn></>} />
      {err && <div className="g-error">{err}</div>}
      <Panel testid="past-runs">
        <table className="g-table">
          <thead><tr><th>Date</th><th>Result</th><th>Changes</th></tr></thead>
          <tbody>
            {runs.map(r => {
              const s = RUN_LABEL[r.status]
              return (
                <tr key={r.run_id} className={chosen?.run_id === r.run_id ? 'sel' : ''} onClick={() => { setSel(r.run_id); setConfirm(false); setNote('') }} data-testid={`past-${r.run_id}`}>
                  <td>{when(r.started_at)}</td>
                  <td><span className="g-status-cell"><StatusIcon kind={s?.kind ?? 'idle'} />{s?.label ?? r.status}</span></td>
                  <td>{changes[r.run_id] === undefined ? '…' : changes[r.run_id] === 0 ? '0 changes' : `${changes[r.run_id]} change${changes[r.run_id] > 1 ? 's' : ''}`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {runs.length === 0 && <Empty>No runs yet.</Empty>}
      </Panel>
      {chosen && (
        <Panel title="Run details" testid="run-details">
          <div className="g-ask-row">
            <StatusIcon kind={RUN_LABEL[chosen.status]?.kind ?? 'idle'} />
            <span className="g-lead">{when(chosen.started_at)} · {RUN_LABEL[chosen.status]?.label ?? chosen.status}</span>
            <span className="g-detail">{ago(chosen.started_at)}</span>
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
              <Btn primary onClick={() => go(`automations/flow/${envId}/${chosen.run_id}`)} data-testid="run-view">View</Btn>
              {confirm
                ? <><span className="g-detail">Put back everything this run changed?</span><Btn danger onClick={undo} data-testid="run-undo-yes">Yes, undo</Btn><Btn onClick={() => setConfirm(false)}>No</Btn></>
                : <Btn onClick={() => setConfirm(true)} disabled={!changes[chosen.run_id]} data-testid="run-undo">Undo</Btn>}
            </span>
          </div>
          {note && <div className="g-saved">{note}</div>}
        </Panel>
      )}
    </>
  )
}
