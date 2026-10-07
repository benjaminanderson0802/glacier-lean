import { tok } from '../ui/tok.ts'
import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'

/** Read-only xterm.js view of one node's output. Re-renders the whole text when it changes. */
export function TerminalPanel({ text }: { text: string }) {
  const host = useRef<HTMLDivElement>(null)
  const term = useRef<Terminal | null>(null)

  useEffect(() => {
    const t = new Terminal({
      convertEol: true,
      disableStdin: true,
      rows: 12,
      theme: { background: tok('--g-void'), foreground: tok('--g-text'), cursor: tok('--g-void') }, fontFamily: tok('--g-font-body'), fontSize: 18,
    })
    t.open(host.current!)
    term.current = t
    return () => { t.dispose(); term.current = null }
  }, [])

  useEffect(() => {
    const t = term.current
    if (!t) return
    t.reset()
    t.write(text || '(no output)')
  }, [text])

  return <div className="terminal-host" ref={host} data-testid="terminal" data-text={text} />
}
