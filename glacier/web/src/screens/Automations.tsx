import { useEffect, useMemo, useState } from 'react'
import { ago, api, teamsApi, type Environment, type EnvSummary, type RunSummary } from '../api.ts'
import { Btn, Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { StatusIcon, type StatusKind } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'

type Flow = EnvSummary & { last?: RunSummary }
const FILTERS = [t('automations.all'), t('automations.running'), t('automations.needsYou'), t('automations.failed')] as const
const STATUS: Record<string, { kind: StatusKind; label: string }> = {
  done: { kind: 'ok', label: t('automations.success') }, failed: { kind: 'bad', label: t('automations.failed') }, rejected: { kind: 'bad', label: t('automations.rejected') },
  running: { kind: 'run', label: t('automations.running') }, waiting: { kind: 'warn', label: t('automations.needsYou') },
}

export function AutomationsScreen() {
  const [flows, setFlows] = useState<Flow[] | null>(null)
  const [filter, setFilter] = useState<typeof FILTERS[number]>(t('automations.all'))
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [naming, setNaming] = useState(false)
  const [name, setName] = useState('')
  const [details, setDetails] = useState<Record<string, Environment>>({})
  const [busy, setBusy] = useState('')
  const [copied, setCopied] = useState('')
  const [undo, setUndo] = useState<UndoAction | null>(null)
  const [teams, setTeams] = useState<{ team_id: string; status: string; done: number; tasks: number; passing: number; feature_count: number; needs_owner: number }[]>([])

  useEffect(() => {
    teamsApi.list().then(setTeams).catch(() => {})
    api.listEnvs().then(async envs => {
      const withRuns = await Promise.all(envs.map(async e => {
        const [runs, detail] = await Promise.all([api.listRuns(e.id).catch(() => [] as RunSummary[]), api.getEnv(e.id).catch(() => null)])
        const startNodes = detail?.nodes.filter(n => ['schedule', 'file_trigger', 'webhook_trigger'].includes(n.type)) ?? []
        const triggerRuns = startNodes.length ? await Promise.all([...runs].map(async run => ({ run, state: await api.getRun(run.run_id).catch(() => null) }))) : []
        const last = startNodes.length && startNodes.every(node => node.type === 'schedule')
          ? [...runs].sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))[0]
          : startNodes.length
          ? triggerRuns.filter(item => startNodes.some(node => item.state?.trigger?.node_id === node.id)).sort((a, b) => b.run.started_at.localeCompare(a.run.started_at))[0]?.run
          : [...runs].sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))[0]
        if (detail) setDetails(prev => ({ ...prev, [e.id]: detail }))
        return { ...e, enabled: detail?.enabled, last }
      }))
      setFlows(withRuns)
    }).catch(e => setErr(String(e)))
  }, [])

  const shown = useMemo(() => (flows ?? []).filter(f => {
    const s = f.last?.status
    if (filter === t('automations.running') && s !== 'running') return false
    if (filter === t('automations.needsYou') && s !== 'waiting') return false
    if (filter === t('automations.failed') && s !== 'failed' && s !== 'rejected') return false
    return !q || f.name.toLowerCase().includes(q.toLowerCase())
  }), [flows, filter, q])

  const create = () => {
    const n = name.trim()
    if (!n) return
    go(`automations/new/${encodeURIComponent(n)}`)
  }

  const save = async (flow: Environment) => {
    setBusy(flow.id); setErr('')
    try { await api.saveEnv(flow); setDetails(prev => ({ ...prev, [flow.id]: flow })); setFlows(prev => prev?.map(f => f.id === flow.id ? { ...f, enabled: flow.enabled } : f) ?? null) }
    catch (e) { setErr(String(e)) } finally { setBusy('') }
  }

  const setStart = async (flow: Environment, choice: string) => {
    const next = structuredClone(flow)
    const oldStartIds = new Set(next.nodes.filter(n => ['schedule', 'file_trigger', 'webhook_trigger'].includes(n.type)).map(n => n.id))
    next.nodes = next.nodes.filter(n => !['schedule', 'file_trigger', 'webhook_trigger'].includes(n.type))
    next.edges = next.edges.filter(edge => !oldStartIds.has(edge.source) && !oldStartIds.has(edge.target))
    if (choice !== 'manual') {
      const id = `start-${choice}`
      const type = choice === 'schedule' ? 'schedule' : choice === 'file' ? 'file_trigger' : 'webhook_trigger'
      next.nodes.unshift({ id, type, config: choice === 'schedule' ? { cron: '0 9 * * *' } : choice === 'file' ? { folder: '', pattern: '*' } : {}, position: { x: 80, y: 80 } })
      const first = next.nodes.find(n => n.id !== id)
      if (first) next.edges.unshift({ id: `${id}-${first.id}`, source: id, target: first.id, label: '' })
    }
    await save(next)
  }

  const copyText = async (value: string, id: string) => {
    await navigator.clipboard.writeText(value); setCopied(id); window.setTimeout(() => setCopied(''), 1600)
  }

  return (
    <>
      <PageHead title={t('automations.title')} sub={t('automations.subtitle')} side={
        naming
          ? <form style={{ display: 'flex', gap: 8 }} onSubmit={e => { e.preventDefault(); create() }}>
              <input className="g-input" autoFocus placeholder={t('automations.newName')} value={name} onChange={e => setName(e.target.value)} data-testid="flow-new-name" style={{ width: 240 }} />
              <Btn primary type="submit" data-testid="flow-new-create">{t('automations.create')}</Btn>
              <Btn onClick={() => setNaming(false)}>{t('automations.cancel')}</Btn>
            </form>
          : <span style={{ display: 'flex', gap: 10 }}><Btn onClick={() => go('automations/templates')} data-testid="flow-templates">{t('automations.templates')}</Btn><Btn primary icon="plus" onClick={() => setNaming(true)} data-testid="flow-new">{t('automations.new')}</Btn></span>
      } />
      <DeleteUndo action={undo} onDone={() => setUndo(null)} onError={e => setErr(String(e))} />
      <Panel className="automations-window" testid="automations-window">
        <section className="g-panel" data-testid="automation-teams"><h2 className="g-panel-title">{t('team.automationTeams')}</h2><div className="g-rows">{teams.length === 0 && <Empty>{t('team.noTeams')}</Empty>}{teams.map(team => <Row key={team.team_id} status={team.needs_owner ? 'warn' : 'run'} lead={`${t('team.teamCard')} ${team.team_id}`} detail={team.status} when={`${team.done}/${team.tasks}`} onClick={() => go(`automations/team/${team.team_id}`)} testid={`automation-team-${team.team_id}`} />)}</div></section>
        <div className="g-toolbar">
          <div className="g-seg" role="tablist">
            {FILTERS.map(f => <button key={f} className={`g-seg-btn${f === filter ? ' active' : ''}`} onClick={() => setFilter(f)} data-testid={`filter-${f}`}>{f}</button>)}
          </div>
          <input className="g-input" placeholder={t('automations.search')} value={q} onChange={e => setQ(e.target.value)} style={{ maxWidth: 260 }} data-testid="flow-search" />
        </div>
        {err && <div className="g-error">{err}</div>}
        <table className="g-table" data-testid="flow-table">
          <thead><tr><th>{t('automations.name')}</th><th>{t('automations.lastRun')}</th><th>{t('automations.status')}</th><th>{t('automations.startsWhen')}</th><th>{t('delete.action')}</th></tr></thead>
          <tbody>
            {shown.map(f => {
              const st = f.last ? STATUS[f.last.status] : undefined
              const detail = details[f.id]
              const trigger = detail?.nodes.find(n => ['schedule', 'file_trigger', 'webhook_trigger'].includes(n.type))
              const choice = trigger?.type === 'schedule' ? 'schedule' : trigger?.type === 'file_trigger' ? 'file' : trigger?.type === 'webhook_trigger' ? 'webhook' : 'manual'
              const cfg = trigger?.config ?? {}
              const active = detail?.enabled !== false
              const apiBase = (globalThis as { __GLACIER_API__?: string }).__GLACIER_API__ ?? 'http://127.0.0.1:8000'
              const hook = `${apiBase.replace(/\/$/, '')}/api/hooks/${encodeURIComponent(f.id)}`
              return (
                <tr key={f.id}>
                  <td className="g-lead"><button className="g-link" title={f.name} style={{ fontSize: 'inherit', fontWeight: 'inherit' }} onClick={() => go(`automations/flow/${f.id}`)} data-testid={`flow-${f.id}`}>{f.name}</button></td>
                  <td>{f.last ? ago(f.last.started_at) : t('automations.never')}</td>
                  <td>{st ? <span className="g-status-cell"><StatusIcon kind={st.kind} />{st.label}</span> : <span className="g-muted">{t('automations.notRun')}</span>}</td>
                  <td><div className="g-trigger-cell" data-testid={`trigger-${f.id}`}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span>{t('automations.startsWhen')}</span>
                      <select className="g-input" aria-label={t('automations.startsWhen')} value={choice} disabled={!detail || busy === f.id} onChange={e => void setStart(detail!, e.target.value)} data-testid={`trigger-choice-${f.id}`}>
                        <option value="manual">{t('automations.byHand')}</option><option value="schedule">{t('automations.onSchedule')}</option><option value="file">{t('automations.whenFile')}</option><option value="webhook">{t('automations.whenRequest')}</option>
                      </select>
                    </label>
                    {!active && <div className="g-muted" data-testid={`trigger-disabled-${f.id}`}>{t('automations.willNotStart')}</div>}
                    {choice === 'schedule' && <label>{t('automations.schedule')} <input className="g-input" value={cfg.cron ?? ''} placeholder={t('automations.scheduleExample')} onChange={e => { const next = structuredClone(detail!); const node = next.nodes.find(n => n.type === 'schedule')!; node.config.cron = e.target.value; setDetails(prev => ({ ...prev, [f.id]: next })) }} onBlur={() => detail && void save(details[f.id])} data-testid={`trigger-schedule-${f.id}`} /></label>}
                    {choice === 'file' && <><label>{t('automations.folder')} <input className="g-input" value={cfg.folder ?? ''} placeholder={t('automations.folderExample')} onChange={e => { const next = structuredClone(details[f.id]); next.nodes.find(n => n.type === 'file_trigger')!.config.folder = e.target.value; setDetails(prev => ({ ...prev, [f.id]: next })) }} onBlur={() => details[f.id] && void save(details[f.id])} data-testid={`trigger-folder-${f.id}`} /></label><label>{t('automations.filePattern')} <input className="g-input" value={cfg.pattern ?? '*'} onChange={e => { const next = structuredClone(details[f.id]); next.nodes.find(n => n.type === 'file_trigger')!.config.pattern = e.target.value; setDetails(prev => ({ ...prev, [f.id]: next })) }} onBlur={() => details[f.id] && void save(details[f.id])} data-testid={`trigger-pattern-${f.id}`} /></label></>}
                    {choice === 'webhook' && <div style={{ display: 'grid', gap: 6 }}><span>{t('automations.localAddress')}</span><div style={{ display: 'flex', gap: 6 }}><code>{hook}</code><Btn onClick={() => void copyText(hook, `address-${f.id}`)} data-testid={`copy-hook-${f.id}`}>{copied === `address-${f.id}` ? t('automations.copied') : t('automations.copy')}</Btn></div><span>{t('automations.tokenHidden')}</span><Btn onClick={() => void copyText((globalThis as { __GLACIER_TOKEN__?: string }).__GLACIER_TOKEN__ ?? '', `token-${f.id}`)} data-testid={`copy-token-${f.id}`}>{copied === `token-${f.id}` ? t('automations.copied') : t('automations.copyToken')}</Btn></div>}
                    <div>{t('automations.lastStart')} {f.last ? <><span>{ago(f.last.started_at)}</span> · <button className="g-link" onClick={() => go(`automations/flow/${f.id}/${f.last!.run_id}`)} data-testid={`last-trigger-run-${f.id}`}>{t('automations.viewRun')}</button></> : t('automations.never')}</div>
                    {detail && <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}><input type="checkbox" checked={active} onChange={e => void save({ ...detail, enabled: e.target.checked })} data-testid={`trigger-enabled-${f.id}`} />{t('automations.enabled')}</label>}
                  </div></td>
                  <td><DeleteAction label={t('automations.deleteFlow')} impact={t('delete.flowImpact')} testid={`flow-delete-${f.id}`}
                    onDelete={async () => { const result = await api.deleteEnv(f.id); return { title: t('delete.removed'), run: async () => {
                      await api.undoDeleteEnv(f.id, result.commit)
                      const restored = await api.getEnv(f.id)
                      setDetails(current => ({ ...current, [f.id]: restored }))
                      setFlows(current => [...(current ?? []).filter(item => item.id !== f.id), { ...f, enabled: restored.enabled }])
                    } } }}
                    onDeleted={action => { setUndo(action ?? null); setFlows(current => current?.filter(item => item.id !== f.id) ?? null) }}
                    onError={e => setErr(String(e))} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {flows && shown.length === 0 && <Empty>{flows.length ? t('automations.noMatches') : t('automations.empty')}</Empty>}
      </Panel>
    </>
  )
}
