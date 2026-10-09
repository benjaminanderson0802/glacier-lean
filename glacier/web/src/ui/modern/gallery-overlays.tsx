import { useCallback, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { CommandPalette } from './CommandPalette'
import { Notifications, type GlacierNotification } from './Notifications'
import { Shortcuts } from './Shortcuts'
import { installGlobalShortcuts, registerAction, registerShortcut } from './keys'
import './overlays.css'

function OverlayGallery() {
  const [palette, setPalette] = useState(false)
  const [shortcuts, setShortcuts] = useState(false)
  const [notifications, setNotifications] = useState(false)
  const [feedback, setFeedback] = useState('')
  const say = useCallback((message: string) => setFeedback(message), [])
  useEffect(() => {
    const removers = [
      registerAction({ id: 'nav-home', label: 'Go to Home', group: 'Navigation', icon: '⌂', shortcut: 'Ctrl+1', keywords: ['overview'], run: () => say('Opened Home') }),
      registerAction({ id: 'nav-build', label: 'Open Build', group: 'Navigation', icon: '◇', shortcut: 'Ctrl+2', keywords: ['assistant'], run: () => say('Opened Build') }),
      registerAction({ id: 'nav-automations', label: 'Open Automations', group: 'Navigation', icon: '↗', shortcut: 'Ctrl+3', keywords: ['flows', 'workflows'], run: () => say('Opened Automations') }),
      registerAction({ id: 'nav-memory', label: 'Open Memory', group: 'Navigation', icon: '⌘', shortcut: 'Ctrl+4', keywords: ['notes'], run: () => say('Opened Memory') }),
      registerAction({ id: 'nav-settings', label: 'Open Settings', group: 'Navigation', icon: '⚙', shortcut: 'Ctrl+5', keywords: ['preferences'], run: () => say('Opened Settings') }),
      registerAction({ id: 'new-build', label: 'Start a new build', group: 'Actions', icon: '+', shortcut: 'Ctrl+N', keywords: ['new assistant goal'], run: () => say('Started a new build') }),
      registerAction({ id: 'new-flow', label: 'Create a new flow', group: 'Actions', icon: '＋', keywords: ['automation'], run: () => say('Started a new flow') }),
      registerAction({ id: 'run-flow', label: 'Run a flow', group: 'Actions', icon: '▶', keywords: ['start automation'], run: () => say('Choose a flow to run') }),
      registerAction({ id: 'settings-models', label: 'Open model settings', group: 'Settings', icon: '◈', keywords: ['engine'], run: () => say('Opened Settings · Models') }),
      registerAction({ id: 'toggle-sidebar', label: 'Toggle sidebar', group: 'Actions', icon: '◧', shortcut: 'Ctrl+B', run: () => say('Sidebar toggled') }),
      registerAction({ id: 'toggle-side-panel', label: 'Toggle side panel', group: 'Actions', icon: '◨', shortcut: 'Ctrl+\\', run: () => say('Side panel toggled') }),
      registerAction({ id: 'switch-engine', label: 'Switch engine', group: 'Actions', icon: '⇄', keywords: ['model route'], run: () => say('Engine menu opened') }),
      registerAction({ id: 'recent-chat', label: 'Clip revenue loop', group: 'Recent', icon: '◉', keywords: ['chat build'], run: () => say('Opened Clip revenue loop') }),
      registerAction({ id: 'recent-flow', label: 'Weekly research digest', group: 'Recent', icon: '↻', keywords: ['flow automation'], run: () => say('Opened Weekly research digest') }),
      registerAction({ id: 'recent-note', label: 'Quarterly planning notes', group: 'Recent', icon: '▤', keywords: ['memory'], run: () => say('Opened Quarterly planning notes') }),
      registerShortcut({ id: 'new-build-key', label: 'Start a new build', keys: 'Mod+N', run: () => say('Started a new build') }),
      registerShortcut({ id: 'sidebar-key', label: 'Show or hide the sidebar', keys: 'Mod+B', run: () => say('Sidebar toggled') }),
      registerShortcut({ id: 'panel-key', label: 'Show or hide the side panel', keys: 'Mod+\\', run: () => say('Side panel toggled') }),
      registerShortcut({ id: 'settings-key', label: 'Open Settings', keys: 'Mod+,', run: () => say('Opened Settings') }),
      ...[1, 2, 3, 4, 5].map((number, index) => registerShortcut({ id: `nav-key-${number}`, label: ['Go to Home', 'Open Build', 'Open Automations', 'Open Memory', 'Open Settings'][index], keys: `Mod+${number}`, run: () => say(`Opened ${['Home', 'Build', 'Automations', 'Memory', 'Settings'][index]}`) })),
    ]
    const uninstall = installGlobalShortcuts(() => setPalette(true), () => setNotifications(true))
    const close = () => { setPalette(false); setShortcuts(false); setNotifications(false) }
    const openNotifications = () => setNotifications(true)
    const showShortcuts = () => setShortcuts(true)
    window.addEventListener('glacier:close-overlays', close)
    window.addEventListener('glacier:open-notifications', openNotifications)
    window.addEventListener('glacier:show-shortcuts', showShortcuts)
    return () => { removers.forEach(remove => remove()); uninstall(); window.removeEventListener('glacier:close-overlays', close); window.removeEventListener('glacier:open-notifications', openNotifications); window.removeEventListener('glacier:show-shortcuts', showShortcuts) }
  }, [say])

  const activity: GlacierNotification[] = [
    { id: 'run-finished', kind: 'run', title: 'Research digest is ready', detail: 'Weekly research digest', at: '2 min ago', onOpen: () => say('Opened Weekly research digest') },
    { id: 'approval-waiting', kind: 'approval', title: 'A step is waiting for you', detail: 'Publish the release notes', at: '8 min ago', onOpen: () => say('Opened approval for Publish the release notes') },
    { id: 'run-failed', kind: 'failure', title: 'Backup needs attention', detail: 'Photo backup · Could not reach the drive', at: '18 min ago', onOpen: () => say('Opened Backup photos to NAS') },
  ]

  return <div className="gm-overlay-root gm-overlay-gallery" data-testid="overlay-gallery">
    <div className="gm-gallery-backdrop" aria-hidden="true"><svg viewBox="0 0 1600 1000" preserveAspectRatio="none"><defs>
      <filter id="ice-facets" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".0045 .006" numOctaves="2" seed="11" result="n"/><feDiffuseLighting in="n" lightingColor="#5aa9d6" surfaceScale="6" diffuseConstant=".8" result="d"><feDistantLight azimuth="235" elevation="38"/></feDiffuseLighting><feColorMatrix in="d" values=".18 0 0 0 0 0 .32 0 0 0 0 0 .48 0 0 0 0 0 0 1"/></filter>
      </defs><rect width="100%" height="100%" filter="url(#ice-facets)" opacity=".62"/></svg></div>
    <div className="gm-gallery-shell">
      <header className="gm-gallery-title"><span className="gm-gallery-logo"/><strong>Glacier</strong><span>/ Build / Clip revenue loop</span><span className="gm-gallery-spacer"/><button className="gm-gallery-trigger" type="button" onClick={() => setPalette(true)}>⌕ <span>Search chats, flows, memory…</span><kbd className="gm-kbd">Ctrl K</kbd></button><button aria-label="Open notifications" data-testid="notifications-bell" className="gm-bell" onClick={() => setNotifications(true)}><svg viewBox="0 0 24 24"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg><span className="gm-badge">3</span></button></header>
      <aside className="gm-gallery-sidebar gm-glass"><button className="gm-gallery-new" onClick={() => say('Started a new build')}>＋ &nbsp;New build <kbd className="gm-kbd">Ctrl N</kbd></button><nav className="gm-gallery-nav"><span>⌂ &nbsp;Home</span><span>◇ &nbsp;Build</span><span>↗ &nbsp;Automations</span><span>⌘ &nbsp;Memory</span><span>⚙ &nbsp;Settings</span></nav><div className="gm-gallery-label">Pinned</div><div className="gm-gallery-thread">◉ &nbsp;Clip revenue loop</div><div className="gm-gallery-thread">◌ &nbsp;Weekly research digest</div><div className="gm-gallery-label">Recent</div><div className="gm-gallery-thread">Backup photos to NAS</div><div className="gm-gallery-thread">Explain the failed sync run</div><div className="gm-gallery-account"><span className="gm-gallery-avatar">BA</span><span>Benjamin<br/><small>Codex · local model ready</small></span></div></aside>
      <main className="gm-gallery-main gm-glass"><header className="gm-gallery-main-head"><strong>Clip revenue loop</strong><span className="gm-gallery-tag">Interview · 3 of ~6</span><span className="gm-gallery-tag">Codex</span><div className="gm-gallery-tabs"><span>Chat</span><span>Spec</span><span>Team</span><span>Runs</span></div></header><article className="gm-gallery-copy"><h1>Build a system that earns from clipping campaigns.</h1><p>Scout → parse rules → produce → quality check → post → track → learn. Keep the whole loop visible and ready for your review.</p><div className="gm-gallery-callout"><span className="gm-gallery-tag">Biggest open question</span><p>Where does approved source footage come from: a folder you fill, channels with reuse rights, or each campaign’s own asset pack?</p></div></article><div className="gm-gallery-composer gm-glass"><span>Answer, or add details…</span><span className="gm-gallery-spacer"/><button onClick={() => say('Message added to the build')}>Add detail</button></div></main>
      <aside className="gm-gallery-context gm-glass"><header className="gm-gallery-context-head"><strong>What I understand</strong><span className="gm-gallery-tag">Live</span></header><div className="gm-gallery-context-body"><div><small>Readiness · 62%</small><div className="gm-gallery-meter"><i/></div></div><div><small>Goal</small>An unattended loop that turns approved footage into compliant clips and maximises paid views across campaigns.</div><div><small>Requirements</small><p>Rank live campaigns by return, budget and past results.</p><p>Pause accounts that show a view drop and shift their share.</p></div><div><small>Proposed team</small>Lead · Builders · Independent evaluator</div></div></aside>
    </div>
    {feedback && <div className="gm-feedback" data-testid="gallery-feedback">{feedback}</div>}
    <CommandPalette open={palette} onClose={() => setPalette(false)} />
    <Shortcuts open={shortcuts} onClose={() => setShortcuts(false)} />
    <Notifications items={activity} open={notifications} onClose={() => setNotifications(false)} showBell={false} />
    <button hidden data-testid="gallery-command" onClick={() => setPalette(true)}/><button hidden data-testid="gallery-notifications" onClick={() => setNotifications(true)}/>
  </div>
}

const root = document.getElementById('root')
if (root) createRoot(root).render(<OverlayGallery />)
