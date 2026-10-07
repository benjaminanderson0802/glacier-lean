import { useEffect, useMemo, useState } from 'react'
import { ago, api, type EnvSummary, type RunSummary } from '../api.ts'
import { Btn, Empty, PageHead, Panel } from '../ui/kit.tsx'
import { StatusIcon, type StatusKind } from '../ui/Pixel.tsx'
import { go } from '../route.ts'

type Flow = EnvSummary & { last?: RunSummary }
const FILTERS = ['All', 'Running', 'Needs you', 'Failed'] as const
const STATUS: Record<string, { kind: StatusKind; label: string }> = {
  done: { kind: 'ok', label: 'Success' }, failed: { kind: 'bad', label: 'Failed' }, rejected: { kind: 'bad', label: 'Rejected' },
  running: { kind: 'run', label: 'Running' }, waiting: { kind: 'warn', label: 'Needs you' },
}

export function AutomationsScreen() {
  const [flows, setFlows] = useState<Flow[] | null>(null)
  const [filter, setFilter] = useState<typeof FILTERS[number]>('All')
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [naming, setNaming] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => {
    api.listEnvs().then(async envs => {
      const withRuns = await Promise.all(envs.map(async e => {
        const runs = await api.listRuns(e.id).catch(() => [] as RunSummary[])
        const last = [...runs].sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))[0]
        return { ...e, last }
      }))
      setFlows(withRuns)
    }).catch(e => setErr(String(e)))
  }, [])

  const shown = useMemo(() => (flows ?? []).filter(f => {
    const s = f.last?.status
    if (filter === 'Running' && s !== 'running') return false
    if (filter === 'Needs you' && s !== 'waiting') return false
    if (filter === 'Failed' && s !== 'failed' && s !== 'rejected') return false
    return !q || f.name.toLowerCase().includes(q.toLowerCase())
  }), [flows, filter, q])

  const create = () => {
    const n = name.trim()
    if (!n) return
    go(`automations/new/${encodeURIComponent(n)}`)
  }

  return (
    <>
      <PageHead title="Automations" sub="Your flows." side={
        naming
          ? <form style={{ display: 'flex', gap: 8 }} onSubmit={e => { e.preventDefault(); create() }}>
              <input className="g-input" autoFocus placeholder="Name the new flow" value={name} onChange={e => setName(e.target.value)} data-testid="flow-new-name" style={{ width: 240 }} />
              <Btn primary type="submit" data-testid="flow-new-create">Create</Btn>
              <Btn onClick={() => setNaming(false)}>Cancel</Btn>
            </form>
          : <Btn primary icon="plus" onClick={() => setNaming(true)} data-testid="flow-new">New</Btn>
      } />
      <Panel>
        <div className="g-toolbar">
          <div className="g-seg" role="tablist">
            {FILTERS.map(f => <button key={f} className={`g-seg-btn${f === filter ? ' active' : ''}`} onClick={() => setFilter(f)} data-testid={`filter-${f}`}>{f}</button>)}
          </div>
          <input className="g-input" placeholder="Search flows…" value={q} onChange={e => setQ(e.target.value)} style={{ maxWidth: 260 }} data-testid="flow-search" />
        </div>
        {err && <div className="g-error">{err}</div>}
        <table className="g-table" data-testid="flow-table">
          <thead><tr><th>Name</th><th>Last run</th><th>Status</th></tr></thead>
          <tbody>
            {shown.map(f => {
              const st = f.last ? STATUS[f.last.status] : undefined
              return (
                <tr key={f.id} onClick={() => go(`automations/flow/${f.id}`)} data-testid={`flow-${f.id}`} tabIndex={0} onKeyDown={e => e.key === 'Enter' && go(`automations/flow/${f.id}`)}>
                  <td className="g-lead">{f.name}</td>
                  <td>{f.last ? ago(f.last.started_at) : 'never'}</td>
                  <td>{st ? <span className="g-status-cell"><StatusIcon kind={st.kind} />{st.label}</span> : <span className="g-muted">Not run yet</span>}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {flows && shown.length === 0 && <Empty>{flows.length ? 'No flows match.' : 'No flows yet. Press New, or ask the assistant to make one.'}</Empty>}
      </Panel>
    </>
  )
}
