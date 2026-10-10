import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { messagesApi, subscribeEvents, type MessageSource, type MessageThread, type ThreadMessage } from '../api.ts'
import { t } from '../i18n/index.ts'
import './messenger.css'

type View = 'list' | 'thread' | 'new'
const SOURCES: MessageSource[] = ['glacier', 'codex', 'claude', 'opencode', 'gemini', 'worker']
const initials = (source: MessageSource) => ({ glacier: 'gl', codex: 'co', claude: 'cl', opencode: 'op', gemini: 'ge', worker: 'wk' })[source]
const formatTime = (value: string) => {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? '' : date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}
const dayLabel = (value: string) => {
  if (!value) return t('messenger.earlier')
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return t('messenger.earlier')
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1)
  const day = new Date(date); day.setHours(0, 0, 0, 0)
  if (day.valueOf() === today.valueOf()) return t('messenger.today')
  if (day.valueOf() === yesterday.valueOf()) return t('messenger.yesterday')
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined })
}
const dayKey = (value: string) => value ? new Date(value).toLocaleDateString() : 'unknown'
const eventMessage = (event: unknown): event is { type: string; thread_id?: string; message?: ThreadMessage; message_id?: string; delta?: string } => !!event && typeof event === 'object' && 'type' in event

export function Messenger() {
  const [view, setView] = useState<View>('list')
  const [threads, setThreads] = useState<MessageThread[]>([])
  const [activeId, setActiveId] = useState('')
  const [messages, setMessages] = useState<ThreadMessage[]>([])
  const [nextBefore, setNextBefore] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState('')
  const [newSource, setNewSource] = useState<'glacier' | 'codex' | 'claude'>('glacier')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const active = useMemo(() => threads.find(thread => thread.id === activeId) ?? null, [threads, activeId])
  const mergeMessage = useCallback((message: ThreadMessage) => {
    setMessages(current => current.some(item => item.id === message.id) ? current : [...current, message].sort((a, b) => a.at.localeCompare(b.at)))
  }, [])

  const refreshThreads = useCallback(async (q = query) => {
    try {
      const result = await messagesApi.threads(q)
      if (!Array.isArray(result)) {
        setThreads([])
        setError(t('messenger.invalidThreads'))
        return
      }
      setThreads(result)
      setError('')
    }
    catch (e) { setError(String(e)) }
  }, [query])

  useEffect(() => {
    const timer = setTimeout(() => { void refreshThreads(query) }, query ? 200 : 0)
    return () => clearTimeout(timer)
  }, [query, refreshThreads])

  const loadThread = useCallback(async (id: string, before?: string) => {
    const result = await messagesApi.messages(id, before)
    const page = [...result.messages].reverse()
    if (before) setMessages(current => [...page, ...current.filter(item => !page.some(old => old.id === item.id))])
    else { setMessages(page); stickToBottom.current = true }
    setNextBefore(result.next_before)
  }, [])

  const openThread = async (thread: MessageThread) => {
    setActiveId(thread.id); setView('thread'); setError(''); setLoading(true)
    try { await loadThread(thread.id) }
    catch (e) { setError(String(e)); setMessages([]) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    let refreshTimer: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(event => {
      if (!eventMessage(event)) return
      const incoming = event as { type: string; thread_id?: string; message?: ThreadMessage; message_id?: string; delta?: string }
      if (incoming.type === 'messages.thread_message' && incoming.thread_id && incoming.message) {
        setThreads(rows => rows.map(row => row.id === incoming.thread_id ? { ...row, last_text: incoming.message!.text, last_at: incoming.message!.at, unread: incoming.thread_id !== activeId } : row).sort((a, b) => b.last_at.localeCompare(a.last_at)))
        if (incoming.thread_id === activeId) mergeMessage(incoming.message)
        clearTimeout(refreshTimer); refreshTimer = setTimeout(() => { void refreshThreads(query) }, 150)
      } else if (incoming.type === 'messages.thread_delta' && incoming.thread_id === activeId && incoming.message_id) {
        const partial: ThreadMessage = { id: incoming.message_id, from: 'them', author: 'Glacier', text: incoming.delta ?? '', at: new Date().toISOString(), kind: 'text' }
        setMessages(current => {
          const existing = current.find(item => item.id === partial.id)
          if (existing) return current.map(item => item.id === partial.id ? { ...item, text: item.text + partial.text } : item)
          return [...current, partial]
        })
      }
    }, () => {})
    return () => { off(); clearTimeout(refreshTimer) }
  }, [activeId, mergeMessage, query, refreshThreads])

  useEffect(() => {
    if (!stickToBottom.current) return
    const log = logRef.current
    if (log) log.scrollTop = log.scrollHeight
  }, [messages, view])

  const loadOlder = async () => {
    const log = logRef.current
    if (!activeId || !nextBefore || loadingOlder || !log) return
    const oldHeight = log.scrollHeight, oldTop = log.scrollTop
    setLoadingOlder(true)
    try {
      await loadThread(activeId, nextBefore)
      requestAnimationFrame(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight - oldHeight + oldTop })
    } catch (e) { setError(String(e)) }
    finally { setLoadingOlder(false) }
  }

  const send = async () => {
    const text = draft.trim()
    if (!text || !active || !active.can_send || sending) return
    setDraft(''); setError(''); setSending(true); stickToBottom.current = true
    const optimistic: ThreadMessage = { id: `pending:${crypto.randomUUID()}`, from: 'me', author: t('messenger.you'), text, at: new Date().toISOString(), kind: 'text' }
    mergeMessage(optimistic)
    try {
      const result = await messagesApi.send(active.id, text)
      if (result.message.from === 'me') setMessages(current => [...current.filter(item => item.id !== optimistic.id && item.id !== result.message.id), result.message].sort((a, b) => a.at.localeCompare(b.at)))
      else mergeMessage(result.message)
      setThreads(rows => rows.map(row => row.id === active.id ? { ...row, last_text: result.message.text, last_at: result.message.at } : row).sort((a, b) => b.last_at.localeCompare(a.last_at)))
    } catch (e) {
      setError(String(e)); setDraft(text); setMessages(current => current.filter(item => item.id !== optimistic.id))
      if (active.source === 'codex' || active.source === 'claude') {
        try {
          const rows = await messagesApi.threads(query)
          if (Array.isArray(rows)) { setThreads(rows); setError('') }
        } catch { /* keep the send error visible if the list also failed */ }
      }
    }
    finally { setSending(false) }
  }

  const start = async () => {
    const text = draft.trim()
    if (!text || sending) return
    setError(''); setSending(true)
    try {
      const result = await messagesApi.create(newSource, text)
      setThreads(rows => [result.thread, ...rows.filter(row => row.id !== result.thread.id)].sort((a, b) => b.last_at.localeCompare(a.last_at)))
      setActiveId(result.thread_id); setView('thread'); setDraft(''); setLoading(true)
      await loadThread(result.thread_id).catch(() => setMessages([{ id: result.message.id, from: result.message.from, author: result.message.author, text: result.message.text, at: result.message.at, kind: result.message.kind }]))
    } catch (e) { setError(String(e)) }
    finally { setSending(false); setLoading(false) }
  }

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget
    stickToBottom.current = target.scrollHeight - target.scrollTop - target.clientHeight < 48
    if (target.scrollTop < 28) void loadOlder()
  }

  return <div className="messenger" data-testid="messenger">
    {view === 'list' && <>
      <header className="messenger-head"><div><h2>{t('messenger.title')}</h2><span>{t('messenger.subtitle')}</span></div><button className="messenger-icon-btn" type="button" data-testid="messenger-new" aria-label={t('messenger.newChat')} title={t('messenger.newChat')} onClick={() => { setView('new'); setDraft(''); setError('') }}>＋</button></header>
      <label className="messenger-search"><span aria-hidden="true">⌕</span><input aria-label={t('messenger.search')} value={query} onChange={event => setQuery(event.target.value)} placeholder={t('messenger.search')} /></label>
      {error && <div className="messenger-error" role="alert">{error}</div>}
      <div className="messenger-thread-list" aria-label={t('messenger.threads')}>
        {threads.map(thread => <button type="button" key={thread.id} data-testid={`messenger-thread-${thread.id}`} className="messenger-thread-row" onClick={() => void openThread(thread)}>
          <span className={`messenger-avatar source-${thread.source}`}>{initials(thread.source)}</span>
          <span className="messenger-thread-copy"><span className="messenger-thread-top"><b>{thread.title || thread.source}</b><time>{formatTime(thread.last_at)}</time></span><span className="messenger-preview">{thread.last_text}</span></span>
          {thread.unread && <i className="messenger-unread" aria-label={t('messenger.unread')} />}
        </button>)}
        {threads.length === 0 && <div className="messenger-empty">{t('messenger.noThreads')}</div>}
      </div>
      <footer className="messenger-sources">{SOURCES.map(source => <span key={source} className={`messenger-source source-${source}`}>{source}</span>)}</footer>
    </>}

    {view === 'new' && <>
      <header className="messenger-head"><button className="messenger-icon-btn" type="button" data-testid="messenger-new-back" aria-label={t('messenger.back')} onClick={() => { setView('list'); setError('') }}>‹</button><div><h2>{t('messenger.newChat')}</h2><span>{t('messenger.chooseSource')}</span></div></header>
      <div className="messenger-new-source">{(['glacier', 'codex', 'claude'] as const).map(source => <button key={source} type="button" data-testid={`messenger-source-${source}`} className={newSource === source ? 'selected' : ''} onClick={() => setNewSource(source)}><span className={`messenger-avatar source-${source}`}>{initials(source)}</span>{source}</button>)}</div>
      <label className="messenger-new-label" htmlFor="messenger-new-text">{t('messenger.firstMessage')}</label>
      <textarea id="messenger-new-text" aria-label={t('messenger.startConversation')} value={draft} onChange={event => setDraft(event.target.value)} placeholder={t('messenger.startConversation')} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void start() } }} />
      {error && <div className="messenger-error" role="alert">{error}</div>}
      <button className="messenger-send" type="button" data-testid="messenger-start" disabled={!draft.trim() || sending} onClick={() => void start()}>{sending ? t('messenger.starting') : t('messenger.start')}</button>
    </>}

    {view === 'thread' && <>
      <header className="messenger-chat-head"><button className="messenger-icon-btn" type="button" data-testid="messenger-chat-back" aria-label={t('messenger.back')} onClick={() => { setView('list'); setError(''); void refreshThreads(query) }}>‹</button><span className={`messenger-avatar source-${active?.source ?? 'glacier'}`}>{active ? initials(active.source) : 'gl'}</span><div className="messenger-chat-title"><b>{active?.title ?? ''}</b><span>{active?.source ?? ''}</span></div></header>
      <div ref={logRef} className="messenger-log" onScroll={handleScroll} aria-live="polite">
        {loadingOlder && <div className="messenger-loading">{t('messenger.loadingOlder')}</div>}
        {loading && <div className="messenger-loading">{t('messenger.loading')}</div>}
        {messages.map((message, index) => {
          const previous = messages[index - 1]
          const showDay = !previous || dayKey(previous.at) !== dayKey(message.at)
          return <div key={message.id}>
            {showDay && <div className="messenger-day"><span>{dayLabel(message.at)}</span></div>}
            {message.from === 'system' || message.kind !== 'text'
              ? <div className="messenger-system">{message.text}</div>
              : <div className={`messenger-message ${message.from === 'me' ? 'mine' : 'theirs'}`}><div className="messenger-bubble">{message.text}<time>{formatTime(message.at)}</time></div></div>}
          </div>
        })}
        {messages.length === 0 && !loading && <div className="messenger-empty">{t('messenger.emptyThread')}</div>}
      </div>
      {error && <div className="messenger-error" role="alert">{error}</div>}
      {active?.can_send
        ? <form className="messenger-composer" onSubmit={event => { event.preventDefault(); void send() }}><textarea aria-label={t('messenger.message')} value={draft} onChange={event => setDraft(event.target.value)} placeholder={t('messenger.message')} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() } }} /><button type="submit" className="messenger-send" disabled={!draft.trim() || sending} aria-label={sending ? t('messenger.sending') : t('messenger.send')}>{sending ? '…' : '➤'}</button></form>
        : <div className="messenger-readonly">{active?.can_send_reason || t('messenger.readOnly', { source: active?.source ?? '' })}</div>}
    </>}
  </div>
}
