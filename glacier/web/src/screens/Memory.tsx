import { useEffect, useMemo, useRef, useState } from 'react'
import { ago, api, memory, type MemCommit, type MemHit, type MemNote, type MemNoteFull } from '../api.ts'
import { Btn, Empty, Hint, HintBar, KeyboardMenu, NamedTextBox, PageHead, Panel, Row } from '../ui/kit.tsx'
import { NoteEditor } from './NoteEditor.tsx'
import { MemoryAdd } from './MemoryAdd.tsx'
import { MemoryCleanup } from './MemoryCleanup.tsx'
import { lazy, Suspense } from 'react'
const MemoryMap = lazy(() => import('./MemoryMap.tsx').then(m => ({ default: m.MemoryMap })))
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'
import './memory.css'

/** Plain-language writer: owner -> you; run:<id> -> an automation; worker:<model> -> AI (<model>). */
function whoWrote(author: string): string {
  if (!author || author === 'owner') return t('memory.wroteYou')
  if (author.startsWith('run:')) return t('memory.wroteAutomation')
  if (author.startsWith('worker:')) return t('memory.wroteAI', { name: author.slice(7) })
  if (author === 'assistant') return t('memory.wroteAssistant')
  return author
}

const VIEWS = [['', t('memory.viewsNotes')], ['~map', t('memory.map')], ['~add', t('memory.add')], ['~cleanup', t('memory.cleanup')]] as const

export function MemoryScreen({ path }: { path?: string }) {
  const view = path?.startsWith('~') ? path : ''
  const switcher = <KeyboardMenu orientation="horizontal" label={t('memory.title')} items={VIEWS.map(([v, l]) => ({ id: v, label: l, testid: `memview-${l.toLowerCase()}` }))} selected={view} onSelect={v => go(v ? `memory/${v}` : 'memory')} />
  const body = view ? (
    <>
      <PageHead title={view === '~map' ? t('memory.title') : view === '~add' ? t('memory.addTitle') : t('memory.cleanupTitle')} crumb={t('memory.title')}
        sub={view === '~map' ? t('memory.subtitle') : view === '~add' ? t('memory.importSubtitle') : t('memory.organizeSubtitle')} side={switcher} />
      {view === '~map' ? <Suspense fallback={<div className="g-empty">{t('memory.drawMap')}</div>}><MemoryMap /></Suspense> : view === '~add' ? <MemoryAdd /> : <MemoryCleanup />}
    </>
  ) : <NotesView path={path} switcher={switcher} />
  return <div className="g-memory-screen g-memory">{body}<HintBar>
    {view === '~map' ? <><Hint keyLabel="Click">{t('hint.openNote')}</Hint><Hint keyLabel="Esc">{t('hint.notes')}</Hint></>
      : view === '~add' ? <><Hint keyLabel="←→">{t('hint.moveTab')}</Hint><Hint keyLabel="Enter">{t('hint.save')}</Hint></>
        : view === '~cleanup' ? <><Hint keyLabel="Space">{t('hint.select')}</Hint><Hint keyLabel="Enter">{t('hint.cleanUp')}</Hint><Hint keyLabel="U">{t('hint.undo')}</Hint></>
          : <><Hint keyLabel="N">{t('hint.newNote')}</Hint><Hint keyLabel="/">{t('hint.search')}</Hint><Hint keyLabel="Enter">{t('hint.openNote')}</Hint></>}
  </HintBar></div>
}

function NotesView({ path, switcher }: { path?: string; switcher: React.ReactNode }) {
  const searchRef = useRef<HTMLInputElement>(null)
  const [notes, setNotes] = useState<MemNote[] | null>(null)
  const [tag, setTag] = useState<string>(t('memory.all'))
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<MemHit[] | null>(null)
  const [note, setNote] = useState<MemNoteFull | null>(null)
  const [hist, setHist] = useState<MemCommit[]>([])
  const [err, setErr] = useState('')
  const [editing, setEditing] = useState<'new' | 'edit' | null>(null)
  const [saved, setSaved] = useState<{ path: string; commit: string } | null>(null)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renamed, setRenamed] = useState<{ from: string; path: string; commit: string } | null>(null)
  const [deleteUndo, setDeleteUndo] = useState<UndoAction | null>(null)
  const [focusedNotePath, setFocusedNotePath] = useState('')

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return
      if (event.key.toLowerCase() === 'n') { event.preventDefault(); setEditing('new') }
      else if (event.key === '/') { event.preventDefault(); searchRef.current?.focus() }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])

  const reloadNotes = () => memory.notes().then(setNotes).catch(e => setErr(String(e)))
  useEffect(() => { reloadNotes() }, [])
  const loadNote = (p: string) => {
    memory.note(p).then(setNote).catch(e => setErr(String(e)))
    memory.history(p).then(setHist).catch(() => setHist([]))
  }
  useEffect(() => {
    setEditing(null); setRenaming(null)
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
  const list = (notes ?? []).filter(n => tag === t('memory.all') || n.tags?.includes(tag)).sort((a, b) => (b.updated ?? '').localeCompare(a.updated ?? ''))
  useEffect(() => {
    if (list.some(n => n.path === focusedNotePath)) return
    const nextPath = list[0]?.path ?? ''
    setFocusedNotePath(nextPath)
    if (focusedNotePath) requestAnimationFrame(() => document.querySelector<HTMLButtonElement>('[data-testid^="mem-note-"]')?.focus())
  }, [list, focusedNotePath])
  const moveNoteFocus = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    const currentPath = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-testid^="mem-note-"]')?.dataset.testid?.slice('mem-note-'.length)
    if (!currentPath || !list.length) return
    event.preventDefault()
    event.stopPropagation()
    const index = list.findIndex(n => n.path === currentPath)
    const next = list[(index + (event.key === 'ArrowDown' ? 1 : list.length - 1)) % list.length]
    setFocusedNotePath(next.path)
    document.querySelector<HTMLButtonElement>(`[data-testid="mem-note-${CSS.escape(next.path)}"]`)?.focus()
  }
  const open = (p: string) => go(`memory/${encodeURIComponent(p)}`)
  const deleteNote = async (p: string) => { const result = await memory.delete(p); return { title: t('delete.removed'), run: async () => { await memory.undoDelete(p, result.commit); reloadNotes() } } }
  const noteDeleted = (p: string, action?: UndoAction) => { setDeleteUndo(action ?? null); reloadNotes(); if (note?.path === p) { setNote(null); go('memory') } }

  return (
    <>
      <PageHead title={t('memory.title')} sub={t('memory.subtitle')} side={<>{switcher}<input ref={searchRef} className="g-input" style={{ width: 240 }} placeholder={t('memory.search')} value={q} onChange={e => setQ(e.target.value)} data-testid="memory-search" /></>} />
      {err && <div className="g-error">{err}</div>}
      <DeleteUndo action={deleteUndo} onDone={() => setDeleteUndo(null)} onError={e => setErr(String(e))} />
      <div className="g-memory g-memory-notes-layout">
        <Panel className="g-sidenav" testid="memory-tags" title={t('memory.filters')}>
          <KeyboardMenu label={t('memory.filters')} items={[t('memory.all'), ...tags.map(x => x[0])].map(value => ({ id: value, label: <><span>{value}</span><span className="g-memory-count">{value === t('memory.all') ? notes?.length ?? '' : tags.find(x => x[0] === value)?.[1]}</span></> }))} selected={tag} onSelect={value => { setTag(value); setQ('') }} />
        </Panel>
        <Panel title={hits ? t('memory.results', { query: q }) : t('memory.viewsNotes')} aside={hits ? hits.length : list.length} testid="memory-list" className="g-scroll">
          <div className="g-rows" onKeyDown={moveNoteFocus}>
            {hits
              ? hits.map(h => <div key={h.path} className="g-memory-note-row"><div className="g-memory-note-row-main"><Row lead={h.title||h.path} detail={h.snippet} onClick={()=>open(h.path)} testid={`mem-hit-${h.path}`} /></div><DeleteAction label={t('memory.deleteNote')} impact={t('delete.noteImpact')} testid={`mem-delete-${encodeURIComponent(h.path)}`} onDelete={()=>deleteNote(h.path)} onDeleted={action=>noteDeleted(h.path,action)} onError={e=>setErr(String(e))} /></div>)
              : list.map(n => <div key={n.path} className="g-memory-note-row"><div className="g-memory-note-row-main"><Row lead={n.title||n.path} detail={n.author?t('memory.byAuthor',{name:n.author}):undefined} when={ago(n.updated)} onClick={()=>open(n.path)} onFocus={() => setFocusedNotePath(n.path)} className={focusedNotePath === n.path ? 'sel' : ''} testid={`mem-note-${n.path}`} /></div><DeleteAction label={t('memory.deleteNote')} impact={t('delete.noteImpact')} testid={`mem-delete-${encodeURIComponent(n.path)}`} onDelete={()=>deleteNote(n.path)} onDeleted={action=>noteDeleted(n.path,action)} onError={e=>setErr(String(e))} /></div>)}
            {notes && !hits && list.length === 0 && <Empty>{t('memory.noNotes')}</Empty>}
            {hits && hits.length === 0 && <Empty>{t('memory.nothingFound')}</Empty>}
          </div>
        </Panel>
        <Panel title={editing === 'new' ? t('memory.newNote') : note ? String(note.meta?.title ?? note.path) : t('memory.note')}
          aside={editing ? undefined : <span style={{ display: 'flex', gap: 8 }}>{note && <Btn onClick={() => setRenaming(note.path.replace(/\.md$/, ''))} data-testid="note-rename">{t('memory.rename')}</Btn>}{note && <Btn onClick={() => setEditing('edit')} data-testid="note-edit">{t('memory.edit')}</Btn>}<Btn onClick={() => setEditing('new')} data-testid="note-new">{t('memory.newNote')}</Btn></span>}
          testid="memory-note" className="g-scroll">
          {saved && !editing && (
            <div className="g-saved" data-testid="note-saved">{t('memory.savedVersion', { commit: saved.commit })}
              <Btn onClick={async () => { await memory.undo(saved.path, saved.commit); setSaved(null); loadNote(saved.path); reloadNotes() }} data-testid="note-undo">{t('memory.undo')}</Btn></div>
          )}
          {renamed && !editing && (
            <div className="g-saved" data-testid="note-renamed">{t('memory.renamed', { from: renamed.from })}
              <Btn onClick={async () => {
                try { await memory.undo(renamed.path, renamed.commit); const back = renamed.from; setRenamed(null); reloadNotes(); open(back) }
                catch (e) { setErr(String(e)) }
              }} data-testid="note-rename-undo">{t('memory.undo')}</Btn></div>
          )}
          {renaming !== null && note && !editing && (
            <form className="g-saved" data-testid="note-rename-form" onSubmit={async e => {
              e.preventDefault()
              const to = renaming.trim().endsWith('.md') ? renaming.trim() : `${renaming.trim()}.md`
              try {
                const r = await memory.rename(note.path, to)
                setRenamed({ from: note.path, path: r.path, commit: r.commit }); setRenaming(null); setErr(''); reloadNotes(); open(r.path)
              } catch (x) { setErr(String(x)) }
            }}>
              <span>{t('memory.newName')}</span>
              <input className="g-input" value={renaming} onChange={e => setRenaming(e.target.value)} data-testid="note-rename-input" autoFocus />
              <Btn primary type="submit" data-testid="note-rename-save">{t('memory.rename')}</Btn>
              <Btn onClick={() => setRenaming(null)}>{t('memory.cancel')}</Btn>
            </form>
          )}
          {editing ? (
            <NoteEditor key={editing + (note?.path ?? '')} path={editing === 'edit' ? note?.path : undefined} initial={editing === 'edit' ? note?.body ?? '' : ''} notes={notes ?? []}
              onCancel={() => setEditing(null)}
              onSaved={(p, commit) => { setSaved({ path: p, commit }); setEditing(null); reloadNotes(); if (p === path) loadNote(p); else open(p) }} />
          ) : !note ? <Empty>{t('memory.pickNote')}</Empty> : (
            <>
              <div className="g-trust" data-testid="note-trust">
                <span>{t('memory.writtenBy')}<b>{whoWrote(String(note.meta?.author ?? 'owner'))}</b></span>
                {note.meta?.updated ? <span>{ago(String(note.meta.updated))}</span> : null}
                {note.meta?.run_id ? <button className="g-link" data-testid="note-run" onClick={() => api.getRun(String(note.meta.run_id)).then(r => go(`automations/flow/${r.env_id}/${r.run_id}`)).catch(() => setErr(t('memory.noRun')))}>{t('memory.fromRun')}</button> : null}
                {hist.length > 1 && <button className="g-link" data-testid="note-undo-last" onClick={async () => { await memory.undo(note.path); loadNote(note.path); reloadNotes() }}>{t('memory.undoLast')}</button>}
              </div>
              <NamedTextBox className="g-notebody" testid="memory-note-body"><pre className="g-memory-text" style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{note.body}</pre></NamedTextBox>
              {(note.links_out.length > 0 || note.links_in.length > 0) && (
                <div className="g-links">
                  {note.links_out.length > 0 && <div><span className="g-muted">{t('memory.linksTo')}</span>{(note.links_out_status ?? note.links_out.map(t => ({ target: t, status: 'resolved', display: t }))).map(l =>
                    l.status === 'resolved'
                      ? <button key={l.target} className="g-link" onClick={() => open(`${l.target}.md`)}>{l.target}</button>
                      : <span key={l.target} className="g-muted" data-testid="link-unwritten" title={t('memory.noNoteYet')}>{l.display} </span>)}</div>}
                  {note.links_in.length > 0 && <div><span className="g-muted">{t('memory.linkedFrom')}</span>{note.links_in.map(l => <button key={l} className="g-link" onClick={() => open(`${l}.md`)}>{l.replace(/\.md$/, '')}</button>)}</div>}
                </div>
              )}
              {hist.length > 0 && (
                <div className="g-rows" style={{ marginTop: 10 }}>
                  {hist.slice(0, 5).map(c => <Row key={c.commit} lead={c.message} detail={`${c.author} · ${c.commit}`} when={ago(c.date)} />)}
                </div>
              )}
            </>
          )}
        </Panel>
      </div>
    </>
  )
}
