import { useState } from 'react'
import { Thread, type ThreadMessageData } from './Thread.tsx'
import './thread.css'
import '../../theme/deep-glacier-tokens.css'

const initial: ThreadMessageData[] = [
  { id: 'user-1', role: 'user', text: 'I want a simple system that turns campaign footage into polished clips, checks the rules, and tracks how each one performs.', timestamp: '10:42 AM' },
  { id: 'assistant-1', role: 'assistant', timestamp: '10:42 AM', text: [
    '## A conversation that keeps its shape', '',
    'That gives us a clear loop: **prepare, check, publish, learn**. I’ll keep every publish action behind your approval.', '',
    '> We can start with footage you already have, then add connected sources later.', '',
    '| Step | What happens |', '| --- | --- |', '| Prepare | Select an approved clip |', '| Check | Confirm it meets campaign rules |', '',
    'The workflow uses `local files` and [your campaign guide](https://example.org/guide).', '',
    '```typescript', 'const clip = await prepare(source)', 'const approved = await checkRules(clip)', 'if (approved) await requestApproval(clip)', '```',
  ].join('\n'),
    tools: [{ id: 'tools-1', name: 'Checked connected tools', status: 'ok', duration: '2.4 s', output: 'clip-library      ready\ncampaign-guide    ready\npost-scheduler    needs approval' }] },
  { id: 'assistant-2', role: 'assistant', text: 'Which source should we use first?', choices: ['Campaign asset packs', 'A folder I fill', 'Licensed channels', 'Mix — I’ll explain'], timestamp: '10:43 AM' },
  { id: 'assistant-3', role: 'assistant', text: 'Before any clip is published, the system will ask you to review the result.', approval: { title: 'Allow clip publishing', detail: 'Glacier will show the clip and destination before anything is posted.' }, timestamp: '10:43 AM' },
]

export function GalleryThread() {
  const [messages, setMessages] = useState(initial)
  const [generating, setGenerating] = useState(false)
  const [toast, setToast] = useState('')
  const [draft, setDraft] = useState('')
  const notice = (value: string) => { setToast(value); setTimeout(() => setToast(''), 1800) }
  const simulate = () => {
    if (generating) return
    const id = `stream-${Date.now()}`
    const item: ThreadMessageData = { id, role: 'assistant', text: '', chunks: [], streaming: true }
    setMessages(current => [...current, item]); setGenerating(true)
    const chunks = ['I checked the three steps. ', 'The source can stay on your computer, ', 'and publishing will wait for your approval.']
    chunks.forEach((chunk, index) => setTimeout(() => setMessages(current => current.map(message => message.id === id ? { ...message, text: message.text + chunk, chunks: [...(message.chunks ?? []), chunk], streaming: index < chunks.length - 1 } : message)), (index + 1) * 550))
    setTimeout(() => setGenerating(false), chunks.length * 550 + 30)
  }
  const act = (name: string) => notice(name)
  return <main className="gallery-thread-page" data-testid="thread-gallery">
    <header className="gallery-thread-header"><div className="gallery-brand"><span className="gallery-brand-mark">✧</span><strong>Glacier</strong><span className="gallery-separator">/</span><span>Build</span></div><div className="gallery-title"><h1>Clip campaign loop</h1><span>Interview · 3 of ~6</span></div><button type="button" onClick={() => setMessages(Array.from({ length: 1000 }, (_, i) => ({ id: `long-${i}`, role: i % 2 ? 'assistant' as const : 'user' as const, text: `Conversation message ${i + 1}. The thread stays responsive as earlier messages move out of view.` })))} data-testid="load-long-thread">Load 1,000 messages</button><button type="button" onClick={simulate} data-testid="stream-demo">Simulate a reply</button></header>
    <section className="gallery-thread-main"><div className="gallery-thread-meta"><span className="gallery-dot" /> Ready to help <span className="gallery-meta-divider">·</span> Codex</div>
      <Thread messages={messages} isGenerating={generating} onStop={() => { setGenerating(false); setMessages(current => current.map(message => message.streaming ? { ...message, streaming: false } : message)); notice('Reply stopped') }}
        onChoice={choice => { setMessages(current => [...current, { id: `choice-${Date.now()}`, role: 'user', text: choice }]); notice('Choice sent') }}
        onApprove={(message, reason) => setMessages(current => current.map(item => item.id === message.id ? { ...item, approval: { ...item.approval!, status: 'approved', detail: reason ? `${item.approval!.detail} Reason: ${reason}` : item.approval!.detail } } : item))}
        onReject={(message, reason) => setMessages(current => current.map(item => item.id === message.id ? { ...item, approval: { ...item.approval!, status: 'rejected', detail: reason ? `${item.approval!.detail} Reason: ${reason}` : item.approval!.detail } } : item))}
        onCopy={() => notice('Message copied')}
        onEdit={message => { setDraft(message.text); notice('Edit this message, then send it again') }}
        onRegenerate={() => act('A new reply is ready')}
        onBranch={() => act('Started a new branch from this reply')}
        onSuggestion={suggestion => { setDraft(suggestion); act('Suggestion added to your message') }} />
      <div className="gallery-composer"><textarea aria-label="Write a message" placeholder="Answer, or add details…" value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (draft.trim()) { setMessages(current => [...current, { id: `typed-${Date.now()}`, role: 'user', text: draft }]); setDraft('') } } }} />
        <div className="gallery-composer-footer"><span>Enter to send <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line</span><button type="button" aria-label="Send message" disabled={!draft.trim()} onClick={() => { setMessages(current => [...current, { id: `typed-${Date.now()}`, role: 'user', text: draft }]); setDraft('') }}>↑</button></div>
      </div>
    </section>
    {toast && <div role="status" className="gallery-toast">{toast}</div>}
  </main>
}
