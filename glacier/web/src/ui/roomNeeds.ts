import type { HomeRun, HomeSummary } from '../api.ts'

/** Home may cap its needs-you list; still expose every waiting run in the room. */
export function roomApprovalsMissingFromNeedsYou(home: HomeSummary | null): HomeRun[] {
  if (!home) return []
  const listed = new Set(home.needs_you.filter(item => item.kind === 'approval').map(item => item.ref.run_id).filter(Boolean))
  return home.running.filter(run => run.status === 'waiting' && !listed.has(run.run_id))
}
