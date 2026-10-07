import { useEffect, useRef, useState } from 'react'
import { applyProposal, chat, type ChatProposal, type ProposalCheck } from '../api.ts'
import { Btn, PageHead, Panel } from '../ui/kit.tsx'
import { Icon, Mascot } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { setDraft } from '../draft.ts'
import type { Environment } from '../api.ts'

type Msg = { who: 'you' | 'glacier'; text: string; at: Date; proposal?: ChatProposal; state?: 'open' | 'approved' | 'rejected'; error?: boolean }

// Conversation lives for the app session (module scope), so switching tabs does not lose it.
let saved: { conv: string | null; msgs: Msg[] } = { conv: null, msgs: [] }

const time = (d: Date) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

// How a proposed automation will be checked, in plain words (shown before anything runs).
const checkText = (c: ProposalCheck) =>
  c.kind === 'command' ? `Glacier runs a check: ${c.cmd ?? ''}`
    : c.kind === 'rubric' ? `An independent reviewer checks: ${c.rubric ?? ''}`
    : c.kind === 'human' ? `You confirm: ${c.question ?? 'Is it done?'}`
    : c.kind === 'schema' ? 'The result must match the expected format'
    : 'A check confirms it is done'

export function AskScreen() {
  const [msgs, setMsgs] = useState<Msg[]>(saved.msgs)
  const [conv, setConv] = useState<string | null>(saved.conv)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { saved = { conv, msgs }; end.current?.scrollIntoView({ block: 'end' }) }, [msgs, conv])

  const send = async () => {
    const m = text.trim()
    if (!m || busy) return
    setText(''); setBusy(true)
    const id = conv ?? crypto.randomUUID()
    setConv(id)
    setMsgs(x => [...x, { who: 'you', text: m, at: new Date() }, { who: 'glacier', text: '', at: new Date() }])
    const patch = (f: (g: Msg) => Msg) => setMsgs(x => [...x.slice(0, -1), f(x[x.length - 1])])
    try {
      await chat(m, id, ev => {
        if (ev.type === 'text') patch(g => ({ ...g, text: g.text + ev.delta }))
        else if (ev.type === 'proposal') patch(g => ({ ...g, proposal: ev.proposal, state: 'open' }))
        else if (ev.type === 'error') patch(g => ({ ...g, text: ev.message, error: true }))
      })
    } catch (e) {
      patch(g => ({ ...g, text: `Could not reach the assistant (${String(e)}).`, error: true }))
    } finally { setBusy(false) }
  }

  const decide = async (i: number, approve: boolean) => {
    const p = msgs[i].proposal!
    try {
      await applyProposal(p.id, approve)
      setMsgs(x => x.map((m, j) => j === i ? { ...m, state: approve ? 'approved' : 'rejected' } : m))
      if (approve && p.flow?.id) go(`automations/build/${p.flow.id}`)
    } catch (e) {
      setMsgs(x => [...x, { who: 'glacier', text: String(e), at: new Date(), error: true }])
    }
  }

  const edit = async (i: number) => {
    const p = msgs[i].proposal!
    const flow = (p.flow ?? {}) as Environment & Record<string, unknown>
    const name = String(flow.name ?? flow.id ?? 'New automation')
    setDraft({ ...flow, id: String(flow.id ?? ''), name, nodes: (flow.nodes ?? []) as Environment['nodes'], edges: (flow.edges ?? []) as Environment['edges'] })
    applyProposal(p.id, false).catch(() => {})  // the edited copy replaces the proposal
    setMsgs(x => x.map((m, j) => j === i ? { ...m, state: 'rejected', text: m.text } : m))
    go(`automations/new/${encodeURIComponent(name)}`)
  }

  return (
    <>
      <PageHead title="Ask" sub="Talk to your assistant." />
      <Panel className="g-chat" testid="chat">
        <div className="g-chat-log" data-testid="chat-log">
          {msgs.length === 0 && <div className="g-empty">Ask a question, or describe something you want done regularly. Glacier will propose an automation for you to approve.</div>}
          {msgs.map((m, i) => (
            <div key={i} className={`g-msg ${m.who}`} data-testid={`msg-${i}`}>
              <div className="g-msg-av">{m.who === 'glacier' ? <Mascot px={2} /> : <span className="g-you">You</span>}</div>
              <div className="g-msg-body">
                <div className="g-msg-head"><span className="g-lead">{m.who === 'you' ? 'You' : 'Glacier'}</span><span className="g-muted">{time(m.at)}</span></div>
                <div className={m.error ? 'g-error' : ''}>{m.text || (busy && i === msgs.length - 1 ? '…' : '')}</div>
                {m.proposal && (
                  <div className="g-proposal" data-testid="proposal">
                    <div className="g-proposal-head"><Icon name="automations" /><span className="g-lead">{m.proposal.flow?.name ?? m.proposal.flow?.id ?? 'New automation'}</span>
                      <span className={`g-chip ${m.state === 'approved' ? 'ok' : m.state === 'rejected' ? 'bad' : ''}`}>{m.state === 'approved' ? 'Approved' : m.state === 'rejected' ? 'Rejected' : 'Proposed'}</span></div>
                    {m.proposal.explanation && <div className="g-detail">{m.proposal.explanation}</div>}
                    {m.proposal.flow?.goal && <div className="g-detail" data-testid="proposal-goal">Goal: {m.proposal.flow.goal}</div>}
                    <div className="g-muted">Steps: {m.proposal.flow?.nodes?.length ?? 0}</div>
                    {(m.proposal.flow?.acceptance?.length ?? 0) > 0 && (
                      <div data-testid="proposal-checks">
                        <div className="g-muted">How Glacier will know it is done:</div>
                        <ul className="g-bullets">{m.proposal.flow!.acceptance!.map((c, j) => <li key={j}>{checkText(c)}</li>)}</ul>
                      </div>
                    )}
                    {m.state === 'open' && (
                      <div className="g-actions">
                        <Btn primary onClick={() => decide(i, true)} data-testid="proposal-approve">Approve</Btn>
                        <Btn onClick={() => edit(i)} data-testid="proposal-edit">Edit</Btn>
                        <Btn onClick={() => decide(i, false)} data-testid="proposal-reject">Reject</Btn>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={end} />
        </div>
        <form className="g-composer" onSubmit={e => { e.preventDefault(); send() }}>
          <input className="g-input" placeholder="Type a message…" value={text} onChange={e => setText(e.target.value)} data-testid="chat-input" disabled={busy} />
          <button className="g-btn primary g-send" type="submit" aria-label="Send" disabled={busy || !text.trim()} data-testid="chat-send"><Icon name="send" /></button>
        </form>
      </Panel>
    </>
  )
}
