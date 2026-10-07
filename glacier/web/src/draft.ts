// A flow handed to the builder before it is saved (e.g. Ask > Edit on a proposed automation).
import type { Environment } from './api.ts'

let draft: (Environment & Record<string, unknown>) | null = null
export function setDraft(flow: Environment & Record<string, unknown>) { draft = flow }
export function takeDraft() { const d = draft; draft = null; return d }
