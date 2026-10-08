import { useCallback, useEffect, useState } from 'react'
import { ago, loadHome, subscribeEvents, type HomeItem, type HomeSummary } from '../api.ts'
import { Empty, PageHead, Panel, Progress, Row } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { StarterPanel } from './Starter.tsx'
import { t } from '../i18n/index.ts'

const KIND_TITLE: Record<HomeItem['kind'], string> = { approval: t('home.kindApproval'), claim: t('home.kindClaim'), failed_run: t('home.kindFailedRun') }

export function HomeScreen() {
  const [data, setData] = useState<HomeSummary | null>(null)
  const [err, setErr] = useState('')
  const refresh = useCallback(() => { loadHome().then(d => { setData(d); setErr('') }).catch(e => setErr(String(e))) }, [])
  useEffect(() => {
    refresh()
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
      <StarterPanel />
      <div className="g-grid-2" style={{ flex: 1 }}>
        <Panel title={t('home.needsYou')} aside={<button className="g-link" onClick={() => go('home/claims')} data-testid="all-claims">{t('home.allClaims')}</button>} testid="needs-you">
          <div className="g-rows">
            {data?.needs_you.length === 0 && <Empty>{t('home.nothingNeedsYou')}</Empty>}
            {data?.needs_you.map((it, i) => (
              <Row key={i} status="bad" lead={`1 ${KIND_TITLE[it.kind] ?? it.title}`} detail={it.detail} when={ago(it.at)} onClick={() => open(it)} testid={`need-${i}`} />
            ))}
          </div>
        </Panel>
        <div className="g-stack">
          <Panel title={t('home.runningNow')} testid="running-now">
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
          <Panel title={t('home.recentNotes')} testid="recent-notes" style={{ flex: 1 }}>
            <div className="g-rows">
              {data?.recent_notes.length === 0 && <Empty>{t('home.noNotes')}</Empty>}
              {data?.recent_notes.map(n => (
                <Row key={n.path + n.at} icon="note" lead={n.summary} when={ago(n.at)} onClick={() => go(`memory/${encodeURIComponent(n.path)}`)} testid={`note-${n.path}`} />
              ))}
            </div>
          </Panel>
        </div>
      </div>
      {!data && !err && <div className="g-empty"><StatusIcon kind="run" /> {t('home.loading')}</div>}
    </>
  )
}
