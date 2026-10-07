// Claims: problems the AI could not solve alone, waiting for the owner (mockup panel 3).
import { useEffect, useState } from 'react'
import { ago, claimsApi, sections, type ClaimFull, type ClaimSummary } from '../api.ts'
import { Btn, Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'

const OPEN = ['proposed', 'open', 'researching']
const lines = (t?: string) => (t ?? '').split('\n').map(l => l.replace(/^\s*[-*]\s*/, '').trim()).filter(Boolean)

export function ClaimsList() {
  const [items, setItems] = useState<ClaimSummary[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { claimsApi.list().then(setItems).catch(e => setErr(String(e))) }, [])
  const open = (items ?? []).filter(c => OPEN.includes(c.status))
  const done = (items ?? []).filter(c => !OPEN.includes(c.status))
  return (
    <>
      <PageHead title="Claims" crumb="Home" sub="Problems the AI could not settle on its own." />
      {err && <div className="g-error">{err}</div>}
      <div className="g-grid-2" style={{ flex: 1 }}>
        <Panel title="Waiting for you" aside={open.length} testid="claims-open" className="g-scroll">
          <div className="g-rows">
            {open.map(c => <Row key={c.id} status={c.status === 'proposed' ? 'bad' : 'warn'} lead={c.summary} detail={`${c.kind} · ${c.status}`} when={ago(c.updated)} onClick={() => go(`home/claim/${c.id}`)} testid={`claim-${c.id}`} />)}
            {items && open.length === 0 && <Empty>Nothing waiting.</Empty>}
          </div>
        </Panel>
        <Panel title="Settled" aside={done.length} className="g-scroll">
          <div className="g-rows">
            {done.map(c => <Row key={c.id} status={c.status === 'resolved' ? 'ok' : 'idle'} lead={c.summary} detail={c.status} when={ago(c.updated)} onClick={() => go(`home/claim/${c.id}`)} />)}
            {items && done.length === 0 && <Empty>None yet.</Empty>}
          </div>
        </Panel>
      </div>
    </>
  )
}

export function ClaimDetail({ id }: { id: string }) {
  const [c, setC] = useState<ClaimFull | null>(null)
  const [err, setErr] = useState('')
  const [done, setDone] = useState('')
  const load = () => claimsApi.get(id).then(setC).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps
  const s = sections(c?.body ?? '')
  const m = c?.meta
  const decide = async (a: 'approve' | 'reject' | 'research_more') => {
    try { const r = await claimsApi.decide(id, a); setDone(a === 'approve' ? 'Approved.' : a === 'reject' ? 'Rejected.' : 'Sent back for more research.'); void r; load() } catch (e) { setErr(String(e)) }
  }
  const open = m && OPEN.includes(String(m.status))
  const research = lines(s['Research'])
  const proposal = lines(s['Proposal'])
  const evidence = lines(s['Evidence'])
  return (
    <>
      <PageHead title="Claim Detail" crumb="Home  >  Claim Detail" side={<span className="g-detail">Claim #{id.slice(0, 8)} · {m?.updated ? ago(String(m.updated)) : ''}</span>} />
      {err && <div className="g-error">{err}</div>}
      {m && (
        <div className="g-banner" data-testid="claim-banner"><StatusIcon kind={open ? 'bad' : 'ok'} /><span className="g-lead">{m.kind ? `${String(m.kind)[0].toUpperCase()}${String(m.kind).slice(1)}: ` : ''}{m.summary ?? s['Problem']}</span><span className="g-chip">{String(m.status)}</span></div>
      )}
      <div className="g-grid-2" style={{ flex: 1 }}>
        <Panel title="What research found" testid="claim-research" className="g-scroll">
          {research.length ? <ul className="g-bullets">{research.map((l, i) => <li key={i}>{l}</li>)}</ul> : <Empty>{m?.status === 'researching' ? 'Research is still running.' : 'No research notes yet.'}</Empty>}
          {proposal.length > 0 && <><h3 className="g-panel-title" style={{ marginTop: 12 }}>What the specialist tried</h3><ul className="g-bullets">{proposal.map((l, i) => <li key={i}>{l}</li>)}</ul></>}
        </Panel>
        <Panel title="Proof" testid="claim-proof" className="g-scroll">
          {evidence.length ? <div className="g-rows">{evidence.map((l, i) => <Row key={i} status="ok" lead={l} />)}</div> : <Empty>No evidence attached.</Empty>}
          {m?.run_id && <div style={{ marginTop: 10 }}><Btn primary onClick={() => go(`automations/flow/${String(m.env_id ?? '') || 'unknown'}/${m.run_id}`)} disabled={!m.env_id}>View run</Btn></div>}
          {s['Resolution'] && <><h3 className="g-panel-title" style={{ marginTop: 12 }}>History</h3><ul className="g-bullets">{lines(s['Resolution']).map((l, i) => <li key={i}>{l}</li>)}</ul></>}
        </Panel>
      </div>
      {done && <div className="g-saved" data-testid="claim-done">{done}</div>}
      {open && (
        <div className="g-actions g-actions-wide">
          <Btn primary onClick={() => decide('approve')} data-testid="claim-approve">Approve</Btn>
          <Btn onClick={() => decide('reject')} data-testid="claim-reject">Reject</Btn>
          <Btn onClick={() => decide('research_more')} data-testid="claim-more">Ask for more research</Btn>
        </div>
      )}
    </>
  )
}
