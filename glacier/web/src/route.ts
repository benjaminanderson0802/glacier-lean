// Tiny hash router: #/home, #/build[/<interview|spec|plan>], #/automations[/team/<id>|build/<env>], #/memory[/<note>], #/settings[/<section>]
import { useEffect, useState } from 'react'

export const TABS = ['home', 'ask', 'automations', 'memory', 'settings'] as const
export type Tab = typeof TABS[number]

export function parse(hash = location.hash): { tab: Tab; rest: string[] } {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  if (parts[0] === 'build') parts[0] = 'ask'
  const tab = (TABS as readonly string[]).includes(parts[0]) ? parts[0] as Tab : 'home'
  return { tab, rest: parts.slice(1) }
}

export function go(path: string) { location.hash = `#/${path === 'ask' ? 'build' : path.startsWith('ask/') ? path.replace(/^ask\//, 'build/') : path}` }

export function useRoute() {
  const [r, setR] = useState(parse)
  useEffect(() => {
    const on = () => setR(parse())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return r
}
