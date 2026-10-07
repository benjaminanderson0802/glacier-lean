import { useEffect, useMemo, useState } from 'react'
import { ago, memory, type MemCommit, type MemHit, type MemNote, type MemNoteFull } from '../api.ts'
import { Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { go } from '../route.ts'

export function MemoryScreen({ path }: { path?: string }) {
  const [notes, setNotes] = useState<MemNote[] | null>(null)
  const [tag, setTag] = useState<string>('All')
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<MemHit[] | null>(null)
  const [note, setNote] = useState<MemNoteFull | null>(null)
  const [hist, setHist] = useState<MemCommit[]>([])
  const [err, setErr] = useState('')

  useEffect(() => { memory.notes().then(setNotes).catch(e => setErr(String(e))) }, [])
  useEffect(() => {
    if (!path) { setNote(null); return }
    memory.note(path).then(setNote).catch(e => setErr(String(e)))
    memory.history(path).then(setHist).catch(() => setHist([]))
  }, [path])
  useEffect(() => {
    if (!q.trim()) { setHits(null); return }
    const t = setTimeout(() => memory.search(q).then(setHits).catch(e => setErr(String(e))), 250)
    return () => clearTimeout(t)
  }, [q])

  const tags = useMemo(() => {
    const c = new Map<string, number>()
    for (const n of notes ?? []) for (const t of n.tags ?? []) c.set(t, (c.get(t) ?? 0) + 1)
    return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8)
  }, [notes])
  const list = (notes ?? []).filter(n => tag === 'All' || n.tags?.includes(tag)).sort((a, b) => (b.updated ?? '').localeCompare(a.updated ?? ''))
  const open = (p: string) => go(`memory/${encodeURIComponent(p)}`)

  return (
    <>
      <PageHead title="Memory" sub="What Glacier knows." side={<input className="g-input" style={{ width: 280 }} placeholder="Search memory…" value={q} onChange={e => setQ(e.target.value)} data-testid="memory-search" />} />
      {err && <div className="g-error">{err}</div>}
      <div className="g-memory">
        <Panel className="g-sidenav" testid="memory-tags">
          {['All', ...tags.map(t => t[0])].map(t => (
            <button key={t} className={`g-navitem${t === tag ? ' active' : ''}`} onClick={() => { setTag(t); setQ('') }}>
              <span>{t}</span><span className="g-muted">{t === 'All' ? notes?.length ?? '' : tags.find(x => x[0] === t)?.[1]}</span>
            </button>
          ))}
        </Panel>
        <Panel title={hits ? `Results for “${q}”` : 'Notes'} aside={hits ? hits.length : list.length} testid="memory-list" className="g-scroll">
          <div className="g-rows">
            {hits
              ? hits.map(h => <Row key={h.path} icon="note" lead={h.title || h.path} detail={h.snippet} onClick={() => open(h.path)} testid={`mem-hit-${h.path}`} />)
              : list.map(n => <Row key={n.path} icon="note" lead={n.title || n.path} detail={n.author ? `by ${n.author}` : undefined} when={ago(n.updated)} onClick={() => open(n.path)} testid={`mem-note-${n.path}`} />)}
            {notes && !hits && list.length === 0 && <Empty>No notes yet.</Empty>}
            {hits && hits.length === 0 && <Empty>Nothing found.</Empty>}
          </div>
        </Panel>
        <Panel title={note ? String(note.meta?.title ?? note.path) : 'Note'} testid="memory-note" className="g-scroll">
          {!note ? <Empty>Pick a note to read it.</Empty> : (
            <>
              <pre className="g-notebody" data-testid="memory-note-body">{note.body}</pre>
              {(note.links_out.length > 0 || note.links_in.length > 0) && (
                <div className="g-links">
                  {note.links_out.length > 0 && <div><span className="g-muted">Links to </span>{note.links_out.map(l => <button key={l} className="g-link" onClick={() => open(`${l}.md`)}>{l}</button>)}</div>}
                  {note.links_in.length > 0 && <div><span className="g-muted">Linked from </span>{note.links_in.map(l => <button key={l} className="g-link" onClick={() => open(l)}>{l.replace(/\.md$/, '')}</button>)}</div>}
                </div>
              )}
              {hist.length > 0 && (
                <div className="g-rows" style={{ marginTop: 10 }}>
                  {hist.slice(0, 5).map(c => <Row key={c.commit} icon="memory" lead={c.message} detail={`${c.author} · ${c.commit}`} when={ago(c.date)} />)}
                </div>
              )}
            </>
          )}
        </Panel>
      </div>
    </>
  )
}
