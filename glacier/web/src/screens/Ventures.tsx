import { useEffect, useState } from 'react'
import { venturesApi, type Venture, type VentureStep } from '../api.ts'
import { t } from '../i18n/index.ts'
import { go } from '../route.ts'
import { Btn, Empty } from '../ui/kit.tsx'

function Step({ step }: { step: VentureStep }) {
  const links = [...new Set([...(step.links ?? []), step.link, step.url].filter((link): link is string => !!link))]
    .filter(link => /^#\/(settings|automations|memory|home|ask)(\/|$)/.test(link) || /^https?:\/\//i.test(link))
  return <div className="venture-step" data-testid={`your-step-${step.id}`}>
    <div className="venture-step-copy"><strong className="venture-user-content">{step.title}</strong><p className="venture-user-content">{step.instructions || step.detail}</p>
      {links.map(link => <a key={link} href={link} target={link.startsWith('#') ? undefined : '_blank'} rel="noopener noreferrer" className={link.startsWith('#/settings') ? '' : 'venture-user-content'}>{link.startsWith('#/settings') ? t('settings.title') : link}</a>)}
    </div>
  </div>
}

export function Ventures({ query }: { query: string }) {
  const [rows, setRows] = useState<Venture[] | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    let loading = false
    const refresh = async () => {
      if (loading) return
      loading = true
      try {
        const data = await venturesApi.list()
        if (active) { setRows(data); setError('') }
      } catch { if (active) setError(t('ventures.loadFailed')) }
      finally { loading = false }
    }
    void refresh()
    const timer = window.setInterval(() => { if (!document.hidden) void refresh() }, 10000)
    return () => { active = false; window.clearInterval(timer) }
  }, [reload])
  const shown = rows?.filter(row => `${row.name} ${row.description}`.toLowerCase().includes(query.trim().toLowerCase()))
  return <div className="venture-list" data-testid="venture-list">
    {error && <div className="g-error" role="alert">{error} <Btn onClick={() => setReload(value => value + 1)}>{t('ventures.refresh')}</Btn></div>}
    {!error && rows === null && <Empty>{t('home.loading')}</Empty>}
    {shown?.map(venture => {
      const steps = venture.your_steps.filter(step => !step.done)
      const last = venture.last_run
      return <article className="venture-card" key={venture.slug} data-testid={`venture-${venture.slug}`}>
        <header className="venture-card-head"><h2 className="venture-user-content">{venture.name}</h2><span className="venture-status" data-testid={`venture-status-${venture.slug}`} title={venture.readiness === 'blocked' ? undefined : t(`ventures.${venture.readiness}Help`)}>{t(`ventures.${venture.readiness}`)}</span></header>
        <div className="venture-card-copy"><strong>{t('ventures.what')}</strong><p className={venture.description ? 'venture-user-content' : undefined}>{venture.description || t('ventures.noDescription')}</p></div>
        {venture.blockers.length > 0 && <ul className="venture-blockers">{venture.blockers.map(reason => <li key={reason}>{t(`ventures.${reason}`)}</li>)}</ul>}
        <div className="venture-card-copy"><strong>{t('ventures.lastRun')}</strong> · {last
          ? <a className="g-link" href={`#/automations/flow/${encodeURIComponent(last.env_id)}/${encodeURIComponent(last.run_id)}`} data-testid={`venture-last-run-${venture.slug}`}>{t('ventures.runResult', { status: t(`ventures.result.${last.status}`), when: new Date(last.started_at).toLocaleString() })}</a>
          : t('ventures.neverRun')}</div>
        <div className="venture-card-copy"><strong>{t('ventures.nextRun')}</strong> · {venture.next_run ? new Date(venture.next_run).toLocaleString() : t('ventures.notScheduled')}</div>
        <div className="venture-card-copy"><strong>{t('ventures.today')}</strong> · {t('ventures.todayCounts', venture.today)}</div>
        <div className="venture-card-actions">
          <Btn primary disabled={!!busy || !venture.run_available} onClick={async () => {
            setBusy(venture.slug); setError('')
            try { const run = await venturesApi.run(venture.slug); go(`automations/flow/${encodeURIComponent(run.env_id)}/${encodeURIComponent(run.run_id)}`) }
            catch (reason) { setError(String(reason)) }
            finally { setBusy('') }
          }} data-testid={`venture-run-${venture.slug}`}>{t('ventures.runDry')}</Btn>
          {!venture.run_available && <span className="g-muted">{t('ventures.runUnavailable')}</span>}
        </div>
        <div className="venture-steps"><strong>{t('ventures.yourSteps')} · {t('ventures.stepProgress', { done: venture.your_steps.length - steps.length, total: venture.your_steps.length })}</strong>
          {steps.slice(0, 2).map(step => <Step key={step.id} step={step} />)}
          {steps.length > 2 && <details><summary>{t('ventures.moreSteps', { count: steps.length - 2 })}</summary>{steps.slice(2).map(step => <Step key={step.id} step={step} />)}</details>}
          {steps.length === 0 && <span className="g-muted">{t('ventures.noSteps')}</span>}
        </div>
      </article>
    })}
    {shown?.length === 0 && <Empty>{t(rows?.length ? 'ventures.noMatches' : 'ventures.empty')}</Empty>}
  </div>
}
