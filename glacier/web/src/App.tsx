// Glacier window: top bar with exactly five options, the active screen, and the keyboard footer.
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Icon, Logo, type IconName } from './ui/Pixel.tsx'
import { go, TABS, useRoute, type Tab } from './route.ts'
import { HomeScreen } from './screens/Home.tsx'
import { AskScreen } from './screens/Ask.tsx'
import { AutomationsScreen } from './screens/Automations.tsx'
import { MemoryScreen } from './screens/Memory.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { CommandPalette } from './screens/CommandPalette.tsx'

const BuildScreen = lazy(() => import('./screens/Build.tsx'))

const LABEL: Record<Tab, string> = { home: 'Home', ask: 'Ask', automations: 'Automations', memory: 'Memory', settings: 'Settings' }

async function winAction(a: 'minimize' | 'close') {
  if (!('__TAURI_INTERNALS__' in window)) return
  const { getCurrentWindow } = await import('@tauri-apps/api/window')
  await getCurrentWindow()[a]()
}

export default function App() {
  const { tab, rest } = useRoute()
  const [palette, setPalette] = useState(false)
  const [status, setStatus] = useState('Ready.')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette(p => !p) }
      else if (e.key === 'F1') { e.preventDefault(); go('settings/help') }
      else if (e.ctrlKey && e.key === 'Tab') {
        e.preventDefault()
        const i = TABS.indexOf(tab)
        go(TABS[(i + (e.shiftKey ? TABS.length - 1 : 1)) % TABS.length])
      } else if (e.altKey && /^[1-5]$/.test(e.key)) { e.preventDefault(); go(TABS[Number(e.key) - 1]) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [tab])

  const building = tab === 'automations' && (rest[0] === 'build' || rest[0] === 'new')
  const screen = useMemo(() => {
    switch (tab) {
      case 'ask': return <AskScreen />
      case 'automations': return building
        ? <Suspense fallback={<div className="g-empty">Loading the builder…</div>}><BuildScreen initialEnv={rest[0] === 'build' ? rest[1] : undefined} initialRun={rest[0] === 'build' ? rest[2] : undefined} newName={rest[0] === 'new' ? rest[1] : undefined} onStatus={setStatus} /></Suspense>
        : <AutomationsScreen />
      case 'memory': return <MemoryScreen path={rest[0]} />
      case 'settings': return <SettingsScreen section={rest[0]} />
      default: return <HomeScreen />
    }
  }, [tab, rest, building])

  return (
    <div className="g-window" data-testid="window">
      <nav className="g-topbar">
        <div className="g-brand"><Logo px={3} />Glacier</div>
        <div className="g-tabs" role="tablist">
          {TABS.map(t => (
            <button key={t} role="tab" aria-selected={t === tab} className={`g-tab${t === tab ? ' active' : ''}`} data-testid={`nav-${t}`} onClick={() => go(t)}>
              <Icon name={t as IconName} />{LABEL[t]}
            </button>
          ))}
        </div>
        <div className="g-winctl">
          <button className="g-winbtn" aria-label="Minimise" onClick={() => winAction('minimize')}><Icon name="min" /></button>
          <button className="g-winbtn" aria-label="Close" onClick={() => winAction('close')}><Icon name="close" /></button>
        </div>
      </nav>
      <main className={`g-main${building ? ' flush' : ''}`} data-testid={`screen-${tab}`}>{screen}</main>
      <footer className="g-footer">
        <span><span className="g-key">F1</span> Help</span>
        <span><span className="g-key">Ctrl+K</span> Command</span>
        <span><span className="g-key">Ctrl+Tab</span> Switch</span>
        <span className="g-ready" data-testid="status-line">{status}</span>
      </footer>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
    </div>
  )
}
