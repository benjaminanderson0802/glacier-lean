import { useEffect, useMemo, useRef, useState } from 'react'
import { Message, type ThreadMessageData } from './Message.tsx'
import './thread.css'
import '../../theme/deep-glacier-tokens.css'

export type ThreadProps = {
  messages: ThreadMessageData[]
  isGenerating?: boolean
  onChoice?: (choice: string, message: ThreadMessageData) => void
  onApprove?: (message: ThreadMessageData, reason: string) => void
  onReject?: (message: ThreadMessageData, reason: string) => void
  onCopy?: (message: ThreadMessageData) => void
  onEdit?: (message: ThreadMessageData) => void
  onRegenerate?: (message: ThreadMessageData) => void
  onBranch?: (message: ThreadMessageData) => void
  onStop?: () => void
  onSuggestion?: (suggestion: string) => void
}

const suggestions = ['Help me plan a project', 'Summarize a long document', 'Build a personal workflow']
const ESTIMATED_HEIGHT = 150

export function Thread(props: ThreadProps) {
  const { messages, isGenerating = false } = props
  const log = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportHeight, setViewportHeight] = useState(640)
  const [showLatest, setShowLatest] = useState(false)
  const [measureVersion, setMeasureVersion] = useState(0)
  const measured = useRef(new Map<string, number>())
  const end = useRef<HTMLDivElement>(null)
  const virtual = messages.length > 100
  const offsets = useMemo(() => {
    const list = [0]
    for (const message of messages) list.push(list[list.length - 1] + (measured.current.get(message.id) ?? ESTIMATED_HEIGHT))
    return list
  }, [messages, measureVersion])
  let firstVisible = 0
  while (firstVisible < messages.length - 1 && offsets[firstVisible + 1] < scrollTop) firstVisible++
  const start = virtual ? Math.max(0, firstVisible - 2) : 0
  let lastVisible = firstVisible
  while (lastVisible < messages.length && offsets[lastVisible] < scrollTop + viewportHeight) lastVisible++
  const endIndex = virtual ? Math.min(messages.length, lastVisible + 2) : messages.length
  const visible = messages.slice(start, endIndex)

  useEffect(() => {
    const node = log.current
    if (!node) return
    const resize = () => setViewportHeight(node.clientHeight)
    resize()
    const observer = new ResizeObserver(resize); observer.observe(node)
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    if (!virtual || !log.current) return
    const observers: ResizeObserver[] = []
    for (const node of Array.from(log.current.querySelectorAll<HTMLElement>('[data-virtual-id]'))) {
      const id = node.dataset.virtualId
      if (!id) continue
      const observer = new ResizeObserver(entries => {
        const height = Math.ceil(entries[0]?.contentRect.height ?? 0)
        if (!height) return
        const previous = measured.current.get(id) ?? ESTIMATED_HEIGHT
        if (Math.abs(previous - height) > 1) {
          measured.current.set(id, height)
          setMeasureVersion(version => version + 1)
        }
      })
      observer.observe(node); observers.push(observer)
    }
    return () => observers.forEach(observer => observer.disconnect())
  }, [virtual, start, endIndex, messages.length])
  useEffect(() => {
    if (!showLatest) end.current?.scrollIntoView({ block: 'end' })
  }, [messages.length, messages[messages.length - 1]?.text, measureVersion])

  const scroll = () => {
    const node = log.current
    if (!node) return
    setScrollTop(node.scrollTop)
    setShowLatest(node.scrollHeight - node.scrollTop - node.clientHeight > 100)
  }
  const latest = () => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); setShowLatest(false) }

  return <section className="thread-shell" data-testid="thread" aria-label="Conversation">
    <div className="thread-log" ref={log} onScroll={scroll} data-testid="thread-log" role="log" aria-live="polite">
      {messages.length === 0 ? <div className="thread-empty" data-testid="thread-empty">
        <div className="thread-empty-orb" aria-hidden="true">✧</div><h2>Where should we start?</h2><p>Tell Glacier what you want to work on. You can add details as we go.</p>
        <div className="thread-suggestions">{suggestions.map(s => <button type="button" key={s} onClick={() => props.onSuggestion?.(s)}>{s}<span>↗</span></button>)}</div>
      </div> : <>
        {virtual && <div className="thread-spacer" aria-hidden="true" data-height={offsets[start]} />}
        {visible.map((message, index) => <div className="thread-virtual-row" key={message.id} data-virtual-id={message.id} data-message-index={start + index}><Message message={message} onChoice={props.onChoice} onApprove={props.onApprove} onReject={props.onReject} onCopy={props.onCopy} onEdit={props.onEdit} onRegenerate={props.onRegenerate} onBranch={props.onBranch} /></div>)}
        {virtual && <div className="thread-spacer" aria-hidden="true" data-height={offsets[messages.length] - offsets[endIndex]} />}
      </>}
      <div ref={end} />
    </div>
    {showLatest && <button type="button" className="thread-latest" onClick={latest} aria-label="Jump to latest">↓ <span>Jump to latest</span></button>}
    {isGenerating && <button type="button" className="thread-stop" onClick={props.onStop}>Stop generating <span aria-hidden="true">■</span></button>}
  </section>
}

export { Message } from './Message.tsx'
export { Markdown } from './Markdown.tsx'
export { ToolCard } from './ToolCard.tsx'
export { ChoiceCard } from './ChoiceCard.tsx'
export { ApprovalCard } from './ApprovalCard.tsx'
export type { ThreadMessageData } from './Message.tsx'
