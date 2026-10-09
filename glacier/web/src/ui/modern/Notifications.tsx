import { useEffect, useMemo, useState } from 'react'
import './overlays.css'

export type GlacierNotification = { id: string; kind: 'run' | 'approval' | 'failure'; title: string; detail: string; at: string; read?: boolean; onOpen?: () => void }
const icons = { run: '✓', approval: '◷', failure: '!' }
const labels = { run: 'Run finished', approval: 'Needs your approval', failure: 'Run needs attention' }

export function Notifications({ items, open, onClose, onOpenItem, showBell = true }: { items: GlacierNotification[]; open: boolean; onClose: () => void; onOpenItem?: (item: GlacierNotification) => void; showBell?: boolean }) {
  const [read, setRead] = useState<Set<string>>(() => new Set(items.filter(item => item.read).map(item => item.id)))
  const [toasts, setToasts] = useState<GlacierNotification[]>([])
  const known = useMemo(() => new Set(items.map(item => item.id)), [items])
  const unread = items.filter(item => !read.has(item.id)).length

  useEffect(() => {
    const previous = new Set((window as Window & { __glacierNotificationIds?: string[] }).__glacierNotificationIds ?? [])
    const fresh = items.filter(item => !previous.has(item.id))
    if (previous.size) {
      fresh.forEach(item => {
        setToasts(current => [...current, item])
        window.setTimeout(() => setToasts(current => current.filter(candidate => candidate.id !== item.id)), 4200)
      })
    }
    ;(window as Window & { __glacierNotificationIds?: string[] }).__glacierNotificationIds = [...known]
  }, [items, known])

  useEffect(() => {
    const close = () => onClose()
    window.addEventListener('glacier:close-overlays', close)
    return () => window.removeEventListener('glacier:close-overlays', close)
  }, [onClose])

  const openItem = (item: GlacierNotification) => {
    setRead(current => new Set(current).add(item.id))
    item.onOpen?.()
    onOpenItem?.(item)
    onClose()
  }
  return <>
    {showBell && <button type="button" className="gm-bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} data-testid="notifications-bell" onClick={() => open ? onClose() : window.dispatchEvent(new CustomEvent('glacier:open-notifications'))}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>
      {unread > 0 && <span className="gm-badge">{unread}</span>}
    </button>}
    {open && <div className="gm-scrim gm-notice-scrim" data-testid="notifications-scrim" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <section className="gm-notifications gm-glass" role="dialog" aria-modal="true" aria-label="Notifications" onMouseDown={event => event.stopPropagation()}>
        <header className="gm-dialog-head"><div><span className="gm-eyebrow">Your activity</span><h2>Notifications{unread > 0 && <span className="gm-unread-label">{unread} new</span>}</h2></div><button type="button" aria-label="Close notifications" className="gm-icon-button" onClick={onClose}>×</button></header>
        <div className="gm-notification-list">{items.length ? items.map(item => <button key={item.id} className={`gm-notification${read.has(item.id) ? ' is-read' : ''}`} type="button" data-testid="notification-item" onClick={() => openItem(item)}>
          <span className={`gm-notice-icon is-${item.kind}`}>{icons[item.kind]}</span><span className="gm-notice-copy"><strong>{item.title}</strong><small>{labels[item.kind]} · {item.detail}</small></span><time>{item.at}</time>{!read.has(item.id) && <i aria-label="Unread"/>}
        </button>) : <div className="gm-empty-notifications"><span>✧</span><strong>You’re all caught up</strong><small>Updates will appear here.</small></div>}</div>
        <footer className="gm-dialog-foot">Updates from your runs and approvals</footer>
      </section>
    </div>}
    <div className="gm-toasts" aria-live="polite">{toasts.map(item => <button className="gm-toast gm-glass" key={item.id} onClick={() => openItem(item)}><span className={`gm-notice-icon is-${item.kind}`}>{icons[item.kind]}</span><span><strong>{item.title}</strong><small>{labels[item.kind]}</small></span><span className="gm-toast-close">×</span></button>)}</div>
  </>
}
