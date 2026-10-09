import { useEffect, useMemo, useRef, useState } from 'react'
import { getActions, subscribeRegistry, type RegisteredAction } from './keys'
import './overlays.css'

function score(action: RegisteredAction, query: string): number {
  const words = `${action.label} ${action.group} ${(action.keywords ?? []).join(' ')}`.toLowerCase()
  const q = query.trim().toLowerCase()
  if (!q) return 1
  if (words.includes(q)) return 90 - words.indexOf(q)
  let cursor = 0, gaps = 0
  for (const char of q) {
    const found = words.indexOf(char, cursor)
    if (found < 0) return 0
    gaps += found - cursor
    cursor = found + 1
  }
  return Math.max(1, 60 - gaps - words.length * .01)
}

export function CommandPalette({ open, onClose, actions: extraActions = [] }: { open: boolean; onClose: () => void; actions?: RegisteredAction[] }) {
  const [query, setQuery] = useState(() => sessionStorage.getItem('glacier.palette.query') ?? '')
  const [active, setActive] = useState(0)
  const [version, setVersion] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => subscribeRegistry(() => setVersion(v => v + 1)), [])
  useEffect(() => { if (open) requestAnimationFrame(() => input.current?.focus()) }, [open])
  useEffect(() => {
    const close = () => onClose()
    window.addEventListener('glacier:close-overlays', close)
    return () => window.removeEventListener('glacier:close-overlays', close)
  }, [onClose])

  const results = useMemo(() => [...getActions(), ...extraActions]
    .map((action, index) => ({ action, index, score: score(action, query) }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .slice(0, 12), [extraActions, query, version])
  useEffect(() => setActive(0), [query])
  if (!open) return null

  const choose = (action?: RegisteredAction) => {
    if (!action) return
    sessionStorage.setItem('glacier.palette.query', query)
    action.run()
    onClose()
  }
  const groups = [...new Set(results.map(item => item.action.group))]
  return <div className="gm-scrim" data-testid="command-palette-scrim" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="gm-palette gm-glass" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={event => event.stopPropagation()}>
      <div className="gm-palette-search">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
        <input ref={input} data-testid="command-query" aria-label="Search commands" placeholder="Search Glacier…" value={query}
          onChange={event => setQuery(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'ArrowDown') { event.preventDefault(); setActive(index => Math.min(results.length - 1, index + 1)) }
            else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => Math.max(0, index - 1)) }
            else if (event.key === 'Enter') { event.preventDefault(); choose(results[active]?.action) }
            else if (event.key === 'Escape') { event.preventDefault(); onClose() }
          }} />
        <span className="gm-kbd">ESC</span>
      </div>
      <div className="gm-results" role="listbox" aria-label="Results">
        {results.length ? groups.map(group => <div className="gm-group" key={group}>
          <div className="gm-section-label">{group}</div>
          {results.filter(item => item.action.group === group).map(({ action }) => {
            const globalIndex = results.findIndex(item => item.action === action)
            return <button key={action.id} type="button" className={`gm-result${active === globalIndex ? ' is-active' : ''}`} role="option" aria-selected={active === globalIndex}
              data-testid="command-result" onMouseEnter={() => setActive(globalIndex)} onClick={() => choose(action)}>
              <span className="gm-result-icon">{action.icon ?? '✧'}</span><span className="gm-result-copy"><strong>{action.label}</strong>{action.keywords?.[0] && <small>{action.keywords[0]}</small>}</span>
              {action.shortcut && <kbd className="gm-kbd">{action.shortcut}</kbd>}
            </button>
          })}
        </div>) : <div className="gm-no-results">No matching commands</div>}
      </div>
      <footer className="gm-palette-foot"><span><kbd className="gm-kbd">↑</kbd><kbd className="gm-kbd">↓</kbd> to move</span><span><kbd className="gm-kbd">↵</kbd> to open</span><span><kbd className="gm-kbd">ESC</kbd> to close</span></footer>
    </section>
  </div>
}
