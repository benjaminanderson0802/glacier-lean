import { useState } from 'react'

export function ToolCard({ id, name, status, duration, output }: { id: string; name: string; status: 'running' | 'ok' | 'failed'; duration?: string; output?: string }) {
  const [open, setOpen] = useState(status === 'running')
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(output ?? '').catch(() => {})
    setCopied(true); setTimeout(() => setCopied(false), 1200)
  }
  return <section className="thread-tool" data-testid="tool-card" data-status={status}>
    <button type="button" className="thread-tool-head" aria-expanded={open} aria-controls={`tool-${id}`} onClick={() => setOpen(x => !x)}>
      <span className="thread-tool-glyph">⌘</span><strong>{name}</strong>
      <span className={`thread-tool-state ${status}`}><i />{status === 'running' ? 'Running' : status === 'ok' ? 'Complete' : 'Failed'}</span>
      {duration && <span className="thread-tool-duration">{duration}</span>}<span className="thread-disclosure">{open ? '−' : '+'}</span>
    </button>
    {open && <div className="thread-tool-output" id={`tool-${id}`}>
      <div className="thread-output-head"><span>Output</span><button type="button" onClick={copy} aria-label="Copy tool output">{copied ? 'Copied' : 'Copy'}</button></div>
      <pre>{output || (status === 'running' ? 'Waiting for a result…' : 'No output')}</pre>
    </div>}
  </section>
}
