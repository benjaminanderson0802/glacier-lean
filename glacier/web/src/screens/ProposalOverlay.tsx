import { useState, type FormEvent } from 'react'
import type { ChatProposal } from '../api.ts'

type Props = {
  proposal: ChatProposal | null
  busy: boolean
  error: string
  saved: boolean
  runAvailable: boolean
  undoAvailable: boolean
  onPropose: (prompt: string) => void
  onRefine: (feedback: string) => void
  onAccept: () => void
  onDiscard: () => void
  onRun: () => void
  onUndo: () => void
}

export function ProposalOverlay({ proposal, busy, error, saved, runAvailable, undoAvailable, onPropose, onRefine, onAccept, onDiscard, onRun, onUndo }: Props) {
  const [prompt, setPrompt] = useState('')
  const [feedback, setFeedback] = useState('')
  const submitPrompt = (event: FormEvent) => {
    event.preventDefault()
    if (!prompt.trim() || busy) return
    onPropose(prompt.trim())
    setPrompt('')
  }
  const submitFeedback = (event: FormEvent) => {
    event.preventDefault()
    if (!feedback.trim() || busy) return
    onRefine(feedback.trim())
    setFeedback('')
  }
  return <section className={`proposal-overlay${proposal ? ' has-proposal' : ''}`} data-testid="proposal-overlay">
    {!proposal && <form className="proposal-prompt" onSubmit={submitPrompt}>
      <label htmlFor="watch-build-prompt">What would you like Glacier to build?</label>
      <textarea id="watch-build-prompt" data-testid="watch-build-prompt" value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Describe the task in your own words" />
      <button type="submit" className="primary" data-testid="watch-build-send" disabled={busy || !prompt.trim()}>{busy ? 'thinking…' : 'propose a flow'}</button>
      {error && <p role="alert">{error}</p>}
    </form>}
    {proposal && <>
      <div className="proposal-title-row">
        <div><strong data-testid="proposal-summary">{proposal.explanation || `A flow for ${proposal.flow?.goal || proposal.flow?.name || 'your request'}`}</strong>
          <div className="proposal-caption">{proposal.flow?.goal || 'Review the proposed steps, then accept or refine.'}</div>
        </div>
        {saved && <span data-testid="proposal-saved">saved</span>}
      </div>
      {!saved && <>
        <form className="proposal-refine" onSubmit={submitFeedback}>
          <input data-testid="proposal-refine-input" aria-label="What should Glacier change?" value={feedback} onChange={event => setFeedback(event.target.value)} placeholder="What should Glacier change?" />
          <button type="submit" data-testid="proposal-refine" disabled={busy || !feedback.trim()}>{busy ? 'updating…' : 'refine'}</button>
        </form>
        <div className="proposal-actions">
          <button type="button" className="primary" data-testid="proposal-accept" disabled={busy} onClick={onAccept}>accept and build</button>
          <button type="button" className="ghost" data-testid="proposal-discard" disabled={busy} onClick={onDiscard}>discard</button>
        </div>
      </>}
      {runAvailable && <button type="button" className="run" data-testid="watch-build-run-once" disabled={busy} onClick={onRun}>run it once</button>}
      {undoAvailable && <button type="button" className="ghost" data-testid="proposal-undo" disabled={busy} onClick={onUndo}>undo save</button>}
      {error && <p role="alert">{error}</p>}
    </>}
  </section>
}
