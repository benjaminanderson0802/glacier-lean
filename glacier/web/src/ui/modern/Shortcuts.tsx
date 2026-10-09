import { useEffect, useState } from 'react'
import { getShortcuts, subscribeRegistry, type RegisteredShortcut } from './keys'
import './overlays.css'

export function Shortcuts({ open, onClose, shortcuts: extraShortcuts = [] }: { open: boolean; onClose: () => void; shortcuts?: RegisteredShortcut[] }) {
  const [version, setVersion] = useState(0)
  useEffect(() => subscribeRegistry(() => setVersion(v => v + 1)), [])
  useEffect(() => {
    const show = () => window.dispatchEvent(new CustomEvent('glacier:show-shortcuts'))
    window.addEventListener('glacier:shortcuts', show)
    return () => window.removeEventListener('glacier:shortcuts', show)
  }, [])
  useEffect(() => {
    const close = () => onClose()
    window.addEventListener('glacier:close-overlays', close)
    return () => window.removeEventListener('glacier:close-overlays', close)
  }, [onClose])
  if (!open) return null
  const shortcuts = [...getShortcuts(), ...extraShortcuts]
  const groups = [...new Set(shortcuts.map(item => item.id.startsWith('nav-') ? 'Navigation' : item.id === 'escape' ? 'Panels' : 'Glacier'))]
  return <div className="gm-scrim" data-testid="shortcuts-scrim" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="gm-shortcuts gm-glass" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" onMouseDown={event => event.stopPropagation()}>
      <header className="gm-dialog-head"><div><span className="gm-eyebrow">Move around faster</span><h2>Keyboard shortcuts</h2></div><button type="button" aria-label="Close shortcuts" className="gm-icon-button" onClick={onClose}>×</button></header>
      <div className="gm-shortcut-list" data-testid="shortcut-list" key={version}>
        {groups.map(group => <div className="gm-shortcut-group" key={group}><div className="gm-section-label">{group}</div>{shortcuts.filter(item => (item.id.startsWith('nav-') ? 'Navigation' : item.id === 'escape' ? 'Panels' : 'Glacier') === group).map(item => <ShortcutRow key={item.id} shortcut={item} />)}</div>)}
      </div>
      <footer className="gm-dialog-foot">Shortcuts work while you’re using Glacier.</footer>
    </section>
  </div>
}

function ShortcutRow({ shortcut }: { shortcut: RegisteredShortcut }) {
  return <div className="gm-shortcut-row"><span>{shortcut.label}</span><span className="gm-keyset">{shortcut.keys.split('+').map(key => <kbd className="gm-kbd" key={key}>{key === 'Mod' ? '⌘ / Ctrl' : key}</kbd>)}</span></div>
}
