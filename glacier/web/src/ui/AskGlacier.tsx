import { createContext, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { chat } from '../api.ts'
import { t } from '../i18n/index.ts'

type AskLocation = { screen: string; focus: string }
type AskState = { location: AskLocation | null; setLocation: (location: AskLocation | null) => void; open: boolean; setOpen: (open: boolean) => void }
const Context = createContext<AskState | null>(null)

function routeLocation(): AskLocation {
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  if (parts[0] === 'build' || parts[0] === 'ask') return { screen: 'build', focus: parts[1] || 'interview' }
  if (parts[0] === 'memory') return { screen: 'memory', focus: parts.slice(1).join('/') }
  if (parts[0] === 'settings') return { screen: 'settings', focus: parts[1] || 'general' }
  if (parts[0] === 'automations' && parts[1] === 'build') return { screen: 'automations/build', focus: parts[2] || 'new flow' }
  if (parts[0] === 'automations') return { screen: 'automations', focus: '' }
  return { screen: parts[0] || 'home', focus: parts.slice(1).join('/') }
}

export function AskGlacierProvider({ children }: { children: ReactNode }) {
  const [locationContext, setLocationContext] = useState<AskLocation | null>(() => routeLocation())
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const update = () => setLocationContext(routeLocation())
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  return <Context.Provider value={{ location: locationContext, setLocation: setLocationContext, open, setOpen }}>{children}</Context.Provider>
}

function useAskState() {
  const value = useContext(Context)
  if (!value) throw new Error('AskGlacier must be used inside AskGlacierProvider')
  return value
}

// Screen components call this once with their current focus so the global action follows open content.
export function useAskContext(screen: string, focus: string) {
  const { setLocation } = useAskState()
  useEffect(() => { setLocation({ screen, focus }) }, [screen, focus, setLocation])
}

export function AskGlacier() {
  const { setOpen } = useAskState()
  return <button type="button" className="g-link" data-testid="ask-glacier-open" onClick={() => setOpen(true)} title={t('askGlacier.shortcut')}>{t('askGlacier.action')}</button>
}

type Line = { who: 'you' | 'glacier'; text: string }

export function AskGlacierPanel() {
  const { location: current, open, setOpen } = useAskState()
  const [context, setContext] = useState<AskLocation | null>(current)
  const [draft, setDraft] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { if (!open) return; setContext(current); setDraft(t('askGlacier.prompt', { screen: current?.screen ?? 'home', focus: current?.focus || t('askGlacier.currentScreen') })) }, [open, current])
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [lines, busy])

  const send = async (event: FormEvent) => {
    event.preventDefault()
    const message = draft.trim()
    if (!message || busy) return
    const conversationId = sessionStorage.getItem('glacier.ask-glacier-conversation') || crypto.randomUUID()
    sessionStorage.setItem('glacier.ask-glacier-conversation', conversationId)
    setDraft(''); setBusy(true); setError('')
    setLines(rows => [...rows, { who: 'you', text: message }, { who: 'glacier', text: '' }])
    const patch = (update: (line: Line) => Line) => setLines(rows => [...rows.slice(0, -1), update(rows[rows.length - 1])])
    try {
      await chat(message, conversationId, value => {
        if (value.type === 'text') patch(line => ({ ...line, text: line.text + value.delta }))
        else if (value.type === 'error') patch(line => ({ ...line, text: value.message }))
      }, context ? { screen: context.screen, focus: context.focus } : undefined)
    } catch (cause) {
      const message = t('ask.assistantError', { error: String(cause) })
      patch(line => ({ ...line, text: message })); setError(message)
    } finally { setBusy(false) }
  }

  if (!open) return null
  return <section aria-label={t('askGlacier.title')} data-testid="ask-glacier-panel" style={{ position: 'absolute', inset: 'calc(2 * var(--px))', zIndex: 5, display: 'flex', flexDirection: 'column', gap: 'calc(3 * var(--px))', minWidth: 0, padding: 'calc(4 * var(--px))', border: '1px solid var(--l-edge)', borderRadius: 'var(--l-radius)', background: 'var(--l-glass-deep)', backdropFilter: 'blur(18px)', color: 'var(--g-white)', textShadow: 'var(--l-text-shadow)' }}>
    <header style={{ display: 'flex', alignItems: 'center', gap: 'calc(2 * var(--px))' }}><strong style={{ flex: 1, fontSize: 'var(--g-size-h2)', textTransform: 'lowercase' }}>{t('askGlacier.title')}</strong><button type="button" className="messenger-icon-btn" aria-label={t('askGlacier.close')} data-testid="ask-glacier-close" onClick={() => setOpen(false)}>×</button></header>
    {context && <div data-testid="ask-glacier-context" style={{ display: 'flex', alignItems: 'center', gap: 'calc(2 * var(--px))', width: 'fit-content', maxWidth: '100%', padding: 'calc(1 * var(--px)) calc(3 * var(--px))', border: '1px solid var(--l-edge)', borderRadius: '999px', background: 'var(--g-ice1)', fontSize: 'var(--g-size-small)' }}>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t('askGlacier.on', { context: [context.screen, context.focus].filter(Boolean).join(' · ') })}</span>
      <button type="button" className="g-link" aria-label={t('askGlacier.removeContext')} onClick={() => { setContext(null); setDraft(t('askGlacier.prompt', { screen: t('askGlacier.currentScreen'), focus: t('askGlacier.currentScreen') })) }}>×</button>
    </div>}
    <div className="messenger-log" data-testid="ask-glacier-log" aria-live="polite" style={{ flex: 1, padding: 'calc(2 * var(--px)) 0' }}>
      {lines.map((line, index) => <div key={index} className={`messenger-message ${line.who === 'you' ? 'mine' : 'theirs'}`}><div className="messenger-bubble" data-testid={`ask-glacier-message-${index}`}>{line.text || (busy && index === lines.length - 1 ? '…' : '')}</div></div>)}
      <div ref={end} />
    </div>
    {error && <div className="messenger-error" role="alert">{error}</div>}
    <form className="messenger-composer" onSubmit={event => void send(event)}>
      <textarea aria-label={t('askGlacier.input')} data-testid="ask-glacier-input" value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
      <button type="submit" className="messenger-send" data-testid="ask-glacier-send" disabled={busy || !draft.trim()} aria-label={t('ask.send')}>{busy ? '…' : '➤'}</button>
    </form>
  </section>
}

export function useAskGlacierOpen() {
  return useAskState().setOpen
}
