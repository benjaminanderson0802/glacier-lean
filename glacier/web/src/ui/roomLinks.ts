import type { HomeItem } from '../api.ts'

export const roomTeamPath = (id: string) => `automations/team/${encodeURIComponent(id)}`
export const roomRunPath = (env: string, run: string) => `automations/flow/${encodeURIComponent(env)}/${encodeURIComponent(run)}`

export function roomNeedPath(item: HomeItem): string {
  if (item.ref.claim_id) return `home/claim/${encodeURIComponent(item.ref.claim_id)}`
  if (item.ref.env_id && item.ref.run_id) return roomRunPath(item.ref.env_id, item.ref.run_id)
  // Venture setup and incomplete references belong in the existing owner inbox.
  return 'home'
}
