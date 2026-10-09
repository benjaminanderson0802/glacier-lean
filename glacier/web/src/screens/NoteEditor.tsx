// Friendly note editor: plain text, no markdown knowledge needed. Typing [[ suggests notes to link.
import { useMemo, useRef, useState } from 'react'
import { memory, slugify, type MemNote } from '../api.ts'
import { Btn } from '../ui/kit.tsx'
import { t } from '../i18n/index.ts'

export function NoteEditor({ path, initial, notes, onSaved, onCancel }: {
  path?: string; initial: string; notes: MemNote[]; onSaved: (path: string, commit: string) => void; onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState(initial)
  const [query, setQuery] = useState<string | null>(null)
  const [sel, setSel] = useState(0)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const ta = useRef<HTMLTextAreaElement>(null)

  const matches = useMemo(() => query === null ? [] : notes
    .filter(n => (n.title + ' ' + n.path).toLowerCase().includes(query.toLowerCase()))
    .slice(0, 6), [query, notes])

  const onChange = (v: string) => {
    setBody(v)
    const caret = ta.current?.selectionStart ?? v.length
    const before = v.slice(0, caret)
    const m = before.match(/\[\[([^\]\n]*)$/)
    setQuery(m ? m[1] : null); setSel(0)
  }
  const insert = (n: MemNote) => {
    const el = ta.current!
    const caret = el.selectionStart
    const start = body.slice(0, caret).lastIndexOf('[[')
    const link = `[[${n.path.replace(/\.md$/, '')}]]`
    const next = body.slice(0, start) + link + body.slice(caret)
    setBody(next); setQuery(null)
    requestAnimationFrame(() => { el.focus(); el.selectionStart = el.selectionEnd = start + link.length })
  }
  const save = async () => {
    const target = path ?? `${slugify(title || body.split('\n')[0] || 'note')}.md`
    if (!path && !title.trim()) { setErr(t('noteEditor.giveTitle')); return }
    setBusy(true); setErr('')
    try {
      const text = !path && !body.startsWith('# ') ? `# ${title.trim()}\n\n${body}` : body
      const r = await memory.save(target, text)
      onSaved(r.path, r.commit)
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  return (
    <div className="g-editor" data-testid="note-editor">
      {!path && <input className="g-input" placeholder={t('noteEditor.title')} value={title} onChange={e => setTitle(e.target.value)} data-testid="note-title" autoFocus />}
      <div className="g-editor-wrap">
        <textarea ref={ta} className="g-input g-textarea" value={body} data-testid="note-body" autoFocus={!!path}
          placeholder={t('noteEditor.placeholder')}
          onChange={e => onChange(e.target.value)}
          onKeyDown={e => {
            if (query === null || matches.length === 0) return
            if (e.key === 'ArrowDown') { e.preventDefault(); setSel(s => Math.min(matches.length - 1, s + 1)) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(s => Math.max(0, s - 1)) }
            else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); insert(matches[sel]) }
            else if (e.key === 'Escape') setQuery(null)
          }} />
        {query !== null && matches.length > 0 && (
          <div className="g-suggest g-panel" data-testid="link-suggest">
            <span className="g-detail">{t('noteEditor.linkTo')}</span>
            {matches.map((n, i) => (
              <button key={n.path} type="button" className={`g-navitem${i === sel ? ' active' : ''}`} onMouseDown={e => { e.preventDefault(); insert(n) }}>
                <span className="g-memory-link-suggestion">{n.title || n.path}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {err && <div className="g-error">{err}</div>}
      <div className="g-actions">
        <Btn primary onClick={save} disabled={busy} data-testid="note-save">{t('noteEditor.save')}</Btn>
        <Btn onClick={onCancel}>{t('noteEditor.cancel')}</Btn>
        <span className="g-detail" style={{ marginLeft: 'auto' }}>{t('noteEditor.savedInfo')}</span>
      </div>
    </div>
  )
}
