// Add to memory (mockup panel 11): drop files, write text, import ChatGPT / Claude chats, or save a coding-agent session.
import { useEffect, useRef, useState } from 'react'
import { addToMemory, ago, memory, sessionsApi, slugify, type CodingSession, type SessionEvent } from '../api.ts'
import { Btn, Empty, Panel, Row } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'

type Tab = 'files' | 'text' | 'chats' | 'sessions'
type Done = { name: string; ok: boolean; detail: string }

export function MemoryAdd() {
  const [tab, setTab] = useState<Tab>('files')
  const [files, setFiles] = useState<File[]>([])
  const [project, setProject] = useState('')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [source, setSource] = useState<'chatgpt' | 'claude'>('chatgpt')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<Done[]>([])
  const [over, setOver] = useState(false)
  const pick = useRef<HTMLInputElement>(null)
  const [imports, setImports] = useState<{ source: string; last_import: string | null; added: number; updated: number }[]>([])
  const loadImports = () => addToMemory.imports().then(setImports).catch(() => setImports([]))
  useEffect(() => { if (tab === 'chats') loadImports() }, [tab])
  const [sessions, setSessions] = useState<CodingSession[] | null>(null)
  const [sel, setSel] = useState<(CodingSession & { events: SessionEvent[] }) | null>(null)
  const [sessErr, setSessErr] = useState('')
  useEffect(() => { if (tab === 'sessions') { setSessErr(''); sessionsApi.list().then(setSessions).catch(e => { setSessions([]); setSessErr(String(e).replace(/^Error: /, '')) }) } }, [tab])
  const openSession = (id: string) => sessionsApi.get(id).then(setSel).catch(e => setSessErr(String(e).replace(/^Error: /, '')))
  const saveSession = async () => {
    if (!sel) return
    setBusy(true)
    try { const r = await sessionsApi.save(sel.id); setDone([{ name: sel.title || 'Session', ok: true, detail: r.saved ? `saved as ${r.path}` : 'already in memory' }]) }
    catch (e) { setDone([{ name: sel.title || 'Session', ok: false, detail: String(e).replace(/^Error: /, '') }]) }
    finally { setBusy(false) }
  }
  const toolName = (s: CodingSession) => ({ opencode: 'OpenCode', claude: 'Claude Code', 'claude-code': 'Claude Code', gemini: 'Gemini CLI' } as Record<string, string>)[s.source ?? ''] ?? 'Codex'
  const refresh = async () => {
    setBusy(true)
    try {
      const r = await addToMemory.refreshImports()
      const rows = Object.entries(r).map(([src, counts]) => ({ name: src === 'chatgpt' ? 'ChatGPT' : 'Claude', ok: true, detail: Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(', ') }))
      setDone(rows.length ? rows : [{ name: 'Chats', ok: true, detail: 'nothing new to import' }])
      loadImports()
    } catch (e) { setDone([{ name: 'Chats', ok: false, detail: String(e).replace(/^Error: /, '') }]) } finally { setBusy(false) }
  }

  const add = async () => {
    setBusy(true); const out: Done[] = []
    try {
      if (tab === 'text') {
        if (!title.trim() || !text.trim()) { out.push({ name: 'Note', ok: false, detail: 'Give it a title and some text.' }) }
        else { const r = await memory.save(`${slugify(title)}.md`, `# ${title.trim()}\n\n${text}`); out.push({ name: title, ok: true, detail: `saved (version ${r.commit})` }); setTitle(''); setText('') }
      } else {
        for (const f of files) {
          try {
            if (tab === 'chats') {
              const r = await addToMemory.chatExport(source, f)
              out.push({ name: f.name, ok: true, detail: Object.entries(r).map(([k, v]) => `${v} ${k}`).join(', ') || 'imported' })
            } else {
              const r = await addToMemory.file(f, project.trim() || undefined)
              out.push({ name: f.name, ok: true, detail: r.duplicate ? 'already in memory' : 'added' })
            }
          } catch (e) { out.push({ name: f.name, ok: false, detail: String(e).replace(/^Error: /, '') }) }
        }
        setFiles([])
      }
    } finally { setDone(out); setBusy(false) }
  }

  return (
    <div className="g-memadd">
      <Panel testid="memory-add">
        <div className="g-seg" style={{ alignSelf: 'flex-start', marginBottom: 12 }}>
          {([['files', 'Files'], ['text', 'Text'], ['chats', 'Chat import'], ['sessions', 'Coding sessions']] as [Tab, string][]).map(([t, l]) =>
            <button key={t} className={`g-seg-btn${t === tab ? ' active' : ''}`} onClick={() => { setTab(t); setDone([]) }} data-testid={`add-tab-${t}`}>{l}</button>)}
        </div>
        {tab === 'sessions' ? (
          <div className="g-rows g-scroll" data-testid="sessions-list">
            {sessErr && <div className="g-error">{sessErr}</div>}
            {sessions === null ? <Empty>Looking for coding sessions…</Empty> : sessions.length === 0 ? <Empty>No coding-agent sessions found on this computer.</Empty> :
              sessions.map((x, i) => (
                <button key={x.id} type="button" className={`g-row${sel?.id === x.id ? ' sel' : ''}`} onClick={() => openSession(x.id)} data-testid={`session-${i}`}>
                  <span className="g-ico"><Icon name="run" /></span>
                  <span className="g-mid"><span className="g-lead">{x.title || 'Untitled session'}</span><span className="g-detail">{toolName(x)}{x.cwd ? ` · ${x.cwd}` : ''}{x.active ? ' · running now' : ''}</span></span>
                  <span className="g-when">{x.updated ? ago(x.updated) : ''}</span>
                </button>))}
          </div>
        ) : tab === 'text' ? (
          <div className="g-editor">
            <input className="g-input" placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} data-testid="add-title" />
            <textarea className="g-input g-textarea" style={{ minHeight: 220 }} placeholder="Paste or type anything you want Glacier to remember." value={text} onChange={e => setText(e.target.value)} data-testid="add-text" />
          </div>
        ) : (
          <div className={`g-drop${over ? ' over' : ''}`} data-testid="add-drop" onClick={() => pick.current?.click()}
            onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); const dropped = Array.from(e.dataTransfer.files); setFiles(f => [...f, ...dropped]) }}>
            <Icon name="note" px={5} />
            <span className="g-lead">{files.length ? `${files.length} file${files.length > 1 ? 's' : ''} ready` : 'Drop files here'}</span>
            <span className="g-detail">{files.length ? files.map(f => f.name).join(', ') : 'or click to browse'}</span>
            <input ref={pick} type="file" multiple hidden accept={tab === 'chats' ? '.zip,.json' : undefined} data-testid="add-input"
              onChange={e => { const picked = Array.from(e.target.files ?? []); setFiles(f => [...f, ...picked]); e.target.value = '' }} />
          </div>
        )}
        <div className="g-detail" style={{ marginTop: 10 }}>{tab === 'sessions' ? 'Your Codex, OpenCode, Claude Code and Gemini CLI sessions, read-only. Glacier never changes them. Secrets are hidden.' : tab === 'chats' ? 'Use the export file from ChatGPT or Claude (Settings > Data export). Duplicates are skipped.' : tab === 'files' ? 'Supports PDF, Word, text, Markdown, spreadsheets and images. Text is extracted so it can be searched.' : 'Saved as a plain note you can edit later.'}</div>
      </Panel>
      <Panel title={tab === 'sessions' ? 'Session' : 'Options'} testid="add-options">
        {tab === 'files' && <label className="g-field"><span className="g-detail">Add to project (optional)</span><input className="g-input" value={project} onChange={e => setProject(e.target.value)} placeholder="None" data-testid="add-project" /></label>}
        {tab === 'chats' && imports.length > 0 && (
          <div className="g-rows" style={{ marginBottom: 10 }} data-testid="import-history">
            {imports.map(i => <div key={i.source} className="g-row"><span className="g-ico" /><span className="g-mid"><span className="g-lead">{i.source === 'chatgpt' ? 'ChatGPT' : 'Claude'}</span><span className="g-detail">{i.added} added, {i.updated} updated</span></span><span className="g-when">{i.last_import ? ago(i.last_import) : ''}</span></div>)}
            <Btn onClick={refresh} disabled={busy} data-testid="import-refresh" style={{ marginTop: 8 }}>Check for new chats</Btn>
          </div>
        )}
        {tab === 'chats' && (
          <div className="g-seg" style={{ alignSelf: 'flex-start' }}>
            {(['chatgpt', 'claude'] as const).map(s => <button key={s} className={`g-seg-btn${s === source ? ' active' : ''}`} onClick={() => setSource(s)}>{s === 'chatgpt' ? 'ChatGPT' : 'Claude'}</button>)}
          </div>
        )}
        {tab === 'sessions' ? (
          sel ? (
            <div data-testid="session-detail">
              <div className="g-lead">{sel.title || 'Untitled session'}</div>
              <div className="g-detail">{toolName(sel)} · {sel.events.length} step{sel.events.length === 1 ? '' : 's'}{sel.started ? ` · started ${ago(sel.started)}` : ''}</div>
              <div className="g-rows g-scroll" style={{ maxHeight: 360, marginTop: 8 }}>
                {sel.events.slice(0, 40).map((ev, i) => <Row key={i} icon={ev.type === 'user_message' ? 'ask' : ev.type === 'assistant_message' ? 'automations' : ev.type.startsWith('command') ? 'run' : 'note'} lead={ev.type === 'user_message' ? 'You' : ev.type === 'assistant_message' ? toolName(sel) : ev.type === 'command' ? 'Command' : ev.type === 'command_output' ? 'Output' : 'Step'} detail={ev.text.slice(0, 160)} />)}
              </div>
              <Btn primary onClick={saveSession} disabled={busy} data-testid="session-save" style={{ marginTop: 12 }}>Save to memory</Btn>
            </div>
          ) : <Empty>Pick a session to see it here.</Empty>
        ) : <Btn primary onClick={add} disabled={busy || (tab !== 'text' && files.length === 0)} data-testid="add-go" style={{ marginTop: 12 }}>Add to memory</Btn>}
        <div className="g-rows" style={{ marginTop: 10 }}>
          {done.map((d, i) => <Row key={i} status={d.ok ? 'ok' : 'bad'} lead={d.name} detail={d.detail} testid={`add-result-${i}`} />)}
        </div>
        {done.some(d => d.ok) && <button className="g-link" onClick={() => go('memory')}>See it in Notes</button>}
      </Panel>
    </div>
  )
}
