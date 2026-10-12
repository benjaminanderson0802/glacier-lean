import { Messenger } from './Messenger.tsx'
import { useRoomStatus, type RoomTeam } from '../ui/roomStatus.ts'
import { t } from '../i18n/index.ts'
import { go } from '../route.ts'
import { roomNeedPath, roomRunPath as runPath, roomTeamPath as teamPath } from '../ui/roomLinks.ts'
import { roomApprovalsMissingFromNeedsYou } from '../ui/roomNeeds.ts'

function WorkerList({ team }: { team: RoomTeam }) {
  if (!team.detail) return <small>{t('settingsSections.unavailable')}</small>
  const { plan, tasks } = team.detail
  return <ul className="l-workers" aria-label={t('team.roles')}>
    {plan.team.roles.map(role => {
      const assigned = plan.tasks.filter(task => task.role === role.id)
      return <li key={role.id}>
        <span className="l-user-text">{role.id}{role.model ? ` · ${role.model}` : ''}</span>
        {assigned.map(task => <small key={task.id} className="l-worker-task"><span className="l-user-text">{task.title}</span> · {String(tasks[task.id]?.status ?? '—').replaceAll('_', ' ')}</small>)}
      </li>
    })}
  </ul>
}

// Keep messages available below the compact, independently scrolling live overview.
function RoomOverview() {
  const { home, teams, connected, homeError, teamError } = useRoomStatus()
  const waitingTeams = teams?.filter(team => team.needs_owner > 0) ?? []
  const waitingRuns = roomApprovalsMissingFromNeedsYou(home)
  const pending = (error: string) => <p className="l-side-empty" title={error || undefined}>{t(error ? 'settingsSections.unavailable' : 'home.loading')}</p>
  return <>
    <div className="l-live" data-testid="room-live" data-connected={connected} role="status" title={t(connected ? 'build.liveConnected' : 'build.liveDisconnected')}>
      <i className={`l-dot ${connected ? 'l-dot-ok' : 'l-dot-warn'}`} aria-hidden="true" />{t(connected ? 'build.live' : 'build.liveDisconnected')}
    </div>
    <div className="l-overview" data-testid="room-overview">
      <details className="l-side-block" open>
        <summary className="l-side-head">{t('shell.team')} <span data-testid="room-team-count">{teams?.length ?? '—'}</span></summary>
        {!teams ? pending(teamError) : teams.length === 0 ? <p className="l-side-empty">{t('team.noTeams')}</p> : teams.map(team => <div className="l-team" key={team.team_id} data-testid={`room-team-${team.team_id}`}>
          <button className="l-side-line" onClick={() => go(teamPath(team.team_id))}><span className="l-user-text">{team.name}</span><small>{team.status.replaceAll('_', ' ')}</small></button>
          <WorkerList team={team} />
        </div>)}
      </details>
      <details className="l-side-block" open>
        <summary className="l-side-head">{t('home.needsYou')} <span data-testid="room-needs-count">{home && teams ? home.counts.need_you + waitingTeams.reduce((sum, team) => sum + team.needs_owner, 0) : '—'}</span></summary>
        {!home ? pending(homeError) : home.needs_you.map((item, index) => <button key={`${item.kind}-${item.ref.run_id ?? item.ref.claim_id ?? item.ref.venture_slug}-${index}`} className="l-side-line" data-testid={`room-need-${index}`} onClick={() => go(roomNeedPath(item))}>
          <span className="l-user-text">{item.detail || item.title}</span><small>{item.kind === 'approval' ? t('home.kindApproval') : item.title}</small>
        </button>)}
        {waitingRuns.map(run => <button key={run.run_id} className="l-side-line" data-testid={`room-need-run-${run.run_id}`} onClick={() => go(runPath(run.env_id, run.run_id))}>
          <span className="l-user-text">{run.name}</span><small>{t('home.kindApproval')}</small>
        </button>)}
        {waitingTeams.map(team => <button key={team.team_id} className="l-side-line" onClick={() => go(teamPath(team.team_id))}><span className="l-user-text">{team.name}</span><small>{t('team.ownerWaiting', { count: team.needs_owner })}</small></button>)}
        {teamError && pending(teamError)}
        {home && teams && home.counts.need_you === 0 && waitingTeams.length === 0 && <p className="l-side-empty">{t('home.noItemsNeedAttention')}</p>}
      </details>
      <details className="l-side-block" open>
        <summary className="l-side-head">{t('shell.running')} <span data-testid="room-running-count">{home?.counts.running ?? '—'}</span></summary>
        {!home ? pending(homeError) : home.running.length === 0 ? <p className="l-side-empty">{t('home.nothingRunning')}</p> : home.running.map(run => <button key={run.run_id} className="l-side-line" data-testid={`room-run-${run.run_id}`} onClick={() => go(runPath(run.env_id, run.run_id))}>
          <span className="l-user-text">{run.name}</span><small>{t(`pixel.${run.status}`)} · {t('home.step', { step: run.step, steps: run.steps })}</small>
        </button>)}
      </details>
    </div>
  </>
}

export function SideStatus() {
  return <><RoomOverview /><Messenger /></>
}
