import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ClipboardEvent, type DragEvent, type KeyboardEvent, type ReactNode } from 'react'
import './composer.css'

export type ComposerMode = 'chat' | 'build'
export type ComposerEngineKind = 'subscription' | 'api' | 'local'
export type ComposerEngine = { id: string; label: string; kind: ComposerEngineKind; status: 'ready' | 'busy' | 'offline'; detail?: string }
export type ComposerCommand = { id: string; label: string; description: string; insert?: string; run?: () => void }
export type ComposerMention = { id: string; label: string; kind: 'flow' | 'note' | 'chat'; detail?: string }
export type ComposerAttachment = { id: string; file: File; preview?: string }
export type ComposerProps = {
  onSend: (text: string, attachments: ComposerAttachment[], engine: ComposerEngine, mode: ComposerMode) => void
  onStop?: () => void
  busy?: boolean
  engines: ComposerEngine[]
  engineId?: string
  onEngineChange?: (engine: ComposerEngine) => void
  mode?: ComposerMode
  onModeChange?: (mode: ComposerMode) => void
  commands: ComposerCommand[]
  searchMentions: (query: string) => Promise<ComposerMention[]>
  contextUsage?: { used: number; total: number }
  maxCharacters?: number
  maxAttachments?: number
  maxFileBytes?: number
  placeholder?: string
  className?: string
  footer?: ReactNode
}

const bytes = (n: number) => n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`
const statusLabel = (status: ComposerEngine['status']) => status === 'ready' ? 'Ready' : status === 'busy' ? 'In use' : 'Offline'

export function Composer(props: ComposerProps) {
  const { onSend, onStop, busy = false, engines, engineId, onEngineChange, mode = 'chat', onModeChange, commands, searchMentions, contextUsage, maxCharacters = 5000, maxAttachments = 8, maxFileBytes = 50 * 1024 * 1024, placeholder = 'Write a message…', className = '', footer } = props
  const [value, setValue] = useState('')
  const [files, setFiles] = useState<ComposerAttachment[]>([])
  const [menu, setMenu] = useState<'slash' | 'mention' | 'engine' | 'mode' | null>(null)
  const [query, setQuery] = useState('')
  const [mentions, setMentions] = useState<ComposerMention[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [engineLocal, setEngineLocal] = useState(engines.find(e => e.id === engineId) ?? engines[0])
  const [modeLocal, setModeLocal] = useState(mode)
  const area = useRef<HTMLTextAreaElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const menuRoot = useRef<HTMLDivElement>(null)
  const ime = useRef(false)
  const selectedEngine = engines.find(e => e.id === (engineId ?? engineLocal?.id)) ?? engineLocal ?? engines[0]
  const selectedMode = onModeChange ? mode : modeLocal
  const filteredCommands = useMemo(() => commands.filter(c => `${c.label} ${c.description}`.toLowerCase().includes(query.toLowerCase())), [commands, query])
  const choices = menu === 'slash' ? filteredCommands : menu === 'mention' ? mentions : []
  const hasImage = (file: File) => file.type.startsWith('image/')

  useEffect(() => {
    if (menu !== 'mention') return
    let current = true
    const timer = window.setTimeout(() => searchMentions(query).then(rows => { if (current) { setMentions(rows); setActiveIndex(0) } }).catch(() => { if (current) setMentions([]) }), 120)
    return () => { current = false; clearTimeout(timer) }
  }, [menu, query, searchMentions])

  useEffect(() => {
    const onOutside = (event: PointerEvent) => { if (menu && menuRoot.current && !menuRoot.current.contains(event.target as Node)) setMenu(null) }
    document.addEventListener('pointerdown', onOutside)
    return () => document.removeEventListener('pointerdown', onOutside)
  }, [menu])

  const resize = () => { const el = area.current; if (!el) return; el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 176)}px`; el.style.overflowY = el.scrollHeight > 176 ? 'auto' : 'hidden' }
  useEffect(resize, [value])

  const addFiles = (incoming: FileList | File[]) => {
    setError('')
    const accepted: ComposerAttachment[] = []
    for (const file of Array.from(incoming)) {
      if (file.size > maxFileBytes) { setError(`${file.name} is larger than ${bytes(maxFileBytes)}. Choose a smaller file.`); continue }
      if (files.length + accepted.length >= maxAttachments) { setError(`You can attach up to ${maxAttachments} files. Remove one to add another.`); break }
      accepted.push({ id: crypto.randomUUID(), file, ...(hasImage(file) ? { preview: URL.createObjectURL(file) } : {}) })
    }
    if (accepted.length) setFiles(current => [...current, ...accepted].slice(0, maxAttachments))
  }
  const removeFile = (id: string) => setFiles(current => { const item = current.find(x => x.id === id); if (item?.preview) URL.revokeObjectURL(item.preview); return current.filter(x => x.id !== id) })
  const send = () => {
    const text = value.trim()
    if ((!text && files.length === 0) || busy || value.length > maxCharacters || !selectedEngine) return
    onSend(text, files, selectedEngine, selectedMode)
    setValue(''); setFiles([]); setError(''); setMenu(null)
    requestAnimationFrame(resize)
  }
  const openTrigger = (which: 'engine' | 'mode') => { setMenu(menu === which ? null : which); setActiveIndex(0) }
  const selectChoice = (index: number) => {
    if (menu === 'slash') {
      const command = filteredCommands[index]
      if (!command) return
      command.run?.()
      if (command.insert) setValue(current => current.replace(/(?:^|\s)\/[^\s]*$/, match => `${match.startsWith(' ') ? ' ' : ''}${command.insert}`))
    } else if (menu === 'mention') {
      const mention = mentions[index]
      if (!mention) return
      setValue(current => current.replace(/(?:^|\s)@[^\s]*$/, match => `${match.startsWith(' ') ? ' ' : ''}@${mention.label} `))
    }
    setMenu(null); setQuery('')
    if (area.current) { area.current.focus(); area.current.setSelectionRange(area.current.value.length, area.current.value.length) }
  }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (ime.current || event.nativeEvent.isComposing) return
    if (menu === 'slash' || menu === 'mention') {
      if (event.key === 'ArrowDown') { event.preventDefault(); setActiveIndex(i => Math.min(i + 1, Math.max(choices.length - 1, 0))); return }
      if (event.key === 'ArrowUp') { event.preventDefault(); setActiveIndex(i => Math.max(0, i - 1)); return }
      if (event.key === 'Enter' && choices.length) { event.preventDefault(); selectChoice(activeIndex); return }
      if (event.key === 'Escape') { event.preventDefault(); setMenu(null); return }
    }
    if (event.key === 'Escape' && menu) { setMenu(null); return }
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() }
  }
  const onChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const next = event.target.value
    if (next.length > maxCharacters) { setValue(next); setError(`Messages can be up to ${maxCharacters.toLocaleString()} characters. Shorten it to send.`) }
    else {
      setValue(next); setError('')
      const match = next.match(/(?:^|\s)([\/@])([^\s]*)$/)
      if (match?.[1] === '/') { setMenu('slash'); setQuery(match[2]); setActiveIndex(0) }
      else if (match?.[1] === '@') { setMenu('mention'); setQuery(match[2]); setActiveIndex(0) }
      else if (menu === 'slash' || menu === 'mention') setMenu(null)
    }
  }
  const onPaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(event.clipboardData.items).filter(item => item.kind === 'file').map(item => item.getAsFile()).filter((f): f is File => !!f)
    if (items.length) { event.preventDefault(); addFiles(items) }
  }
  const onDrop = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); setDragging(false); if (event.dataTransfer.files.length) addFiles(event.dataTransfer.files) }

  return <div className={`dg-composer ${className}${dragging ? ' is-dragging' : ''}`} data-testid="composer" ref={menuRoot}
    onDragEnter={e => { e.preventDefault(); setDragging(true) }} onDragOver={e => e.preventDefault()} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false) }} onDrop={onDrop}>
    <input ref={fileInput} className="dg-file-input" type="file" multiple aria-label="Choose attachments" onChange={e => { if (e.target.files) addFiles(e.target.files); e.target.value = '' }} />
    {dragging && <div className="dg-drop-overlay" data-testid="composer-drop-zone"><span>Drop files to attach</span></div>}
    {(menu === 'slash' || menu === 'mention') && <div className="dg-popover dg-command-menu" role="listbox" aria-label={menu === 'slash' ? 'Commands' : 'Mentions'}>
      {menu === 'mention' && mentions.length === 0 ? <div className="dg-menu-empty">Searching flows, notes, and chats…</div> : choices.map((choice, index) => {
        const label = 'label' in choice ? choice.label : ''
        const description = 'description' in choice ? choice.description : choice.detail ?? choice.kind
        return <button type="button" role="option" aria-selected={index === activeIndex} className={`dg-menu-option${index === activeIndex ? ' is-active' : ''}`} key={choice.id} onMouseEnter={() => setActiveIndex(index)} onClick={() => selectChoice(index)}><span className="dg-option-title">{label}</span><span className="dg-option-detail">{description}</span></button>
      })}
      {menu === 'slash' && choices.length === 0 && <div className="dg-menu-empty">No matching commands</div>}
    </div>}
    {menu === 'engine' && <div className="dg-popover dg-picker" role="listbox" aria-label="Choose an engine">{engines.map(engine => <button type="button" role="option" aria-selected={engine.id === selectedEngine?.id} className="dg-menu-option" key={engine.id} onClick={() => { setEngineLocal(engine); onEngineChange?.(engine); setMenu(null) }}><i className={`dg-status-dot ${engine.status}`} /><span className="dg-option-main"><span className="dg-option-title">{engine.label}</span><span className="dg-option-detail">{engine.detail ?? statusLabel(engine.status)}</span></span><span className="dg-status-label">{statusLabel(engine.status)}</span></button>)}</div>}
    {menu === 'mode' && <div className="dg-popover dg-picker" role="listbox" aria-label="Choose a mode">{(['chat', 'build'] as const).map(item => <button type="button" role="option" aria-selected={selectedMode === item} className="dg-menu-option" key={item} onClick={() => { setModeLocal(item); onModeChange?.(item); setMenu(null) }}><span className="dg-option-main"><span className="dg-option-title">{item === 'chat' ? 'Chat' : 'Build interview'}</span><span className="dg-option-detail">{item === 'chat' ? 'Ask a question or explore an idea' : 'Shape a goal into a checked plan'}</span></span>{selectedMode === item && <span className="dg-check">✓</span>}</button>)}</div>}
    {files.length > 0 && <div className="dg-attachments" aria-label="Attachments">{files.map(item => <div className="dg-attachment" key={item.id}>{item.preview ? <img src={item.preview} alt={`Preview of ${item.file.name}`} /> : <span className="dg-file-glyph">▤</span>}<span className="dg-attachment-meta"><span className="dg-attachment-name" title={item.file.name}>{item.file.name}</span><span className="dg-attachment-size">{bytes(item.file.size)}</span></span><button type="button" className="dg-remove" aria-label={`Remove ${item.file.name}`} onClick={() => removeFile(item.id)}>×</button></div>)}</div>}
    <textarea ref={area} rows={1} value={value} onChange={onChange} onKeyDown={onKeyDown} onPaste={onPaste} onCompositionStart={() => { ime.current = true }} onCompositionEnd={() => { ime.current = false }} placeholder={placeholder} aria-label="Write a message" disabled={busy} />
    {error && <div className="dg-error" role="alert" data-testid="composer-error">{error}</div>}
    <div className="dg-composer-toolbar">
      <div className="dg-toolbar-left"><button type="button" className="dg-icon-button" aria-label="Attach files" title="Attach files" onClick={() => fileInput.current?.click()} disabled={busy}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 12-8.5 8.5a5 5 0 0 1-7-7L14 5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 8" /></svg></button>
        <div className="dg-trigger-wrap"><button type="button" className="dg-picker-trigger" aria-label={`Engine: ${selectedEngine?.label ?? 'Choose'}`} onClick={() => openTrigger('engine')}><i className={`dg-status-dot ${selectedEngine?.status ?? 'offline'}`} /><span>{selectedEngine?.label ?? 'Choose engine'}</span><span className="dg-chevron">⌄</span></button></div>
        <div className="dg-trigger-wrap"><button type="button" className="dg-picker-trigger" aria-label={`Mode: ${selectedMode === 'chat' ? 'Chat' : 'Build interview'}`} onClick={() => openTrigger('mode')}><span>{selectedMode === 'chat' ? 'Chat' : 'Build interview'}</span><span className="dg-chevron">⌄</span></button></div></div>
      <div className="dg-toolbar-right">{contextUsage && <div className="dg-context" aria-label={`Context ${Math.round(contextUsage.used / Math.max(contextUsage.total, 1) * 100)} percent used`}><span className="dg-context-track"><i style={{ width: `${Math.min(100, Math.max(0, contextUsage.used / Math.max(contextUsage.total, 1) * 100))}%` }} /></span><span>{Math.round(contextUsage.used / Math.max(contextUsage.total, 1) * 100)}% context</span></div>}{footer}<span className="dg-key-hint"><kbd>Enter</kbd> send <kbd>⇧ Enter</kbd> newline</span>
        {busy ? <button type="button" className="dg-stop-button" aria-label="Stop generating" onClick={onStop}>■ <span>Stop</span></button> : <button type="button" className="dg-send-button" aria-label="Send message" disabled={(!value.trim() && files.length === 0) || value.length > maxCharacters} onClick={send}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" /></svg></button>}</div>
    </div>
    <div className="dg-live-status" aria-live="polite">{value.length}/{maxCharacters} characters · {files.length}/{maxAttachments} attachments</div>
  </div>
}
