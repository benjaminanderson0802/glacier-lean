import { useEffect, useMemo, useState } from 'react'
import { api, type EnvSummary } from '../api.ts'
import { Panel } from '../ui/kit.tsx'
import { Icon, type IconName } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'

type Cmd = { label: string; icon: IconName; hint?: string; run: () => void }

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const [flows, setFlows] = useState<EnvSummary[]>([])
  useEffect(() => { api.listEnvs().then(setFlows).catch(() => {}) }, [])

  const cmds = useMemo<Cmd[]>(() => [
    { label: t('command.goHome'), icon: 'home', hint: 'Alt+1', run: () => go('home') },
    { label: t('command.askAssistant'), icon: 'ask', hint: 'Alt+2', run: () => go('ask') },
    { label: t('command.automations'), icon: 'automations', hint: 'Alt+3', run: () => go('automations') },
    { label: t('command.searchMemory'), icon: 'search', hint: 'Alt+4', run: () => go('memory') },
    { label: t('command.settings'), icon: 'settings', hint: 'Alt+5', run: () => go('settings') },
    { label: t('command.system'), icon: 'settings', run: () => go('settings/system') },
    { label: t('command.help'), icon: 'note', hint: 'F1', run: () => go('settings/help') },
    ...flows.map(f => ({ label: t('command.openFlow', { name: f.name }), icon: 'run' as IconName, run: () => go(`automations/flow/${f.id}`) })),
  ], [flows])
  const shown = cmds.filter(c => c.label.toLowerCase().includes(q.toLowerCase())).slice(0, 9)
  const pick = (c?: Cmd) => { if (c) { c.run(); onClose() } }

  return (
    <div className="g-scrim" onClick={onClose} data-testid="command-palette">
      <Panel className="g-palette">
        <div onClick={e => e.stopPropagation()}>
          <input className="g-input" autoFocus placeholder={t('command.search')} value={q} data-testid="command-input"
            onChange={e => { setQ(e.target.value); setSel(0) }}
            onKeyDown={e => {
              if (e.key === 'Escape') onClose()
              else if (e.key === 'ArrowDown') { e.preventDefault(); setSel(s => Math.min(shown.length - 1, s + 1)) }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(s => Math.max(0, s - 1)) }
              else if (e.key === 'Enter') pick(shown[sel])
            }} />
          <div className="g-rows" style={{ marginTop: 8 }}>
            {shown.map((c, i) => (
              <button key={c.label} type="button" className={`g-row${i === sel ? ' sel' : ''}`} onMouseEnter={() => setSel(i)} onClick={() => pick(c)}>
                <span className="g-ico"><Icon name={c.icon} /></span><span className="g-lead">{c.label}</span><span className="g-when">{c.hint}</span>
              </button>
            ))}
          </div>
        </div>
      </Panel>
    </div>
  )
}
