import { t } from "../i18n/index.ts"

export type IconName =
  | 'home' | 'ask' | 'automations' | 'memory' | 'settings' | 'note'
  | 'run' | 'lock' | 'plus' | 'search' | 'send' | 'min' | 'close'

const ICONS: Record<IconName, React.ReactNode> = {
  home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-7h6v7"/></>,
  ask: <><path d="M12 18h.01"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 5"/><circle cx="12" cy="12" r="10"/></>,
  automations: <><path d="M4 7h10M4 17h16M14 7l3-3 3 3M10 17l-3 3-3-3"/><circle cx="4" cy="7" r="1"/><circle cx="20" cy="17" r="1"/></>,
  memory: <><path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H20v17H7.5A2.5 2.5 0 0 0 5 21.5z"/><path d="M5 4.5v17M9 6h7M9 10h7"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.8 1.8 0 0 1-2.5 2.5l-.1-.1a1.8 1.8 0 0 0-3 .9v.2a1.8 1.8 0 0 1-3.6 0v-.2a1.8 1.8 0 0 0-3-.9l-.1.1a1.8 1.8 0 1 1-2.5-2.5l.1-.1a1.8 1.8 0 0 0-.9-3h-.2a1.8 1.8 0 0 1 0-3.6h.2a1.8 1.8 0 0 0 .9-3l-.1-.1a1.8 1.8 0 1 1 2.5-2.5l.1.1a1.8 1.8 0 0 0 3-.9v-.2a1.8 1.8 0 0 1 3.6 0v.2a1.8 1.8 0 0 0 3 .9l.1-.1a1.8 1.8 0 1 1 2.5 2.5l-.1.1a1.8 1.8 0 0 0 .9 3h.2a1.8 1.8 0 0 1 0 3.6h-.2a1.8 1.8 0 0 0-.9 3z"/></>,
  note: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></>,
  run: <><circle cx="12" cy="12" r="10"/><path d="m10 8 6 4-6 4z"/></>,
  lock: <><rect x="4" y="10" width="16" height="12" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v4"/></>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  send: <><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></>,
  min: <><path d="M5 12h14"/></>,
  close: <><path d="m18 6-12 12M6 6l12 12"/></>,
}

export function Icon({ name, px: _px = 3, className }: { name: IconName; px?: number; className?: string }) {
  return <svg className={`g-icon ${className ?? ''}`} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[name]}</svg>
}

export type StatusKind = 'bad' | 'warn' | 'ok' | 'run' | 'idle'
export function StatusIcon({ kind }: { kind: StatusKind; px?: number }) {
  const title = kind === 'ok' ? t('pixel.done') : kind === 'warn' ? t('pixel.queued') : kind === 'run' ? t('pixel.running') : kind === 'idle' ? t('pixel.waiting') : t('pixel.needsYou')
  return <span className={`g-status l-dot l-dot-${kind}`} role="img" aria-label={title} title={title} />
}

export function Logo({ px: _px = 2 }: { px?: number }) {
  return <span className="g-logo" role="img" aria-label="limbo">limbo</span>
}
