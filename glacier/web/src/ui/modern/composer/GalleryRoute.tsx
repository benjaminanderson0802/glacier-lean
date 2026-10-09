import { useCallback, useState } from 'react'
import { Composer, type ComposerEngine, type ComposerMode } from './Composer.tsx'
import './gallery.css'

const engineOptions: ComposerEngine[] = [
  { id: 'subscription', label: 'Codex subscription', kind: 'subscription', status: 'ready', detail: 'Signed in · included' },
  { id: 'api', label: 'OpenAI API', kind: 'api', status: 'busy', detail: 'API route · monthly cap set' },
  { id: 'local', label: 'Local · granite', kind: 'local', status: 'ready', detail: 'On this computer' },
]
const commandOptions = [
  { id: 'search', label: 'Search memory', description: 'Find a note or saved conversation', insert: '/search ' },
  { id: 'flow', label: 'Open a flow', description: 'Find and open an automation', insert: '/flow ' },
  { id: 'help', label: 'Show help', description: 'Learn what you can ask Glacier', insert: '/help ' },
]
const results = [
  { id: 'flow-1', label: 'Weekly research digest', kind: 'flow' as const, detail: 'Automation · runs every Monday' },
  { id: 'note-1', label: 'Research sources', kind: 'note' as const, detail: 'Memory · updated yesterday' },
  { id: 'chat-1', label: 'Research planning', kind: 'chat' as const, detail: 'Chat · 8 messages' },
]

export default function GalleryRoute() {
  const [sent, setSent] = useState('')
  const [busy, setBusy] = useState(false)
  const [engine, setEngine] = useState<ComposerEngine>(engineOptions[0])
  const [mode, setMode] = useState<ComposerMode>('chat')
  const [attachments, setAttachments] = useState(0)
  const searchMentions = useCallback(async (query: string) => results.filter(row => row.label.toLowerCase().includes(query.toLowerCase())), [])
  return <main className="dg-gallery">
    <div className="dg-gallery-glow" aria-hidden="true" />
    <header className="dg-gallery-header"><div className="dg-gallery-mark"><span className="dg-gallery-glyph">✧</span></div><div><div className="dg-gallery-eyebrow">GLACIER <span>/</span> BUILD</div><h1>Clip revenue loop</h1></div><div className="dg-gallery-header-side"><span className="dg-gallery-pill"><i /> Interview · 3 of ~6</span><span className="dg-gallery-pill">{engine.label}</span></div></header>
    <section className="dg-gallery-thread" aria-label="Conversation">
      <div className="dg-gallery-intro"><span className="dg-gallery-avatar">G</span><div><p className="dg-gallery-kicker">GLACIER · INTERVIEWER</p><h2>Let’s shape the goal together.</h2><p>Tell Glacier what you want to build. You can add files, reference saved work, or switch engines at any time.</p><div className="dg-gallery-suggestions"><button onClick={() => { setSent('Build an automation that watches a folder and summarizes new files.'); setMode('build') }}>Build an automation <span>↗</span></button><button onClick={() => setSent('Help me find a note in memory.')}>Search my memory <span>↗</span></button></div></div></div>
      {sent && <div className="dg-gallery-message" data-testid="sent-message"><span>{sent}</span><small>Just now</small></div>}
      {busy && <div className="dg-gallery-reply"><span className="dg-gallery-avatar">G</span><span className="dg-gallery-thinking"><i /><i /><i /> Glacier is thinking</span></div>}
    </section>
    <div className="dg-gallery-compose-wrap"><Composer engines={engineOptions} engineId={engine.id} onEngineChange={setEngine} mode={mode} onModeChange={setMode} commands={commandOptions} searchMentions={searchMentions} contextUsage={{ used: 1800, total: 10000 }} busy={busy} maxAttachments={8} onSend={(text, items) => { setAttachments(items.length); setSent(text || `${items.length} attachment${items.length === 1 ? '' : 's'}`); setBusy(true); window.setTimeout(() => setBusy(false), 1200) }} onStop={() => setBusy(false)} />
      <div className="dg-gallery-compose-note">{attachments ? `${attachments} file${attachments === 1 ? '' : 's'} included` : 'Your files stay on this computer until you choose to send them.'}</div>
    </div>
  </main>
}
