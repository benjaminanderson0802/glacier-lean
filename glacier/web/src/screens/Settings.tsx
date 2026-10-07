import { useEffect, useState } from 'react'
import { system, type SystemCheck } from '../api.ts'
import { Btn, Empty, PageHead, Panel, Row } from '../ui/kit.tsx'
import { go } from '../route.ts'
import { setLayout, useLayout, type Layout } from '../layout.ts'
import { AboutSection, DataSection, ModelsSection, SecretsSection, UsageSection } from './SettingsSections.tsx'

const SECTIONS = [
  { id: 'general', label: 'General' },
  { id: 'models', label: 'Models' },
  { id: 'secrets', label: 'Secrets' },
  { id: 'usage', label: 'Usage' },
  { id: 'data', label: 'Data' },
  { id: 'system', label: 'System check' },
  { id: 'help', label: 'Help & keys' },
  { id: 'about', label: 'About' },
] as const

export function SettingsScreen({ section = 'general' }: { section?: string }) {
  const layout = useLayout()
  const [check, setCheck] = useState<SystemCheck | null>(null)
  const [err, setErr] = useState('')
  const load = () => { setCheck(null); system.check().then(setCheck).catch(e => setErr(String(e))) }
  useEffect(load, [])
  const cur = SECTIONS.find(s => s.id === section) ?? SECTIONS[0]

  return (
    <>
      <PageHead title="Settings" sub={cur.id === 'system' ? 'Make sure everything is working.' : 'How Glacier runs on this computer.'} />
      <div className="g-settings">
        <Panel className="g-sidenav">
          {SECTIONS.map(s => <button key={s.id} className={`g-navitem${s.id === cur.id ? ' active' : ''}`} onClick={() => go(`settings/${s.id}`)} data-testid={`settings-${s.id}`}><span>{s.label}</span></button>)}
        </Panel>
        {cur.id === 'general' && (
          <Panel title="General" testid="settings-general">
            {err && <div className="g-error">{err}</div>}
            {!check ? <Empty>Checking this computer…</Empty> : (
              <dl className="g-kv">
                <dt>Mode</dt><dd>{check.recommended.mode === 'low' ? 'Light (one run at a time)' : 'Standard'}</dd>
                <dt>Local model</dt><dd>{check.recommended.local_model}</dd>
                <dt>Runs at once</dt><dd>{check.recommended.max_parallel_runs}</dd>
                <dt>Theme</dt><dd>Glacier (retro)</dd>
                <dt>Detail level</dt><dd>
                  <div className="g-seg" data-testid="layout-switch">
                    {([['simple', 'Simple'], ['standard', 'Standard'], ['full', 'Full']] as [Layout, string][]).map(([v, l]) =>
                      <button key={v} className={`g-seg-btn${v === layout ? ' active' : ''}`} onClick={() => setLayout(v)} data-testid={`layout-${v}`}>{l}</button>)}
                  </div>
                  <div className="g-muted">{layout === 'simple' ? 'Fewer step types and settings; nothing technical.' : layout === 'full' ? 'Everything, plus each step\'s raw settings in the editor.' : 'The usual view.'}</div>
                </dd>
              </dl>
            )}
          </Panel>
        )}
        {cur.id === 'system' && (
          <Panel title="System check" aside={<Btn onClick={load} data-testid="system-recheck">Run check again</Btn>} testid="settings-system">
            {err && <div className="g-error">{err}</div>}
            {!check ? <Empty>Checking…</Empty> : (
              <div className="g-rows">
                <Row status={check.ollama_models.length ? 'ok' : 'warn'} lead="Local AI models" detail={check.ollama_models.join(', ') || 'none installed'} when={check.ollama_models.length ? 'Ready' : 'Missing'} />
                {Object.entries(check.tools).map(([k, t]) => <Row key={k} status={t.found ? 'ok' : 'warn'} lead={k} detail={t.version || 'not found'} when={t.found ? 'Ready' : 'Missing'} />)}
                <Row status={check.disk_free_gb != null && check.disk_free_gb < 10 ? 'warn' : 'ok'} lead="Storage" detail={check.disk_free_gb != null ? `${check.disk_free_gb} GB free` : 'unknown'} />
                <Row status="ok" lead="Memory" detail={check.memory_gb != null ? `${check.memory_gb} GB` : 'unknown'} when={check.cpu_cores ? `${check.cpu_cores} cores` : ''} />
                {check.messages.map((m, i) => <Row key={i} status="warn" lead={m} />)}
              </div>
            )}
          </Panel>
        )}
        {cur.id === 'models' && <ModelsSection />}
        {cur.id === 'secrets' && <SecretsSection />}
        {cur.id === 'usage' && <UsageSection />}
        {cur.id === 'data' && <DataSection />}
        {cur.id === 'about' && <AboutSection version={__APP_VERSION__} />}
        {cur.id === 'help' && (
          <Panel title="Help & keys" testid="settings-help">
            <dl className="g-kv">
              <dt>Ctrl+K</dt><dd>Command palette: jump anywhere, run a flow</dd>
              <dt>Ctrl+Tab</dt><dd>Next tab (Shift for previous)</dd>
              <dt>Alt+1 … 5</dt><dd>Home, Ask, Automations, Memory, Settings</dd>
              <dt>F1</dt><dd>This page</dd>
            </dl>
          </Panel>
        )}
      </div>
    </>
  )
}
