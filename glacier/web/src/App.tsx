// Glacier window: top bar with exactly five options, the active screen, and the keyboard footer.
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Icon, Logo, type IconName } from './ui/Pixel.tsx'
import { go, TABS, useRoute, type Tab } from './route.ts'
import { HomeScreen } from './screens/Home.tsx'
import { AskScreen } from './screens/Ask.tsx'
import { AutomationsScreen } from './screens/Automations.tsx'
import { MemoryScreen } from './screens/Memory.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { RunView } from './screens/RunView.tsx'
import { ClaimDetail, ClaimsList } from './screens/Claims.tsx'
import { Templates } from './screens/Templates.tsx'
import { CommandPalette } from './screens/CommandPalette.tsx'
import { Splash } from './screens/Splash.tsx'
import { t } from './i18n/index.ts'

// Show the start screen once per launch, only when the app opens without a specific address.
let splashSeen = location.hash.replace(/^#\/?/, '') !== ''

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
  const [splash, setSplash] = useState(!splashSeen)
  const [updateNotice, setUpdateNotice] = useState<{ version: string; notes: string } | null>(null)
  const [updateDismissed, setUpdateDismissed] = useState(false)

  useEffect(() => {
    const receive = (event: Event) => {
      const detail = (event as CustomEvent<{ version: string; notes: string }>).detail
      if (detail?.version) { setUpdateNotice(detail); setUpdateDismissed(false) }
    }
    window.addEventListener('glacier-update-available', receive)
    if (window.__GLACIER_UPDATE_NOTICE__) receive(new CustomEvent('glacier-update-available', { detail: window.__GLACIER_UPDATE_NOTICE__ }))
    return () => window.removeEventListener('glacier-update-available', receive)
  }, [])

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
        : rest[0] === 'flow' && rest[1]
          ? <RunView key={rest.join('/')} envId={rest[1]} runId={rest[2] !== 'history' ? rest[2] : undefined} history={rest[2] === 'history'} />
          : rest[0] === 'templates' ? <Templates /> : <AutomationsScreen />
      case 'memory': return <MemoryScreen path={rest[0]} />
      case 'settings': return <SettingsScreen section={rest[0]} />
      default: return rest[0] === 'claim' && rest[1] ? <ClaimDetail id={rest[1]} /> : rest[0] === 'claims' ? <ClaimsList /> : <HomeScreen />
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
      {tab === 'home' && updateNotice && !updateDismissed && <aside className="g-notice" data-testid="home-update-notice"><div><strong>{t('home.updateAvailable', { version: updateNotice.version })}</strong>{updateNotice.notes && <div className="g-detail">{updateNotice.notes}</div>}</div><button className="g-link" data-testid="home-update-dismiss" onClick={() => setUpdateDismissed(true)}>{t('home.dismissUpdate')}</button></aside>}
      <footer className="g-footer">
        <span><span className="g-key">F1</span> Help</span>
        <span><span className="g-key">Ctrl+K</span> Command</span>
        <span><span className="g-key">Ctrl+Tab</span> Switch</span>
        <span className="g-ready" data-testid="status-line">{status}</span>
      </footer>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
      {splash && <Splash version={__APP_VERSION__} onDone={to => { splashSeen = true; setSplash(false); if (to === 'exit') winAction('close'); else go(to) }} />}
    </div>
  )
}
