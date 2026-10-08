// Glacier window: top bar with exactly five options, the active screen, and the keyboard footer.
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Icon, Logo } from './ui/Pixel.tsx'
import { go, TABS, useRoute, type Tab } from './route.ts'
import { HomeScreen } from './screens/Home.tsx'
import { BuildTeamsScreen } from './screens/BuildTeams.tsx'
import { AutomationsScreen } from './screens/Automations.tsx'
import { MemoryScreen } from './screens/Memory.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { RunView } from './screens/RunView.tsx'
import { ClaimDetail, ClaimsList } from './screens/Claims.tsx'
import { Templates } from './screens/Templates.tsx'
import { CommandPalette } from './screens/CommandPalette.tsx'
import { Splash } from './screens/Splash.tsx'
import { t as translate } from './i18n/index.ts'

// Show the start screen once per launch, only when the app opens without a specific address.
let splashSeen = location.hash.replace(/^#\/?/, '') !== ''

const BuildScreen = lazy(() => import('./screens/Build.tsx'))

const LABEL: Record<Tab, string> = { home: 'nav.home', ask: 'nav.build', automations: 'nav.automations', memory: 'nav.memory', settings: 'nav.settings' }

const isDesktop = '__TAURI_INTERNALS__' in window

async function winAction(a: 'minimize' | 'close') {
  if (!('__TAURI_INTERNALS__' in window)) return
  const { getCurrentWindow } = await import('@tauri-apps/api/window')
  await getCurrentWindow()[a]()
}

export default function App() {
  const { tab, rest } = useRoute()
  const [palette, setPalette] = useState(false)
  const [status, setStatus] = useState(translate('build.ready'))
  const [splash, setSplash] = useState(!splashSeen)
  const [updateNotice, setUpdateNotice] = useState<{ version: string; notes: string } | null>(null)
  const [updateDismissed, setUpdateDismissed] = useState(false)

  useEffect(() => { if (location.hash === '#/ask' || location.hash.startsWith('#/ask/')) location.replace(location.hash.replace('#/ask', '#/build')) }, [])

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
      if (e.key.startsWith('Arrow') && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        const i = TABS.indexOf(tab)
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); go(TABS[(i + 1) % TABS.length]) }
        else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); go(TABS[(i + TABS.length - 1) % TABS.length]) }
      }
      else if (e.key === 'Enter' && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) { (document.querySelector('.g-menu-item[aria-current="page"]') as HTMLButtonElement | null)?.click() }
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

  const building = tab === 'ask' || tab === 'automations' && (rest[0] === 'build' || rest[0] === 'new')
  const screen = useMemo(() => {
    switch (tab) {
      case 'ask': return <BuildTeamsScreen />
      case 'automations': return building
        ? <Suspense fallback={<div className="g-empty">{translate('build.loading')}</div>}><BuildScreen initialEnv={rest[0] === 'build' ? rest[1] : undefined} initialRun={rest[0] === 'build' ? rest[2] : undefined} newName={rest[0] === 'new' ? rest[1] : undefined} onStatus={setStatus} /></Suspense>
        : rest[0] === 'team' && rest[1] ? <BuildTeamsScreen teamId={rest[1]} />
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
      <nav className="g-topbar" data-tauri-drag-region>
        <div className="g-brand" data-tauri-drag-region><Logo px={3} /><span className="g-brand-name">GLACIER - {translate(LABEL[tab]).toUpperCase()}</span></div>
        <div className="g-tabs" aria-hidden="true" />
        {isDesktop && <div className="g-winctl" data-tauri-drag-region="false">
          <button className="g-winbtn" aria-label={translate('shell.minimize')} title={translate('shell.minimize')} onClick={() => winAction('minimize')}><Icon name="min" /></button>
          <button className="g-winbtn" aria-label={translate('shell.close')} title={translate('shell.close')} onClick={() => winAction('close')}><Icon name="close" /></button>
        </div>}
      </nav>
      <aside className="g-side" data-testid="game-menu">
        <section className="g-panel"><h2 className="g-panel-title">MENU</h2><div className="g-menu-list" role="tablist" aria-orientation="vertical">{TABS.map((item) => <button key={item} role="tab" aria-selected={item === tab} data-testid={`nav-${item}`} aria-current={item === tab ? 'page' : undefined} className={`g-menu-item${item === tab ? ' active' : ''}`} onClick={() => go(item)}><span className="g-menu-cursor"/><span className="g-menu-icon" style={{ '--icon': `url('./theme/sprites/icon-${item === 'ask' ? 'build' : item}.png')` } as React.CSSProperties}/>{translate(LABEL[item])}</button>)}</div></section>
        <section className="g-panel g-engines"><h2 className="g-panel-title">ENGINES</h2><small>● Codex</small><small>● granite</small></section>
      </aside>
      <main className={`g-main${building ? ' flush' : ''}`} data-testid={`screen-${tab}`}>{screen}</main>
      {tab === 'home' && updateNotice && !updateDismissed && <aside className="g-notice" data-testid="home-update-notice"><div><strong>{translate('home.updateAvailable', { version: updateNotice.version })}</strong>{updateNotice.notes && <div className="g-detail">{updateNotice.notes}</div>}</div><button className="g-link" data-testid="home-update-dismiss" onClick={() => setUpdateDismissed(true)}>{translate('home.dismissUpdate')}</button></aside>}
      <footer className="g-footer">
        <span><span className="g-key">F1</span> {translate('shell.help')}</span>
        <span><span className="g-key">Ctrl+K</span> {translate('shell.command')}</span>
        <span><span className="g-key">Ctrl+Tab</span> {translate('shell.switch')}</span>
        <span className="g-ready" data-testid="status-line">{status}</span>
      </footer>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
      {splash && <Splash version={__APP_VERSION__} onDone={to => { splashSeen = true; setSplash(false); if (to === 'exit') winAction('close'); else go(to) }} />}
    </div>
  )
}
