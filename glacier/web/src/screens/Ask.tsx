import { useEffect, useRef, useState } from 'react'
import { ago, api, applyProposal, chat, conversationsApi, type ChatProposal, type ConversationItem, type ProposalCheck } from '../api.ts'
import { Btn, Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { Icon, Logo } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { setDraft } from '../draft.ts'
import type { Environment } from '../api.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'

type Msg = { who: 'you' | 'glacier'; text: string; at: Date; proposal?: ChatProposal; state?: 'open' | 'approved' | 'rejected'; error?: boolean; run?: { id: string; env: string; status: string } }

// Conversation lives for the app session (module scope), so switching tabs does not lose it.
let saved: { conv: string | null; msgs: Msg[]; title: string } = { conv: null, msgs: [], title: '' }

const time = (d: Date) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

// How a proposed automation will be checked, in plain words (shown before anything runs).
const checkText = (c: ProposalCheck) =>
  c.kind === 'command' ? t('ask.commandCheck', { value: c.cmd ?? '' })
    : c.kind === 'rubric' ? t('ask.rubricCheck', { value: c.rubric ?? '' })
    : c.kind === 'human' ? t('ask.humanCheck', { value: c.question ?? t('ask.defaultQuestion') })
    : c.kind === 'schema' ? t('ask.schemaCheck')
    : t('ask.genericCheck')

export function AskScreen() {
  const [msgs, setMsgs] = useState<Msg[]>(saved.msgs)
  const [conv, setConv] = useState<string | null>(saved.conv)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [title, setTitle] = useState(saved.title)
  const [view, setView] = useState<'chat' | 'past'>('chat')
  const [past, setPast] = useState<ConversationItem[] | null>(null)
  const [q, setQ] = useState('')
  const [renaming, setRenaming] = useState<string | null>(null)
  const [err, setErr] = useState('')
  const [deleteUndo, setDeleteUndo] = useState<UndoAction | null>(null)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { saved = { conv, msgs, title }; end.current?.scrollIntoView({ block: 'end' }) }, [msgs, conv, title])
  useEffect(() => {
    if (view !== 'past') return
    const t = setTimeout(() => conversationsApi.list(q).then(setPast).catch(e => setErr(String(e))), q ? 250 : 0)
    return () => clearTimeout(t)
  }, [view, q])

  const reopen = async (id: string) => {
    try {
      const c = await conversationsApi.get(id)
      setMsgs(c.messages.map(m => ({ who: m.who, text: m.text, at: new Date(m.at) })))
      setConv(c.id); setTitle(c.title); setRenaming(null); setErr(''); setView('chat')
    } catch (e) { setErr(String(e)) }
  }
  const fresh = () => { setMsgs([]); setConv(null); setTitle(''); setRenaming(null); setView('chat') }
  const rename = async () => {
    if (!conv || renaming === null) return
    try { const r = await conversationsApi.rename(conv, renaming); setTitle(r.title); setRenaming(null); setErr('') }
    catch (e) { setErr(String(e)) }
  }

  const send = async () => {
    const m = text.trim()
    if (!m || busy) return
    setText(''); setBusy(true)
    const id = conv ?? crypto.randomUUID()
    setConv(id)
    if (!title) setTitle(m.replace(/\s+/g, ' ').slice(0, 60))
    setMsgs(x => [...x, { who: 'you', text: m, at: new Date() }, { who: 'glacier', text: '', at: new Date() }])
    const patch = (f: (g: Msg) => Msg) => setMsgs(x => [...x.slice(0, -1), f(x[x.length - 1])])
    try {
      await chat(m, id, ev => {
        if (ev.type === 'text') patch(g => ({ ...g, text: g.text + ev.delta }))
        else if (ev.type === 'proposal') patch(g => ({ ...g, proposal: ev.proposal, state: 'open' }))
        else if (ev.type === 'error') patch(g => ({ ...g, text: ev.message, error: true }))
      })
    } catch (e) {
      patch(g => ({ ...g, text: t('ask.assistantError', { error: String(e) }), error: true }))
    } finally { setBusy(false) }
  }

  // Follow a run started from this chat until it finishes, then show its plain-language result.
  const follow = (i: number, runId: string, env: string) => {
    const tick = async () => {
      const r = await api.getRun(runId).catch(() => null)
      const status = r?.status ?? 'running'
      setMsgs(x => x.map((m, j) => j === i ? { ...m, run: { id: runId, env, status } } : m))
      if (['running', 'waiting', 'pending'].includes(status)) { setTimeout(tick, 1500); return }
      const id = conv
      if (id) conversationsApi.get(id).then(c => {
        const last = c.messages[c.messages.length - 1]
        if (last && last.who === 'glacier') setMsgs(x => x.some(m => m.text === last.text) ? x : [...x, { who: 'glacier', text: last.text, at: new Date(last.at) }])
      }).catch(() => {})
    }
    tick()
  }

  const decide = async (i: number, approve: boolean, runNow = false) => {
    const p = msgs[i].proposal!
    try {
      const r = await applyProposal(p.id, approve, runNow)
      setMsgs(x => x.map((m, j) => j === i ? { ...m, state: approve ? 'approved' : 'rejected' } : m))
      if (approve && r.run_id && p.flow?.id) follow(i, r.run_id, p.flow.id)
      else if (approve && p.flow?.id && !p.run_existing) go(`automations/build/${p.flow.id}`)
    } catch (e) {
      setMsgs(x => [...x, { who: 'glacier', text: String(e), at: new Date(), error: true }])
    }
  }

  const edit = async (i: number) => {
    const p = msgs[i].proposal!
    const flow = (p.flow ?? {}) as Environment & Record<string, unknown>
    const name = String(flow.name ?? flow.id ?? t('ask.newAutomation'))
    setDraft({ ...flow, id: String(flow.id ?? ''), name, nodes: (flow.nodes ?? []) as Environment['nodes'], edges: (flow.edges ?? []) as Environment['edges'] })
    applyProposal(p.id, false).catch(() => {})  // the edited copy replaces the proposal
    setMsgs(x => x.map((m, j) => j === i ? { ...m, state: 'rejected', text: m.text } : m))
    go(`automations/new/${encodeURIComponent(name)}`)
  }

  return (
    <>
      <PageHead title={t('ask.title')} side={
        <div className="g-seg" data-testid="ask-views">
          <button className={`g-seg-btn${view === 'chat' ? ' active' : ''}`} onClick={() => setView('chat')} data-testid="askview-chat">{t('ask.chat')}</button>
          <button className={`g-seg-btn${view === 'past' ? ' active' : ''}`} onClick={() => setView('past')} data-testid="askview-past">{t('ask.pastChats')}</button>
        </div>} />
      {err && <div className="g-error">{err}</div>}
      <DeleteUndo action={deleteUndo} onDone={() => setDeleteUndo(null)} onError={e => setErr(String(e))} />
      {view === 'past' ? (
        <Panel title={t('ask.pastChats')} aside={<input className="g-input" style={{ width: 220 }} placeholder={t('ask.search')} value={q} onChange={e => setQ(e.target.value)} data-testid="past-search" />} testid="past-chats" className="g-scroll">
          <div className="g-rows">
            {(past ?? []).map(c => <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ flex: 1 }}><Row icon="ask" lead={c.title} detail={`${c.messages} message${c.messages === 1 ? '' : 's'}`} when={c.updated ? ago(c.updated) : undefined} onClick={() => reopen(c.id)} testid={`past-${c.id}`} /></div><DeleteAction label={t('ask.deleteConversation')} impact={t('delete.conversationImpact')} testid={`conversation-delete-${c.id}`}
              onDelete={async () => { const result = await conversationsApi.delete(c.id); return { title: t('delete.removed'), run: async () => { await conversationsApi.undoDelete(c.id, result.commit); setPast(await conversationsApi.list(q)) } } }}
              onDeleted={action => { setDeleteUndo(action ?? null); setPast(current => current?.filter(item => item.id !== c.id) ?? null); if (conv === c.id) { saved = { conv: null, msgs: [], title: '' }; setConv(null); setMsgs([]); setTitle('') } }}
              onError={e => setErr(String(e))} /></div>)}
            {past && past.length === 0 && <Empty>{q ? t('ask.noMatches') : t('ask.noPast')}</Empty>}
          </div>
        </Panel>
      ) : (
      <Panel className="g-chat" testid="chat">
        {conv && (
          <div className="g-chat-title" data-testid="chat-title">
            {renaming === null ? (
              <><span className="g-lead">{title || t('ask.thisChat')}</span>
                <button className="g-link" onClick={() => setRenaming(title)} data-testid="chat-rename">{t('ask.rename')}</button>
                <button className="g-link" onClick={fresh} data-testid="chat-new">{t('ask.newChat')}</button></>
            ) : (
              <form onSubmit={e => { e.preventDefault(); rename() }} style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1 }}>
                <input className="g-input" style={{ flex: 1 }} value={renaming} maxLength={80} onChange={e => setRenaming(e.target.value)} data-testid="chat-rename-input" autoFocus />
                <Btn primary type="submit" disabled={!renaming.trim()} data-testid="chat-rename-save">{t('ask.save')}</Btn>
                <Btn onClick={() => setRenaming(null)}>{t('ask.cancel')}</Btn>
              </form>
            )}
          </div>
        )}
        <div className="g-chat-log" data-testid="chat-log">
          {msgs.length === 0 && <div className="g-empty">{t('ask.empty')}</div>}
          {msgs.map((m, i) => (
            <div key={i} className={`g-msg ${m.who}`} data-testid={`msg-${i}`}>
              <div className="g-msg-av">{m.who === 'glacier' ? <Logo px={1} /> : <span className="g-you">{t('ask.you')}</span>}</div>
              <div className="g-msg-body">
                <div className="g-msg-head"><span className="g-lead">{m.who === 'you' ? t('ask.you') : t('pixel.glacier')}</span><span className="g-muted">{time(m.at)}</span></div>
                <div className={m.error ? 'g-error' : ''}>{m.text || (busy && i === msgs.length - 1 ? '…' : '')}</div>
                {m.proposal && (
                  <div className="g-proposal" data-testid="proposal">
                    <div className="g-proposal-head"><Icon name="automations" /><span className="g-lead">{m.proposal.flow?.name ?? m.proposal.flow?.id ?? t('ask.newAutomation')}</span>
                      <span className={`g-chip ${m.state === 'approved' ? 'ok' : m.state === 'rejected' ? 'bad' : ''}`}>{m.state === 'approved' ? t('ask.approved') : m.state === 'rejected' ? t('ask.rejected') : t('ask.proposed')}</span></div>
                    {m.proposal.explanation && <div className="g-detail">{m.proposal.explanation}</div>}
                    {m.proposal.flow?.goal && <div className="g-detail" data-testid="proposal-goal">{t('ask.goal', { goal: m.proposal.flow.goal })}</div>}
                    {!m.proposal.run_existing && <div className="g-muted">{t('ask.steps', { count: m.proposal.flow?.nodes?.length ?? 0 })}</div>}
                    {(m.proposal.flow?.acceptance?.length ?? 0) > 0 && (
                      <div data-testid="proposal-checks">
                        <div className="g-muted">{t('ask.checkHeading')}</div>
                        <ul className="g-bullets">{m.proposal.flow!.acceptance!.map((c, j) => <li key={j}>{checkText(c)}</li>)}</ul>
                      </div>
                    )}
                    {m.state === 'open' && (m.proposal.run_existing ? (
                      <div className="g-actions">
                        <Btn primary onClick={() => decide(i, true, true)} data-testid="proposal-run">{t('ask.runNow')}</Btn>
                        <Btn onClick={() => decide(i, false)} data-testid="proposal-reject">{t('ask.notNow')}</Btn>
                      </div>
                    ) : (
                      <div className="g-actions">
                        <Btn primary onClick={() => decide(i, true)} data-testid="proposal-approve">{t('ask.approve')}</Btn>
                        <Btn onClick={() => decide(i, true, true)} data-testid="proposal-approve-run">{t('ask.approveAndRun')}</Btn>
                        <Btn onClick={() => edit(i)} data-testid="proposal-edit">{t('ask.edit')}</Btn>
                        <Btn onClick={() => decide(i, false)} data-testid="proposal-reject">{t('ask.reject')}</Btn>
                      </div>
                    ))}
                    {m.run && (
                      <div className="g-detail" data-testid="proposal-run-status">
                        {['running', 'waiting', 'pending'].includes(m.run.status) ? t('ask.runRunning') : t('ask.runFinished', { status: m.run.status })}{' '}
                        <button className="g-link" onClick={() => go(`automations/flow/${m.run!.env}/${m.run!.id}`)} data-testid="proposal-view-run">{t('ask.viewRun')}</button>
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
          <input className="g-input" placeholder={t('ask.input')} value={text} onChange={e => setText(e.target.value)} data-testid="chat-input" disabled={busy} />
          <button className="g-btn primary g-send" type="submit" aria-label={t('ask.send')} disabled={busy || !text.trim()} data-testid="chat-send"><Icon name="send" /></button>
        </form>
      </Panel>
      )}
    </>
  )
}
