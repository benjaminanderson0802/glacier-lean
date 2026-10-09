import { useState } from 'react'
import { Markdown } from './Markdown.tsx'
import { ToolCard } from './ToolCard.tsx'
import { ApprovalCard } from './ApprovalCard.tsx'
import { ChoiceCard } from './ChoiceCard.tsx'

export type ThreadMessageData = {
  id: string
  role: 'user' | 'assistant'
  text: string
  chunks?: string[]
  streaming?: boolean
  timestamp?: string
  choices?: string[]
  approval?: { title: string; detail?: string; status?: 'pending' | 'approved' | 'rejected' }
  tools?: Array<{ id: string; name: string; status: 'running' | 'ok' | 'failed'; duration?: string; output?: string }>
}

type Props = {
  message: ThreadMessageData
  onChoice?: (choice: string, message: ThreadMessageData) => void
  onApprove?: (message: ThreadMessageData, reason: string) => void
  onReject?: (message: ThreadMessageData, reason: string) => void
  onCopy?: (message: ThreadMessageData) => void
  onEdit?: (message: ThreadMessageData) => void
  onRegenerate?: (message: ThreadMessageData) => void
  onBranch?: (message: ThreadMessageData) => void
}

export function Message({ message, onChoice, onApprove, onReject, onCopy, onEdit, onRegenerate, onBranch }: Props) {
  const [copied, setCopied] = useState(false)
  const own = message.role === 'user'
  const copy = async () => {
    await navigator.clipboard.writeText(message.text).catch(() => {})
    setCopied(true); onCopy?.(message); setTimeout(() => setCopied(false), 1300)
  }
  return <article className={`thread-message ${own ? 'is-user' : 'is-assistant'}`} data-testid="thread-message" data-message-id={message.id}>
    <div className="thread-message-row">
      <div className="thread-message-content">
        {!own && <div className="thread-message-author"><span className="thread-mark" aria-hidden="true">✧</span><span>Glacier</span><span className="thread-author-detail">Interviewer</span></div>}
        <div className="thread-message-text">
          {message.chunks?.length && message.streaming ? message.chunks.map((chunk, i) => <span className="thread-chunk" key={`${message.id}-${i}`}>{chunk}</span>) : <Markdown source={message.text} />}
          {message.streaming && <span className="thread-caret" aria-label="Writing" />}
        </div>
        {message.timestamp && <time className="thread-time">{message.timestamp}</time>}
        <div className="thread-message-actions" role="toolbar" aria-label="Message actions">
          <button type="button" aria-label="Copy message" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
          {own ? <button type="button" aria-label="Edit and resend" onClick={() => onEdit?.(message)}>Edit &amp; resend</button> : <>
            <button type="button" aria-label="Regenerate response" onClick={() => onRegenerate?.(message)}>Regenerate</button>
            <button type="button" aria-label="Branch from here" onClick={() => onBranch?.(message)}>Branch</button>
          </>}
        </div>
        {message.choices?.length ? <ChoiceCard question="Choose one option" choices={message.choices} onSelect={choice => onChoice?.(choice, message)} /> : null}
        {message.approval && <ApprovalCard title={message.approval.title} detail={message.approval.detail} status={message.approval.status} onApprove={value => onApprove?.(message, value)} onReject={value => onReject?.(message, value)} />}
        {message.tools?.map(tool => <ToolCard key={tool.id} {...tool} />)}
      </div>
    </div>
  </article>
}
