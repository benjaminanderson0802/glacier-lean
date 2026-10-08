// Claims: problems the AI could not solve alone, waiting for the owner (mockup panel 3).
import { useEffect, useState } from 'react'
import { ago, api, claimsApi, sections, type ClaimFull, type ClaimSummary } from '../api.ts'
import { Btn, Empty, Hint, HintBar, KeyboardMenu, NamedTextBox, PageHead, Panel, Row } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'

const OPEN = ['proposed', 'open', 'researching']
const lines = (t?: string) => (t ?? '').split('\n').map(l => l.replace(/^\s*[-*]\s*/, '').trim()).filter(Boolean)

export function ClaimsList() {
  const [items, setItems] = useState<ClaimSummary[] | null>(null)
  const [err, setErr] = useState('')
  const [selected, setSelected] = useState('')
  const [deleteUndo,setDeleteUndo]=useState<UndoAction|null>(null)
  useEffect(() => { claimsApi.list().then(setItems).catch(e => setErr(String(e))) }, [])
  const open = (items ?? []).filter(c => OPEN.includes(c.status))
  const done = (items ?? []).filter(c => !OPEN.includes(c.status))
  const selectedClaim = open.find(c => c.id === selected)
  return (
    <>
      <PageHead title={t('claims.title')} crumb={t('claims.crumb')} sub={t('claims.subtitle')} />
      {err && <div className="g-error">{err}</div>}
      <DeleteUndo action={deleteUndo} onDone={()=>setDeleteUndo(null)} onError={e=>setErr(String(e))}/>
      <div className="g-grid-2" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: 'calc(2 * var(--px))', flex: 1, minHeight: 0 }}>
        <Panel title={t('claims.waiting')} aside={open.length} testid="claims-open" className="g-scroll" style={{ gridColumn: 'auto', gridRow: 'auto' }}>
          {open.length ? <>
            <KeyboardMenu label={t('claims.waiting')} items={open.map(c => ({ id: c.id, testid: `claim-${c.id}`, label: <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}><span className="g-lead">{c.summary}</span><span className="g-detail">{c.kind} · {c.status} · {ago(c.updated)}</span></span> }))} selected={selected} onSelect={setSelected} />
            {selectedClaim && <div onKeyDown={event => { if (event.key === 'Enter') go(`home/claim/${selectedClaim.id}`) }}><Btn onClick={() => go(`home/claim/${selectedClaim.id}`)}>{t('hint.open')}</Btn></div>}
            {open.map(c=><div key={c.id} style={{display:'flex',alignItems:'center',gap:6}}><div style={{flex:1}}><Row status={c.status==='proposed'?'bad':'warn'} lead={c.summary} detail={`${c.kind} · ${c.status}`} when={ago(c.updated)} onClick={()=>go(`home/claim/${c.id}`)} testid={`claim-row-${c.id}`}/></div><DeleteAction label={t('claims.deleteClaim')} impact={t('delete.claimImpact')} testid={`claim-delete-${c.id}`} onDelete={async()=>{const r=await claimsApi.delete(c.id);return {title:t('delete.removed'),run:async()=>{await claimsApi.undoDelete(c.id,r.commit);setItems(await claimsApi.list())}}}} onDeleted={action=>{setDeleteUndo(action??null);setItems(current=>current?.filter(x=>x.id!==c.id)??null)}} onError={e=>setErr(String(e))}/></div>)}
          </> : items && <Empty>{t('claims.nothingWaiting')}</Empty>}
        </Panel>
        <Panel title={t('claims.settled')} aside={done.length} className="g-scroll" style={{ gridColumn: 'auto', gridRow: 'auto' }}>
          {done.length ? done.map(c=><div key={c.id} style={{display:'flex',alignItems:'center',gap:6}}><div style={{flex:1}}><Row status={c.status==='resolved'?'ok':'idle'} lead={c.summary} detail={c.status} when={ago(c.updated)} onClick={()=>go(`home/claim/${c.id}`)}/></div><DeleteAction label={t('claims.deleteClaim')} impact={t('delete.claimImpact')} testid={`claim-delete-${c.id}`} onDelete={async()=>{const r=await claimsApi.delete(c.id);return {title:t('delete.removed'),run:async()=>{await claimsApi.undoDelete(c.id,r.commit);setItems(await claimsApi.list())}}}} onDeleted={action=>{setDeleteUndo(action??null);setItems(current=>current?.filter(x=>x.id!==c.id)??null)}} onError={e=>setErr(String(e))}/></div>) : items && <Empty>{t('claims.noneYet')}</Empty>}
        </Panel>
      </div>
      <HintBar><Hint keyLabel="↑↓">{t('hint.selectClaim')}</Hint><Hint keyLabel="Enter">{t('hint.open')}</Hint></HintBar>
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
    try { const r = await claimsApi.decide(id, a); setDone(a === 'approve' ? t('claims.approved') : a === 'reject' ? t('claims.rejected') : t('claims.sentForResearch')); void r; load() } catch (e) { setErr(String(e)) }
  }
  const open = m && OPEN.includes(String(m.status))
  const rerun = async () => {
    try { const r = await claimsApi.rerun(id); go(`automations/flow/${r.env_id}/${r.run_id}`) } catch (e) { setErr(String(e).replace(/^Error: /, '')) }
  }
  const research = lines(s['Research'])
  const proposal = lines(s['Proposal'])
  const evidence = lines(s['Evidence'])
  useEffect(() => {
    if (!open) return
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return
      if (event.key === 'Escape') { go('home/claims'); return }
      const actions: Record<string, 'approve' | 'reject' | 'research_more'> = { a: 'approve', x: 'reject', r: 'research_more' }
      const action = actions[event.key.toLowerCase()]
      if (action) { event.preventDefault(); void decide(action) }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [open, id]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <PageHead title={t('claims.detail')} crumb={t('claims.detailCrumb')} side={<span className="g-detail">{t('claims.id', { id: id.slice(0, 8) })} · {m?.updated ? ago(String(m.updated)) : ''}</span>} />
      {err && <div className="g-error">{err}</div>}
      {m && (
        <div className="g-banner" data-testid="claim-banner"><StatusIcon kind={open ? 'bad' : 'ok'} /><span className="g-lead">{m.kind ? `${String(m.kind)[0].toUpperCase()}${String(m.kind).slice(1)}: ` : ''}{m.summary ?? s['Problem']}</span><span className="g-chip">{String(m.status)}</span></div>
      )}
      <div className="g-grid-2" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: 'calc(2 * var(--px))', flex: 1, minHeight: 0 }}>
        <Panel title={t('claims.research')} testid="claim-research" className="g-scroll" style={{ gridColumn: 'auto', gridRow: 'auto' }}>
          {research.length ? <NamedTextBox><ul className="g-bullets">{research.map((l, i) => <li key={i}>{l}</li>)}</ul></NamedTextBox> : <Empty>{m?.status === 'researching' ? t('claims.researchRunning') : t('claims.noResearch')}</Empty>}
          {proposal.length > 0 && <><h3 className="g-panel-title" style={{ marginTop: 12 }}>{t('claims.specialistTried')}</h3><ul className="g-bullets">{proposal.map((l, i) => <li key={i}>{l}</li>)}</ul></>}
        </Panel>
        <Panel title={t('claims.proof')} testid="claim-proof" className="g-scroll" style={{ gridColumn: 'auto', gridRow: 'auto' }}>
          {evidence.length ? <NamedTextBox><div className="g-rows">{evidence.map((l, i) => <Row key={i} status="ok" lead={l} />)}</div></NamedTextBox> : <Empty>{t('claims.noEvidence')}</Empty>}
          {m?.run_id && (
            <div className="g-actions" style={{ marginTop: 10 }}>
              <Btn primary={open} onClick={() => api.getRun(String(m.run_id)).then(r => go(`automations/flow/${r.env_id}/${r.run_id}`)).catch(() => setErr(t('claims.runGone')))} data-testid="claim-view-run">{t('claims.viewRun')}</Btn>
              {!open && <Btn primary onClick={rerun} data-testid="claim-rerun" title={t('claims.rerunTitle')}>{t('claims.rerun')}</Btn>}
            </div>
          )}
          {s['Resolution'] && <><h3 className="g-panel-title" style={{ marginTop: 12 }}>{t('claims.history')}</h3><ul className="g-bullets">{lines(s['Resolution']).map((l, i) => <li key={i}>{l}</li>)}</ul></>}
        </Panel>
      </div>
      {done && <div className="g-saved" data-testid="claim-done">{done}</div>}
      {open && (
        <div className="g-actions g-actions-wide">
          <Btn primary onClick={() => decide('approve')} data-testid="claim-approve">{t('claims.approve')}</Btn>
          <Btn onClick={() => decide('reject')} data-testid="claim-reject">{t('claims.reject')}</Btn>
          <Btn onClick={() => decide('research_more')} data-testid="claim-more">{t('claims.moreResearch')}</Btn>
        </div>
      )}
      <HintBar>{open ? <><Hint keyLabel="A">{t('hint.approve')}</Hint><Hint keyLabel="X">{t('hint.reject')}</Hint><Hint keyLabel="R">{t('hint.researchMore')}</Hint></> : <Hint keyLabel="Esc">{t('hint.backClaims')}</Hint>}</HintBar>
    </>
  )
}
