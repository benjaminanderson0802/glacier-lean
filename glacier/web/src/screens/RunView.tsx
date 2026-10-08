// Simple Run view of one flow (mockup panels 7 and 8): live steps, output, verification, usage; past runs with undo.
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ago, api, subscribeEvents, type Environment, type NodeState, type NodeTypeInfo, type RunExplanation, type RunState, type RunSummary } from '../api.ts'
import { Bar, Btn, Empty, Hint, HintBar, KeyboardMenu, NamedTextBox, PageHead, Panel, Row } from '../ui/kit.tsx'
import { StatusIcon, type StatusKind } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'
import './Settings.css'

const RUN_LABEL: Record<string, { kind: StatusKind; label: string }> = {
  done: { kind: 'ok', label: t('run.success') }, failed: { kind: 'bad', label: t('run.failed') }, rejected: { kind: 'bad', label: t('run.rejected') },
  running: { kind: 'run', label: t('run.running') }, waiting: { kind: 'warn', label: t('run.needsYou') },
}
const when = (iso: string) => { const d = new Date(iso); return Number.isNaN(+d) ? '' : `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` }
const savedHttpTime = (key: string) => {
  try {
    const value = sessionStorage.getItem(`glacier-http-time:${key}`)
    return value === null ? undefined : Number(value)
  } catch { return undefined }
}

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
  const [httpElapsed, setHttpElapsed] = useState<Record<string, number>>({})
  const httpStarts = useRef<Record<string, number>>({})

  const [why, setWhy] = useState<RunExplanation | null>(null)
  const load = useCallback(() => {
    if (!current) return
    api.getRun(current).then(setRun).catch(e => setErr(String(e)))
    api.explain(current).then(setWhy).catch(() => setWhy(null))  // older engines have no explanation
  }, [current, setErr])
  useEffect(() => { setRun(null); load() }, [load])
  useEffect(() => {
    let t: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(ev => { if (ev.run_id === current) {
      const key = `${ev.run_id}:${ev.node_id}`
      if (ev.state === 'running') httpStarts.current[key] = Date.now()
      else if (['done', 'failed', 'skipped'].includes(ev.state) && httpStarts.current[key]) {
        setHttpElapsed(x => ({ ...x, [key]: Date.now() - httpStarts.current[key] }))
        delete httpStarts.current[key]
      }
      clearTimeout(t); t = setTimeout(() => { load(); refreshRuns() }, 250)
    } }, () => {})
    return () => { off(); clearTimeout(t) }
  }, [current, load, refreshRuns])

  const nodes = env?.nodes ?? []
  const label = (type: string) => types.find(t => t.type === type)?.label ?? type
  const active = sel ?? (run && (run.waiting_on ?? nodes.find(n => run.node_states[n.id] === 'running')?.id)) ?? nodes[0]?.id
  const activeNode = nodes.find(n => n.id === active)
  const usage = useMemo(() => {
    const u = Object.values(run?.usage ?? {})
    return {
      model: [...new Set(u.map(x => x.model).filter(Boolean))].join(', ') || t('run.dash'),
      route: [...new Set(u.map(x => x.route).filter(Boolean))].join(', ') || t('run.dash'),
      tokens: u.reduce((a, x) => a + (x.tokens_in ?? 0) + (x.tokens_out ?? 0), 0),
      cost: u.reduce((a, x) => a + (x.cost_usd ?? 0), 0),
    }
  }, [run])
  const done = run ? nodes.filter(n => run.node_states[n.id] === 'done').length : 0

  const start = useCallback(async () => {
    setBusy(true)
    try { const r = await api.runEnv(envId); go(`automations/flow/${envId}/${r.run_id}`); refreshRuns() } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }, [envId, refreshRuns])
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return
      if (event.key.toLowerCase() === 'r') { event.preventDefault(); void start() }
      else if (event.key.toLowerCase() === 'h') go(`automations/flow/${envId}/history`)
      else if (event.key.toLowerCase() === 'b') go(`automations/build/${envId}`)
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [envId, start])
  const decide = async (ok: boolean) => {
    if (!run?.waiting_on) return
    try { await api.approve(run.run_id, run.waiting_on, ok); load() } catch (e) { setErr(String(e)) }
  }
  const st = run ? RUN_LABEL[run.status] : undefined

  return (
    <>
      <PageHead title={`${run?.status === 'running' ? t('run.titlePrefix') : ''}${env?.name ?? envId}`} crumb={t('run.automations')}
        sub={run ? t('run.progress', { status: st?.label ?? run.status, done, total: nodes.length }) : t('run.notRun')}
        side={<>
          <Btn onClick={() => go(`automations/flow/${envId}/history`)} data-testid="run-history">{t('run.pastRuns')}</Btn>
          <Btn onClick={() => go(`automations/build/${envId}`)} data-testid="open-builder">{t('run.editFlow')}</Btn>
          <Btn primary icon="run" onClick={start} disabled={busy || nodes.length === 0} data-testid="run-start">{t('run.run')}</Btn>
          {run && <Bar value={done} max={nodes.length} tone={run.status === 'failed' ? 'bad' : run.status === 'waiting' ? 'warn' : 'ok'} />}
        </>} />
      {err && <div className="g-error">{err}</div>}
      {why && (
        <div className={`g-why${why.verified === false ? ' bad' : why.verified ? ' ok' : ''}`} data-testid="run-why">
          <StatusIcon kind={why.verified ? 'ok' : why.verified === false ? 'bad' : run?.status === 'waiting' ? 'warn' : run?.status === 'running' ? 'run' : 'idle'} />
          <span><b>{t('run.whatHappened')}</b> {why.summary}{why.needs_you ? ` ${why.needs_you}` : ''}</span>
        </div>
      )}
      {run?.status === 'waiting' && (
        <Panel className="g-ask" testid="run-approval">
          <div className="g-ask-row"><StatusIcon kind="warn" /><span className="g-lead">{run.waiting_prompt || t('run.waitingApproval')}</span>
            <Btn primary onClick={() => decide(true)} data-testid="run-approve">{t('run.approve')}</Btn><Btn danger onClick={() => decide(false)} data-testid="run-reject">{t('run.reject')}</Btn></div>
        </Panel>
      )}
      <div className="g-runview" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.2fr)', gridTemplateRows: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 'calc(2 * var(--px))', flex: 1 }}>
        <Panel title={t('run.steps')} testid="run-steps" className="g-scroll">
          {nodes.length > 0 ? <KeyboardMenu label={t('run.steps')} items={nodes.map((n, i) => {
            const s = (run?.node_states[n.id] ?? 'pending') as NodeState
            return { id: n.id, testid: `run-step-${n.id}`, label: <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}><span className="g-lead">{`${i + 1}. ${label(n.type)}`}</span><span className="g-detail">{[s, Object.values(n.config).find(Boolean)?.slice(0, 60)].filter(Boolean).join(' · ')}</span></span> }
          })} selected={active ?? ''} onSelect={setSel} /> : <Empty>{t('run.thisFlowEmpty')}</Empty>}
        </Panel>
        <Panel testid="run-output" title={
          <span className="g-seg">
            <button className={`g-seg-btn${tab === 'output' ? ' active' : ''}`} onClick={() => setTab('output')}>{t('run.output')}</button>
            <button className={`g-seg-btn${tab === 'details' ? ' active' : ''}`} onClick={() => setTab('details')}>{t('run.details')}</button>
          </span>} aside={activeNode ? `${label(activeNode.type)} · ${activeNode.id}` : undefined}>
          {tab === 'output'
            ? active && activeNode?.type === 'http_request' && run?.outputs[active]
              ? <HttpRunResult text={run.outputs[active]} elapsed={httpElapsed[`${run.run_id}:${active}`] ?? savedHttpTime(`${run.run_id}:${active}`)} />
              : <NamedTextBox className="g-term" testid="run-output-text"><pre className="g-run-text" style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{(active && run?.outputs[active]) || (run ? t('run.noOutput') : t('run.pressRun'))}</pre></NamedTextBox>
            : <dl className="g-kv">{Object.entries(activeNode?.config ?? {}).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v || t('run.dash')}</dd></Fragment>)}</dl>}
        </Panel>
        <Panel className="g-scroll" title={t('run.verification')} aside={run?.verified === true ? t('run.allChecksPassed') : run?.verified === false ? t('run.notVerified') : undefined} testid="run-verification">
          <div className="g-rows">
            {(run?.verification ?? []).map(c => <Row key={c.check} status={c.passed ? 'ok' : 'bad'} lead={c.kind} detail={c.evidence?.slice(0, 120)} />)}
            {run && !(run.verification ?? []).length && <Empty>{run.verified === null ? t('run.noChecks') : t('run.checksWhenFinished')}</Empty>}
          </div>
        </Panel>
        <Panel title={t('run.usage')} testid="run-usage">
          <dl className="g-kv">
            <dt>{t('run.model')}</dt><dd>{usage.model}</dd>
            <dt>{t('run.route')}</dt><dd>{usage.route}</dd>
            <dt>{t('run.tokens')}</dt><dd>{usage.tokens.toLocaleString()}</dd>
            <dt>{t('run.cost')}</dt><dd data-testid="run-cost">${usage.cost.toFixed(2)}</dd>
          </dl>
        </Panel>
      </div>
      <HintBar><Hint keyLabel="R">{t('hint.run')}</Hint><Hint keyLabel="H">{t('hint.history')}</Hint><Hint keyLabel="B">{t('hint.edit')}</Hint><Hint keyLabel="↑↓">{t('hint.selectStep')}</Hint><Hint keyLabel="Enter">{t('hint.openStep')}</Hint></HintBar>
    </>
  )
}

function HttpRunResult({ text, elapsed }: { text: string; elapsed?: number }) {
  const result = text.match(/^Status: (\d{3})\s*\n\n([\s\S]*)$/)
  if (!result) return <NamedTextBox className="g-term" testid="run-output-text"><pre className="g-run-text" style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{text}</pre></NamedTextBox>
  const body = result[2].slice(0, 2000)
  return <div className="http-result" data-testid="run-http-result-summary">
    <span>{t('http.responseStatus', { status: result[1] })}</span>
    <span>{t('http.responseTime', { time: elapsed === undefined ? t('http.timeUnavailable') : `${elapsed} ms` })}</span>
    <NamedTextBox testid="run-http-result-body"><pre className="g-run-text" style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{body}{result[2].length > 2000 ? t('http.responseTrimmed') : ''}</pre></NamedTextBox>
  </div>
}

function PastRuns({ envId }: { envId: string }) {
  const { env, runs, err, setErr, refreshRuns } = useFlow(envId)
  const [changes, setChanges] = useState<Record<string, number>>({})
  const [sel, setSel] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [note, setNote] = useState('')
  const [deleteUndo, setDeleteUndo] = useState<UndoAction | null>(null)
  useEffect(() => {
    runs.slice(0, 15).forEach(r => api.runChanges(r.run_id).then(c => setChanges(x => ({ ...x, [r.run_id]: c.length }))).catch(() => {}))
  }, [runs])
  const chosen = runs.find(r => r.run_id === (sel ?? runs[0]?.run_id))
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLButtonElement) return
      const index = Math.max(0, runs.findIndex(r => r.run_id === (sel ?? runs[0]?.run_id)))
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        if (runs.length) setSel(runs[(index + (event.key === 'ArrowDown' ? 1 : runs.length - 1)) % runs.length].run_id)
      } else if (event.key === 'Enter' && chosen) { event.preventDefault(); go(`automations/flow/${envId}/${chosen.run_id}`) }
      else if (event.key.toLowerCase() === 'u' && chosen && changes[chosen.run_id]) { event.preventDefault(); setConfirm(true) }
      else if (event.key.toLowerCase() === 'r') { event.preventDefault(); void api.runEnv(envId).then(r => go(`automations/flow/${envId}/${r.run_id}`)).catch(e => setErr(String(e))) }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [runs, sel, chosen, changes, envId, setErr])
  const undo = async () => {
    if (!chosen) return
    try { await api.undoRun(chosen.run_id); setNote(t('run.undone')); setConfirm(false); refreshRuns() } catch (e) { setErr(String(e)); setConfirm(false) }
  }
  return (
    <>
      <PageHead title={t('run.pastRunsTitle', { name: env?.name ?? envId })} crumb={t('run.automations')} sub={t('run.totalRuns', { count: runs.length })}
        side={<><Btn onClick={() => go(`automations/flow/${envId}`)}>{t('run.back')}</Btn><Btn primary icon="run" onClick={() => api.runEnv(envId).then(r => go(`automations/flow/${envId}/${r.run_id}`)).catch(e => setErr(String(e)))} data-testid="rerun">{t('run.rerun')}</Btn></>} />
      {err && <div className="g-error">{err}</div>}
      <DeleteUndo action={deleteUndo} onDone={() => setDeleteUndo(null)} onError={e => setErr(String(e))} />
      <Panel testid="past-runs">
        <table className="g-table">
          <thead><tr><th>{t('run.date')}</th><th>{t('run.result')}</th><th>{t('run.changes')}</th><th>{t('delete.action')}</th></tr></thead>
          <tbody>
            {runs.map(r => {
              const s = RUN_LABEL[r.status]
              return (
              <tr key={r.run_id} className={chosen?.run_id === r.run_id ? 'sel' : ''} style={chosen?.run_id === r.run_id ? { background: 'var(--g-gold)', color: 'var(--g-ink)' } : undefined} onClick={() => { setSel(r.run_id); setConfirm(false); setNote('') }} data-testid={`past-${r.run_id}`}>
                  <td>{when(r.started_at)}</td>
                  <td><span className="g-status-cell"><StatusIcon kind={s?.kind ?? 'idle'} />{s?.label ?? r.status}</span></td>
                  <td>{changes[r.run_id] === undefined ? '…' : changes[r.run_id] === 0 ? t('run.zeroChanges') : t('run.changesCount', { count: changes[r.run_id], plural: changes[r.run_id] > 1 ? 's' : '' })}</td>
                  <td onClick={e => e.stopPropagation()}><DeleteAction label={t('run.deleteRun')} impact={t('delete.runImpact')} testid={`run-delete-${r.run_id}`}
                    onDelete={async () => { await api.deleteRun(r.run_id); return { title: t('delete.removed'), run: async () => { await api.undoDeleteRun(r.run_id); refreshRuns() } } }}
                    onDeleted={action => { setDeleteUndo(action ?? null); refreshRuns() }} onError={e => setErr(String(e))} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {runs.length === 0 && <Empty>{t('run.noRuns')}</Empty>}
      </Panel>
      {chosen && (
        <Panel title={t('run.runDetails')} testid="run-details">
          <div className="g-ask-row">
            <StatusIcon kind={RUN_LABEL[chosen.status]?.kind ?? 'idle'} />
            <span className="g-lead">{when(chosen.started_at)} · {RUN_LABEL[chosen.status]?.label ?? chosen.status}</span>
            <span className="g-detail">{ago(chosen.started_at)}</span>
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
              <Btn primary onClick={() => go(`automations/flow/${envId}/${chosen.run_id}`)} data-testid="run-view">{t('run.view')}</Btn>
              {confirm
                ? <><span className="g-detail">{t('run.undoQuestion')}</span><Btn danger onClick={undo} data-testid="run-undo-yes">{t('run.yesUndo')}</Btn><Btn onClick={() => setConfirm(false)}>{t('run.no')}</Btn></>
                : <Btn onClick={() => setConfirm(true)} disabled={!changes[chosen.run_id]} data-testid="run-undo">{t('run.undo')}</Btn>}
            </span>
          </div>
          {note && <div className="g-saved">{note}</div>}
        </Panel>
      )}
      <HintBar><Hint keyLabel="↑↓">{t('hint.selectRun')}</Hint><Hint keyLabel="Enter">{t('hint.viewRun')}</Hint><Hint keyLabel="U">{t('hint.undo')}</Hint><Hint keyLabel="R">{t('hint.rerun')}</Hint></HintBar>
    </>
  )
}
