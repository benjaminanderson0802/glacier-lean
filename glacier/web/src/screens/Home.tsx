import { useCallback, useEffect, useState } from 'react'
import { ago, loadHome, subscribeEvents, type HomeItem, type HomeSummary } from '../api.ts'
import { Empty, PageHead, Panel, Progress, Row } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { StarterPanel } from './Starter.tsx'
import { t } from '../i18n/index.ts'
import { teamsApi } from '../api.ts'

const KIND_TITLE: Record<HomeItem['kind'], string> = { approval: t('home.kindApproval'), claim: t('home.kindClaim'), failed_run: t('home.kindFailedRun') }

export function HomeScreen() {
  const [data, setData] = useState<HomeSummary | null>(null)
  const [err, setErr] = useState('')
  const [teams, setTeams] = useState<{ team_id: string; name: string; status: string; done: number; tasks: number; passing: number; feature_count: number; needs_owner: number }[]>([])
  const refresh = useCallback(() => { loadHome().then(d => { setData(d); setErr('') }).catch(e => setErr(String(e))) }, [])
  useEffect(() => {
    refresh()
    teamsApi.list().then(setTeams).catch(() => {})
    let t: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(() => { clearTimeout(t); t = setTimeout(refresh, 400) }, () => {})
    const iv = setInterval(refresh, 15000)
    return () => { off(); clearInterval(iv); clearTimeout(t) }
  }, [refresh])

  const open = (it: HomeItem) => {
    if (it.kind === 'claim' && it.ref.claim_id) { go(`home/claim/${it.ref.claim_id}`); return }
    if (it.ref.env_id) go(`automations/flow/${it.ref.env_id}${it.ref.run_id ? `/${it.ref.run_id}` : ''}`)
  }

  return (
    <>
      <PageHead title={t('home.title')} side={
        <div className="g-statusbox" data-testid="home-status">
          <div>{(() => {
            const on = data?.local_ai.online
            const cls = on ? '' : on === false ? ' off' : ' wait'
            const label = on ? t('home.localOnline') : on === false ? t('home.localOffline') : t('home.checkingLocal')
            return <span className={`g-online${cls}`} title={data?.local_ai.model ?? undefined} data-testid="local-ai"><i className="g-dot" />{label}</span>
          })()}</div>
          <div>
            <span data-testid="count-running">{data?.counts.running ?? 0} {t('home.runningCount')}</span>
            <span data-testid="count-need-you">{data?.counts.need_you ?? 0} {t('home.needYouCount')}</span>
          </div>
        </div>
      } />
      {err && <div className="g-error">{err}</div>}
      <div className="g-grid-2 g-home-grid" style={{ flex: 1, minHeight: 0, gridColumn: '1 / -1', gridRow: '2 / 4', display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gridTemplateRows: 'minmax(0, 1fr)', gap: 'calc(2 * var(--px))' }}>
        <div className="g-stack" style={{ gridColumn: 1, gridRow: 1, minHeight: 0 }}>
        <StarterPanel />
        <Panel title={t('home.needsYou')} aside={<button className="g-link" onClick={() => go('home/claims')} data-testid="all-claims">{t('home.allClaims')}</button>} testid="needs-you" style={{ flex: 1 }}>
          <div className="g-rows">
            {data?.needs_you.length === 0 && <Empty>{t('home.noItemsNeedAttention')}</Empty>}
            {data?.needs_you.map((it, i) => (
              <Row key={i} status="bad" lead={`1 ${KIND_TITLE[it.kind] ?? it.title}`} detail={it.detail} when={ago(it.at)} onClick={() => open(it)} testid={`need-${i}`} />
            ))}
          </div>
        </Panel>
        </div>
        <div className="g-stack" style={{ gridColumn: 2, gridRow: 1, minHeight: 0 }}>
          <Panel title={t('home.runningNow')} testid="running-now" style={{ flex: '0 0 30%' }}>
            <div className="g-rows">
              {data?.running.length === 0 && <Empty>{t('home.nothingRunning')}</Empty>}
              {data?.running.map(r => (
                <Row key={r.run_id} status={r.status === 'queued' ? 'warn' : 'run'} lead={r.name}
                  detail={r.status === 'queued' ? undefined : t('home.step', { step: r.step, steps: r.steps })}
                  when={r.status === 'queued' ? 'queued' : <Progress value={r.step} max={r.steps} />}
                  onClick={() => go(`automations/flow/${r.env_id}/${r.run_id}`)} testid={`running-${r.run_id}`} />
              ))}
            </div>
          </Panel>
          <Panel title={t('team.homeTeams')} testid="home-teams" style={{ flex: '0 0 30%' }}>
            <div className="g-rows">{teams.length === 0 && <Empty>{t('team.noTeams')}</Empty>}{teams.map(team => <Row key={team.team_id} status={team.needs_owner ? 'warn' : 'run'} lead={team.name || team.team_id} detail={team.needs_owner ? t('team.ownerWaiting', { count: team.needs_owner }) : t('team.homeTeam', { passing: team.passing, total: team.feature_count })} when={<Progress value={team.passing} max={team.feature_count} />} onClick={() => go(`automations/team/${team.team_id}`)} testid={`home-team-${team.team_id}`} />)}</div>
          </Panel>
          <Panel title={t('home.recentNotes')} testid="recent-notes" style={{ flex: 1 }}>
            <div className="g-rows">
              {data?.recent_notes.length === 0 && <Empty>{t('home.noNotes')}</Empty>}
              {data?.recent_notes.map(n => (
                <Row key={n.path + n.at} icon="note" lead={n.summary} leadTitle={n.summary} when={ago(n.at)} onClick={() => go(`memory/${encodeURIComponent(n.path)}`)} testid={`note-${n.path}`} />
              ))}
            </div>
          </Panel>
        </div>
      </div>
      {!data && !err && <div className="g-empty"><StatusIcon kind="run" /> {t('home.loading')}</div>}
    </>
  )
}
