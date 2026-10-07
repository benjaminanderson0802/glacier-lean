// How much detail the screens show: Simple (fewer step types, no technical fields), Standard (default) or Full.
// A per-person display preference, kept in this browser only; every feature stays reachable in Full.
import { useEffect, useState } from 'react'

export type Layout = 'simple' | 'standard' | 'full'
const KEY = 'glacier.layout'
const subs = new Set<(l: Layout) => void>()

export function getLayout(): Layout {
  try { const v = localStorage.getItem(KEY); return v === 'simple' || v === 'full' ? v : 'standard' } catch { return 'standard' }
}
export function setLayout(l: Layout) {
  try { localStorage.setItem(KEY, l) } catch { /* private window: applies until the app closes */ }
  current = l; subs.forEach(f => f(l))
}
let current: Layout = getLayout()
export function useLayout(): Layout {
  const [l, set] = useState<Layout>(current)
  useEffect(() => { subs.add(set); return () => { subs.delete(set) } }, [])
  return l
}

/** Step types shown in Simple: the everyday ones. */
export const SIMPLE_STEP_TYPES = new Set(['schedule', 'command', 'local_ai', 'note', 'approval', 'check', 'read_document', 'fetch_page'])
