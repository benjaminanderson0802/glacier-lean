// Right wall of the room: the active team, what needs the owner, and what is running. Live from /api/home and /api/teams.
import { useCallback, useEffect, useState } from 'react'
import { loadHome, subscribeEvents, teamsApi, type HomeSummary } from '../api.ts'
import { Progress } from '../ui/kit.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'

type TeamRow = Awaited<ReturnType<typeof teamsApi.list>>[number]

export function SideStatus() {
  const [home, setHome] = useState<HomeSummary | null>(null)
  const [team, setTeam] = useState<TeamRow | null>(null)
  const [roles, setRoles] = useState<string[]>([])

  const refresh = useCallback(() => {
    loadHome().then(setHome).catch(() => {})
    teamsApi.list().then(list => {
      const active = list.find(x => x.status !== 'done' && x.status !== 'stopped') ?? list[0] ?? null
      setTeam(active)
      if (active) teamsApi.get(active.team_id).then(full => setRoles(full.plan?.team?.roles?.map(r => r.id) ?? [])).catch(() => setRoles([]))
      else setRoles([])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    refresh()
    let timer: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(() => { clearTimeout(timer); timer = setTimeout(refresh, 500) }, () => {})
    const iv = setInterval(refresh, 15000)
    return () => { off(); clearInterval(iv); clearTimeout(timer) }
  }, [refresh])

  const needs = home?.needs_you ?? []
  const running = home?.running ?? []

  return (
    <>
      <section className="l-side-block" data-testid="side-team">
        <h2 className="l-side-head">{t('shell.team')}</h2>
        {team
          ? <button type="button" className="l-side-line" onClick={() => go(`automations/team/${team.team_id}`)}>{roles.length ? roles.join(' · ') : (team.name || team.team_id)}</button>
          : <span className="l-side-line">{t('team.noTeams')}</span>}
      </section>
      <section className="l-side-block" data-testid="side-needs-you">
        <h2 className="l-side-head">{t('home.needsYou')}</h2>
        <div className="l-side-list">
          {needs.length === 0 && <span className="l-side-line">{t('home.noItemsNeedAttention')}</span>}
          {needs.slice(0, 4).map((it, i) => (
            <button type="button" key={i} className="l-side-line" onClick={() => {
              if (it.kind === 'claim' && it.ref.claim_id) go(`home/claim/${it.ref.claim_id}`)
              else if (it.ref.env_id) go(`automations/flow/${it.ref.env_id}${it.ref.run_id ? `/${it.ref.run_id}` : ''}`)
            }}>{it.detail || it.title}</button>
          ))}
        </div>
      </section>
      <section className="l-side-block" data-testid="side-running">
        <h2 className="l-side-head">{t('shell.running')}</h2>
        <div className="l-side-list">
          {running.length === 0 && <span className="l-side-line">{t('home.nothingRunning')}</span>}
          {running.slice(0, 3).map(r => (
            <button type="button" key={r.run_id} className="l-side-line l-run" onClick={() => go(`automations/flow/${r.env_id}/${r.run_id}`)}>
              <span>{r.name}{r.steps ? ` · ${Math.round(r.step / r.steps * 100)}%` : ''}</span>
              <Progress value={r.step} max={r.steps} />
            </button>
          ))}
        </div>
      </section>
    </>
  )
}
