import { useEffect, useState } from 'react'
import { api } from '../api.ts'

export function VaultView() {
  const [notes, setNotes] = useState<string[]>([])
  const [open, setOpen] = useState<{ path: string; body: string } | null>(null)
  const [err, setErr] = useState('')

  const refresh = () => api.listNotes().then(n => { setNotes(n); setErr('') }).catch(e => setErr(String(e)))
  useEffect(() => { refresh() }, [])

  return (
    <div className="vault">
      <div className="vault-list">
        <div className="section-head">
          <span>Notes</span>
          <button className="ghost" data-testid="vault-refresh" onClick={refresh}>Refresh</button>
        </div>
        {err && <div className="error">{err}</div>}
        {notes.length === 0 && !err && <div className="muted">No notes yet.</div>}
        {notes.map(p => (
          <button
            key={p}
            className={`list-item${open?.path === p ? ' active' : ''}`}
            data-testid={`vault-note-${p}`}
            onClick={() => api.getNote(p).then(setOpen).catch(e => setErr(String(e)))}
          >{p}</button>
        ))}
      </div>
      <div className="vault-body">
        {open
          ? <><div className="vault-path">{open.path}</div><pre data-testid="vault-note-body">{open.body}</pre></>
          : <div className="muted">Select a note.</div>}
      </div>
    </div>
  )
}
