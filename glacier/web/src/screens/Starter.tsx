// "Get started" on Home: what Glacier found on this computer and a starter setup the owner can accept in one click.
import { useEffect, useState } from 'react'
import { starterApi, type StarterProposal } from '../api.ts'
import { Btn, Panel, Row } from '../ui/kit.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'

const HIDE_KEY = 'glacier.starter.hidden'
const hidden = () => { try { return localStorage.getItem(HIDE_KEY) === '1' } catch { return false } }

export function StarterPanel() {
  const [show, setShow] = useState(false)
  const [p, setP] = useState<StarterProposal | null>(null)
  const [picked, setPicked] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<{ id: string; name: string }[] | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (hidden()) return
    starterApi.get().then(x => {
      if (x.applied) return  // shown until the starter setup is done once (or hidden with "not now")
      setP(x); setPicked(x.suggested_automations.map(a => a.template_id)); setShow(true)
    }).catch(() => {})
  }, [])

  if (!show || !p) return null
  const hide = () => { try { localStorage.setItem(HIDE_KEY, '1') } catch { /* private window: hide for now only */ } setShow(false) }
  const toggle = (id: string) => setPicked(x => x.includes(id) ? x.filter(y => y !== id) : [...x, id])
  const apply = async () => {
    setBusy(true); setErr('')
    try { const r = await starterApi.apply(picked, p.mode); setDone(r.created) }
    catch (e) { setErr(String(e).replace(/^Error: /, '')) }
    finally { setBusy(false) }
  }
  const agents = p.coding_agents_found.filter(a => a.found)

  return (
    <Panel title={t('starter.title')} testid="starter" className="starter-window" aside={<button className="g-link" onClick={hide} data-testid="starter-hide">{t('starter.notNow')}</button>} style={{ flex: 1, minHeight: 0 }}>
      {done ? (
        <div data-testid="starter-done">
          <div className="g-saved">{done.length ? t('starter.added', { count: done.length, plural: done.length > 1 ? 's' : '' }) : t('starter.nothingNew')}</div>
          <div className="g-rows">{done.map(d => <Row key={d.id} icon="automations" lead={d.name} onClick={() => go(`automations/flow/${d.id}`)} />)}</div>
          <Btn onClick={hide} style={{ marginTop: 10 }}>{t('starter.close')}</Btn>
        </div>
      ) : (
        <>
          <div className="g-detail" data-testid="starter-reason" title={p.reason}>{p.reason} {p.local_model && t('starter.localModel', { name: p.local_model })}</div>
          <div className="g-detail" title={t('starter.agentsFound', { value: agents.length ? agents.map(a => a.name).join(', ') : t('starter.noAgents') })}>{t('starter.agentsFound', { value: agents.length ? agents.map(a => a.name).join(', ') : t('starter.noAgents') })}</div>
          <div className="g-muted" style={{ marginTop: 10 }}>{t('starter.suggested')}</div>
          <div className="g-rows">
            {p.suggested_automations.map((a, i) => (
              <Row key={a.template_id} status={picked.includes(a.template_id) ? 'ok' : 'idle'} lead={a.name} detail={a.why}
                onClick={() => toggle(a.template_id)} testid={`starter-pick-${i}`} />
            ))}
          </div>
          {p.missing_but_useful.length > 0 && (
            <>
              <div className="g-muted" style={{ marginTop: 10 }}>{t('starter.tools')}</div>
              <div className="g-rows">{p.missing_but_useful.map(m => <Row key={m.name} icon="plus" lead={`${m.name} (${m.license})`} detail={`${m.why} ${m.download_page}`} />)}</div>
            </>
          )}
          {err && <div className="g-error">{err}</div>}
          <div className="g-actions" style={{ marginTop: 12 }}>
            <Btn primary onClick={apply} disabled={busy} data-testid="starter-apply">{t('starter.setUp')}</Btn>
            <Btn onClick={hide}>{t('starter.cancel')}</Btn>
          </div>
        </>
      )}
    </Panel>
  )
}
