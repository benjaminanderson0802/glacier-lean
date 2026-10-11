import { useEffect, useState } from 'react'
import { loadHome, subscribeEvents, teamsApi, type BuildTeam, type HomeSummary } from '../api.ts'

type TeamSummary = Awaited<ReturnType<typeof teamsApi.list>>[number]
export type RoomTeam = TeamSummary & { detail: BuildTeam | null }

/** Read-only shell data. Refresh on reconnect/events as well as polling for team changes. */
export function useRoomStatus() {
  const [home, setHome] = useState<HomeSummary | null>(null)
  const [teams, setTeams] = useState<RoomTeam[] | null>(null)
  const [homeError, setHomeError] = useState('')
  const [teamError, setTeamError] = useState('')
  const [connected, setConnected] = useState(false)
  useEffect(() => {
    let disposed = false, busy = false, again = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const refreshTeams = async () => {
      const rows = (await teamsApi.list()).filter(team => !['done', 'stopped'].includes(team.status))
      // A missing team detail must not turn an existing team into an empty team.
      const details = await Promise.allSettled(rows.map(team => teamsApi.get(team.team_id)))
      return rows.map((team, i) => ({ ...team, detail: details[i].status === 'fulfilled' ? details[i].value : null }))
    }
    const refresh = async () => {
      if (disposed) return
      if (busy) { again = true; return }
      busy = true
      const [summary, roster] = await Promise.allSettled([loadHome(), refreshTeams()])
      if (disposed) return
      if (summary.status === 'fulfilled') { setHome(summary.value); setHomeError('') }
      else { setHome(null); setHomeError(String(summary.reason)) }
      if (roster.status === 'fulfilled') { setTeams(roster.value); setTeamError('') }
      else { setTeams(null); setTeamError(String(roster.reason)) }
      busy = false
      if (again) { again = false; schedule() }
    }
    // Coalesce bursts without postponing updates indefinitely during worker output.
    const schedule = () => {
      if (disposed || timer) return
      timer = setTimeout(() => { timer = undefined; void refresh() }, 300)
    }
    void refresh()
    const off = subscribeEvents(schedule, online => {
      if (disposed) return
      setConnected(online)
      if (online) schedule()
    })
    const interval = setInterval(schedule, 15000)
    window.addEventListener('focus', schedule)
    return () => { disposed = true; off(); clearTimeout(timer); clearInterval(interval); window.removeEventListener('focus', schedule) }
  }, [])
  return { home, teams, connected, homeError, teamError }
}
