import { useEffect, useRef, useState } from 'react'
import { api } from './api.ts'

export function VaultView() {
  const [notes, setNotes] = useState<string[]>([])
  const [open, setOpen] = useState<{ path: string; body: string } | null>(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const selection = useRef(0)
  const refresh = () => {
    setLoading(true)
    return api.listNotes().then(n => { setNotes(n); setErr('') }).catch(e => setErr(String(e))).finally(() => setLoading(false))
  }
  useEffect(() => { refresh() }, [])
  const openNote = async (path: string) => {
    const request = ++selection.current
    try { const note = await api.getNote(path); if (request === selection.current) { setOpen(note); setErr('') } }
    catch (e) { if (request === selection.current) setErr(String(e)) }
  }
  return <div className="vault">
    <div className="memory-intro"><h2>Keep the useful things.</h2><p>Read the notes and saved flows in your local memory.</p></div>
    {err && <div className="error" role="alert">{err}</div>}
    <div className="memory-grid">
      <div className="vault-list"><div className="section-head"><span>Saved notes · {notes.length}</span><button className="ghost" data-testid="vault-refresh" onClick={refresh}>Refresh</button></div>
        {loading && <p className="muted small" role="status">Loading memory…</p>}
        {!notes.length && !loading && !err && <p className="muted small">Nothing saved yet. Notes from your flows will appear here.</p>}
        {notes.map(p => <button key={p} className={`list-item${open?.path === p ? ' active' : ''}`} data-testid={`vault-note-${p}`} onClick={() => openNote(p)}><span className="note-name">▤ {p.split('/').pop()}</span><span className="note-folder">{p}</span></button>)}
      </div>
      <div className="vault-body">{open ? <><div className="eyebrow">SAVED IN YOUR MEMORY</div><div className="vault-path">{open.path}</div><pre data-testid="vault-note-body">{open.body}</pre></> : <div className="selection-help"><span aria-hidden="true">▤</span><h3>A place to look back.</h3><p>Choose a note to read what was saved.</p></div>}</div>
    </div>
    <div className="memory-future"><span aria-hidden="true">⌘</span><div><h3>See how it all connects. <span className="soon">Coming soon</span></h3><p>A live memory graph, focus mode with links in and out, a friendly editor, and who, when, and which run behind every note.</p></div></div>
  </div>
}
