// Memory cleanup (mockup panel 12): review suggested merges and archives; every change can be undone.
import { useEffect, useState } from 'react'
import { memory, memoryMore, type HygieneProposal } from '../api.ts'
import { Btn, Empty, Panel } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { t } from '../i18n/index.ts'

const WHAT: Record<string, string> = { merge: t('memoryCleanup.merge'), archive: t('memoryCleanup.archive') }

export function MemoryCleanup() {
  const [items, setItems] = useState<HygieneProposal[] | null>(null)
  const [chosen, setChosen] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState<{ text: string; ok: boolean; undo?: { paths: string[]; commit: string } }[]>([])
  const [err, setErr] = useState('')
  const load = () => memoryMore.hygiene().then(p => { setItems(p); setChosen(new Set()) }).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [])
  const scan = async () => { setBusy(true); try { setItems(await memoryMore.scan()); setChosen(new Set()) } catch (e) { setErr(String(e)) } finally { setBusy(false) } }
  const apply = async (approve: boolean) => {
    setBusy(true)
    const out: typeof log = []
    for (const p of (items ?? []).filter(p => chosen.has(p.id))) {
      try {
        const r = await memoryMore.decide(p.id, approve)
        out.push({ text: `${approve ? (WHAT[p.kind] ?? p.kind) : t('memoryCleanup.dismissed')}: ${p.paths.join(', ')}`, ok: true, undo: r.commit ? { paths: p.paths, commit: r.commit } : undefined })
      } catch (e) { out.push({ text: String(e).replace(/^Error: /, ''), ok: false }) }
    }
    setLog(out); setBusy(false); load()
  }
  const sel = (items ?? []).filter(p => chosen.has(p.id))
  const notes = new Set(sel.flatMap(p => p.kind === 'merge' ? p.paths.slice(1) : p.paths)).size
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement && event.target.type === 'checkbox') {
        const boxes = [...(document.querySelector('[data-testid="cleanup-list"]')?.querySelectorAll<HTMLInputElement>('.g-box') ?? [])]
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault()
          const current = boxes.indexOf(event.target)
          boxes[(current + (event.key === 'ArrowDown' ? 1 : boxes.length - 1)) % boxes.length]?.focus()
        } else if (event.key === 'Enter') { event.preventDefault(); event.target.click() }
        return
      }
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLButtonElement) return
      if (event.key === 'Enter' && sel.length > 0) { event.preventDefault(); void apply(true) }
      else if (event.key.toLowerCase() === 'u') {
        const undo = document.querySelector<HTMLButtonElement>('[data-testid^="cleanup-undo-"]')
        if (undo) { event.preventDefault(); undo.click() }
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [sel, items, busy])
  return (
    <div className="g-memadd g-memory-cleanup-layout">
      <Panel title={t('memoryCleanup.suggestions')} aside={<Btn onClick={scan} disabled={busy} data-testid="cleanup-scan">{t('memoryCleanup.scanAgain')}</Btn>} testid="cleanup-list" className="g-scroll">
        {err && <div className="g-error">{err}</div>}
        {items && items.length === 0 && <Empty>{t('memoryCleanup.tidy')}</Empty>}
        <div className="g-rows">
          {(items ?? []).map(p => (
            <label key={p.id} className={`g-row g-check g-cleanup-row${chosen.has(p.id) ? ' selected' : ''}`} data-testid={`cleanup-${p.id}`}>
              <span className="g-menu-cursor" style={{ visibility: chosen.has(p.id) ? 'visible' : 'hidden' }} />
              <input type="checkbox" className="g-box" checked={chosen.has(p.id)} onChange={e => setChosen(c => { const n = new Set(c); if (e.target.checked) n.add(p.id); else n.delete(p.id); return n })} />
              <span className="g-mid"><span className="g-lead">{WHAT[p.kind] ?? p.kind}: {p.paths.map(x => x.replace(/\.md$/, '')).join(', ')}</span><span className="g-detail">{p.reason}</span></span>
              <span className="g-when">{t('memoryCleanup.item', { count: p.paths.length, plural: p.paths.length > 1 ? 's' : '' })}</span>
            </label>
          ))}
        </div>
      </Panel>
      <Panel title={t('memoryCleanup.impact')} testid="cleanup-impact">
        <dl className="g-kv g-kv-tight">
          <dt>{t('memoryCleanup.selected')}</dt><dd>{sel.length}</dd>
          <dt>{t('memoryCleanup.tidied')}</dt><dd>{notes}</dd>
          <dt>{t('memoryCleanup.deleted')}</dt><dd>{t('memoryCleanup.deletedDetail')}</dd>
        </dl>
        <div className="g-actions" style={{ marginTop: 12 }}>
          <Btn primary onClick={() => apply(true)} disabled={busy || sel.length === 0} data-testid="cleanup-apply">{t('memoryCleanup.cleanUp')}</Btn>
          <Btn onClick={() => apply(false)} disabled={busy || sel.length === 0}>{t('memoryCleanup.dismiss')}</Btn>
        </div>
        <div className="g-rows" style={{ marginTop: 10 }}>
          {log.map((l, i) => (
            <div key={i} className="g-row"><span className="g-ico"><StatusIcon kind={l.ok ? 'ok' : 'bad'} /></span><span className="g-mid"><span className="g-lead">{l.text}</span></span>
              <span className="g-when">{l.undo && <Btn onClick={async () => { for (const path of l.undo!.paths) await memory.undo(path, l.undo!.commit); setLog(x => x.map((y, j) => j === i ? { ...y, text: t('memoryCleanup.undone', { value: y.text }), undo: undefined } : y)); load() }} data-testid={`cleanup-undo-${i}`}>{t('memoryCleanup.undo')}</Btn>}</span></div>
          ))}
        </div>
      </Panel>
    </div>
  )
}
