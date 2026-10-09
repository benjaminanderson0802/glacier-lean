// Limbo window: a painted room with three frosted panels. Left wall = menu, back wall = active screen, right wall = team / needs you / running.
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Icon, Logo } from './ui/Pixel.tsx'
import { go, TABS, useRoute, type Tab } from './route.ts'
import { HomeScreen } from './screens/Home.tsx'
import { BuildTeamsScreen } from './screens/BuildTeams.tsx'
import { AskScreen } from './screens/Ask.tsx'
import { AutomationsScreen } from './screens/Automations.tsx'
import { MemoryScreen } from './screens/Memory.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { RunView } from './screens/RunView.tsx'
import { ClaimDetail, ClaimsList } from './screens/Claims.tsx'
import { Templates } from './screens/Templates.tsx'
import { CommandPalette } from './screens/CommandPalette.tsx'
import { Splash } from './screens/Splash.tsx'
import { SideStatus } from './screens/SideStatus.tsx'
import { LEFT_WALL, RIGHT_WALL, wallStyle } from './ui/wallQuad.ts'
import { t as translate } from './i18n/index.ts'
import { releasesApi } from './api.ts'

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
  const [installedUpdate, setInstalledUpdate] = useState<string | null>(null)
  const [installedNoticeDismissed, setInstalledNoticeDismissed] = useState(false)
  const stageRef = useRef<HTMLDivElement>(null)
  const [stage, setStage] = useState({ w: 1672, h: 941 })
  useEffect(() => {
    const el = stageRef.current; if (!el) return
    const ro = new ResizeObserver(() => setStage({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el); return () => ro.disconnect()
  }, [])

  useEffect(() => {
    let live = true
    releasesApi.lastSeen().then(({ version }) => {
      if (!live) return
      if (version && version !== __APP_VERSION__) setInstalledUpdate(__APP_VERSION__)
      else if (!version) void releasesApi.markSeen(__APP_VERSION__)
    }).catch(() => {})
    return () => { live = false }
  }, [])

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

  const building = tab === 'ask' && rest[0] !== 'chat' || tab === 'automations' && (rest[0] === 'build' || rest[0] === 'new')
  const screen = useMemo(() => {
    switch (tab) {
      case 'ask': return rest[0] === 'chat' ? <AskScreen /> : <BuildTeamsScreen />
      case 'automations': return building
        ? <Suspense fallback={<div className="g-empty">{translate('build.loading')}</div>}><BuildScreen initialEnv={rest[0] === 'build' ? rest[1] : undefined} initialRun={rest[0] === 'build' ? rest[2] : undefined} newName={rest[0] === 'new' ? rest[1] : undefined} onStatus={setStatus} /></Suspense>
        : rest[0] === 'team' && rest[1] ? <BuildTeamsScreen teamId={rest[1]} />
        : rest[0] === 'flow' && rest[1]
          ? <RunView key={rest.join('/')} envId={rest[1]} runId={rest[2] !== 'history' ? rest[2] : undefined} history={rest[2] === 'history'} />
          : rest[0] === 'templates' ? <Templates /> : <AutomationsScreen />
      case 'home': return rest[0] === 'claim' && rest[1] ? <ClaimDetail id={rest[1]} /> : rest[0] === 'claims' ? <ClaimsList /> : <HomeScreen />
      case 'memory': return <MemoryScreen path={rest[0]} />
      case 'settings': return <SettingsScreen section={rest[0]} />
      default: return <HomeScreen />
    }
  }, [tab, rest, building])

  return (
    <div className={`l-viewport g-window${building ? ' is-building' : ''}`} data-testid="window">
      <div className="l-backdrop" aria-hidden="true" />
      <div className="l-stage" ref={stageRef}>
        <div className="l-dragbar" data-tauri-drag-region>
          <nav className="g-topbar" aria-hidden="true"><div className="g-brand"><Logo px={3} /><span className="g-brand-name">GLACIER - {translate(LABEL[tab]).toUpperCase()}</span></div></nav>
          {isDesktop && <div className="g-winctl" data-tauri-drag-region="false">
            <button className="g-winbtn" aria-label={translate('shell.minimize')} title={translate('shell.minimize')} onClick={() => winAction('minimize')}><Icon name="min" /></button>
            <button className="g-winbtn" aria-label={translate('shell.close')} title={translate('shell.close')} onClick={() => winAction('close')}><Icon name="close" /></button>
          </div>}
        </div>
        <aside className="l-wall l-left l-glass g-side" data-testid="game-menu" style={wallStyle(stage.w, stage.h, LEFT_WALL)}>
          <div className="l-brand">glacier</div>
          <button type="button" className="g-menu-item l-new" data-testid="nav-new-task" onClick={() => go('ask')}>{translate('shell.newTask')}</button>
          <div className="g-menu-list" role="tablist" aria-orientation="vertical">{TABS.map((item) => <button key={item} role="tab" aria-selected={item === tab} data-testid={`nav-${item}`} aria-label={translate(LABEL[item])} title={translate(LABEL[item])} aria-current={item === tab ? 'page' : undefined} className={`g-menu-item${item === tab ? ' active' : ''}`} onClick={() => go(item)}>{translate(LABEL[item])}</button>)}</div>
          <div className="l-engines g-engines"><small>● Codex</small><small>● granite</small></div>
        </aside>
        <div className="l-center l-glass">
          <main className={`g-main${building ? ' flush' : ''}`} data-testid={`screen-${tab}`}>{screen}</main>
        </div>
        <aside className="l-wall l-right l-glass" data-testid="side-status" style={wallStyle(stage.w, stage.h, RIGHT_WALL)}><SideStatus /></aside>
        <footer className="l-status">
          <span><span className="g-key">Ctrl+K</span> {translate('shell.command')} · <span className="g-key">F1</span> {translate('shell.help')}</span>
          <span className="g-ready" data-testid="status-line" title={status}>{status}</span>
        </footer>
        {tab === 'home' && installedUpdate && !installedNoticeDismissed && <aside className="g-notice" data-testid="home-installed-update-notice"><div><strong>{translate('home.updatedTo', { version: installedUpdate })}</strong> <button className="g-link" data-testid="home-whats-new" onClick={() => { setInstalledNoticeDismissed(true); void releasesApi.markSeen(installedUpdate); go('settings/about') }}>{translate('home.seeWhatsNew')}</button></div><button className="g-link" data-testid="home-installed-update-dismiss" onClick={() => { setInstalledNoticeDismissed(true); void releasesApi.markSeen(installedUpdate) }}>{translate('home.dismissUpdate')}</button></aside>}
        {tab === 'home' && updateNotice && !updateDismissed && <aside className="g-notice" data-testid="home-update-notice"><div><strong>{translate('home.updateAvailable', { version: updateNotice.version })}</strong>{updateNotice.notes && <div className="g-detail">{updateNotice.notes}</div>}</div><button className="g-link" data-testid="home-update-dismiss" onClick={() => setUpdateDismissed(true)}>{translate('home.dismissUpdate')}</button></aside>}
      </div>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
      {splash && <Splash version={__APP_VERSION__} onDone={to => { splashSeen = true; setSplash(false); if (to === 'exit') winAction('close'); else go(to) }} />}
    </div>
  )
}
