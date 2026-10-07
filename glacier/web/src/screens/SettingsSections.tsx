// Settings sections beyond General / System check / Help: Models, Secrets, Usage, Data, About.
import { useEffect, useState } from 'react'
import { settingsApi, system, type Costs, type SystemCheck, type VaultCompat } from '../api.ts'
import { Btn, Empty, Panel, Row } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'

export function ModelsSection() {
  const [c, setC] = useState<SystemCheck | null>(null)
  const [eff, setEff] = useState<{ mode: string; local_model: string; max_parallel_runs: number } | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { system.check().then(setC).catch(e => setErr(String(e))); system.settings().then(setEff).catch(() => {}) }, [])
  return (
    <Panel title="Models" testid="settings-models">
      {err && <div className="g-error">{err}</div>}
      {!c ? <Empty>Checking…</Empty> : (
        <>
          <dl className="g-kv">
            <dt>Using now</dt><dd data-testid="model-in-use">{eff?.local_model ?? c.recommended.local_model}</dd>
            <dt>Mode</dt><dd>{(eff?.mode ?? c.recommended.mode) === 'low' ? 'Light: one run at a time, small model' : 'Standard'}</dd>
            <dt>Runs at once</dt><dd>{eff?.max_parallel_runs ?? c.recommended.max_parallel_runs}</dd>
            <dt>Paid models</dt><dd>Off. Free routes only; a paid option always comes to you as a proposal first.</dd>
          </dl>
          <h3 className="g-panel-title" style={{ marginTop: 14 }}>Installed on this computer</h3>
          <div className="g-rows">
            {c.ollama_models.map(m => <Row key={m} status="ok" lead={m} when={m === (eff?.local_model ?? c.recommended.local_model) ? 'in use' : ''} />)}
            {c.ollama_models.length === 0 && <Empty>No local models yet. Glacier can still use free online routes.</Empty>}
          </div>
        </>
      )}
    </Panel>
  )
}

export function SecretsSection() {
  const [names, setNames] = useState<string[] | null>(null)
  const [name, setName] = useState('')
  const [value, setValue] = useState('')
  const [msg, setMsg] = useState('')
  const [confirm, setConfirm] = useState<string | null>(null)
  const load = () => settingsApi.secrets().then(setNames).catch(e => setMsg(String(e)))
  useEffect(() => { load() }, [])
  const save = async () => {
    try { await settingsApi.setSecret(name.trim(), value); setMsg(`Saved ${name.trim()} in your computer's keychain.`); setName(''); setValue(''); load() }
    catch (e) { setMsg(String(e).replace(/^Error: /, '')) }
  }
  return (
    <Panel title="Secrets" testid="settings-secrets">
      <div className="g-detail" style={{ marginBottom: 8 }}>Passwords and keys that automations can use. They are stored in your computer's keychain and never shown again.</div>
      <div className="g-rows">
        {(names ?? []).map(n => (
          <div key={n} className="g-row" data-testid={`secret-${n}`}>
            <span className="g-ico"><Icon name="lock" /></span><span className="g-mid"><span className="g-lead">{n}</span><span className="g-detail">••••••••</span></span>
            <span className="g-when">{confirm === n
              ? <span style={{ display: 'flex', gap: 8 }}><Btn danger onClick={async () => { await settingsApi.deleteSecret(n); setConfirm(null); load() }} data-testid={`secret-del-yes-${n}`}>Remove</Btn><Btn onClick={() => setConfirm(null)}>Keep</Btn></span>
              : <Btn onClick={() => setConfirm(n)} data-testid={`secret-del-${n}`}>Remove</Btn>}</span>
          </div>
        ))}
        {names && names.length === 0 && <Empty>No secrets saved.</Empty>}
      </div>
      <form className="g-ask-row" style={{ marginTop: 12 }} onSubmit={e => { e.preventDefault(); save() }}>
        <input className="g-input" style={{ width: 220 }} placeholder="Name, e.g. GMAIL_APP_PASSWORD" value={name} onChange={e => setName(e.target.value)} data-testid="secret-name" />
        <input className="g-input" style={{ flex: 1 }} type="password" autoComplete="new-password" placeholder="Value" value={value} onChange={e => setValue(e.target.value)} data-testid="secret-value" />
        <Btn primary type="submit" disabled={!name.trim() || !value} data-testid="secret-save">Save</Btn>
      </form>
      {msg && <div className="g-detail" data-testid="secret-msg" style={{ marginTop: 6 }}>{msg}</div>}
    </Panel>
  )
}

export function UsageSection() {
  const [c, setC] = useState<Costs | null>(null)
  const [days, setDays] = useState(30)
  const [err, setErr] = useState('')
  useEffect(() => { settingsApi.costs(days).then(setC).catch(e => setErr(String(e))) }, [days])
  const tokens = (g: { tokens_in: number; tokens_out: number }) => (g.tokens_in + g.tokens_out).toLocaleString()
  return (
    <Panel title="Usage" aside={<span className="g-seg">{[7, 30, 90].map(d => <button key={d} className={`g-seg-btn${d === days ? ' active' : ''}`} onClick={() => setDays(d)}>{d}d</button>)}</span>} testid="settings-usage">
      {err && <div className="g-error">{err}</div>}
      {c && (
        <>
          <dl className="g-kv">
            <dt>Spent</dt><dd data-testid="usage-total">${c.total_usd.toFixed(2)}</dd>
            <dt>Paid limit</dt><dd>${c.paid_cap_usd.toFixed(2)} {c.paid_cap_usd === 0 ? '(free only)' : ''}</dd>
            <dt>Done on this computer</dt><dd>{Math.round(c.local_share * 100)}% of steps</dd>
          </dl>
          <table className="g-table" style={{ marginTop: 12 }}>
            <thead><tr><th>Model</th><th>Runs</th><th>Steps</th><th>Tokens</th><th>Cost</th></tr></thead>
            <tbody>{c.by_model.map(g => <tr key={g.model}><td className="g-lead">{g.model}</td><td>{g.runs}</td><td>{g.steps}</td><td>{tokens(g)}</td><td>${g.cost_usd.toFixed(2)}</td></tr>)}</tbody>
          </table>
          {c.by_model.length === 0 && <Empty>No AI steps in this period.</Empty>}
        </>
      )}
    </Panel>
  )
}

export function DataSection() {
  const [c, setC] = useState<VaultCompat | null>(null)
  const [err, setErr] = useState('')
  const load = () => { setC(null); settingsApi.compat().then(setC).catch(e => setErr(String(e))) }
  useEffect(load, [])
  return (
    <Panel title="Data" aside={<Btn onClick={load}>Check again</Btn>} testid="settings-data">
      <dl className="g-kv">
        <dt>Your memory</dt><dd>A folder of plain Markdown notes on this computer, with every change saved as a version you can undo.</dd>
        <dt>Open it elsewhere</dt><dd>The same folder works in Obsidian or any Markdown editor.</dd>
        <dt>Leaves this computer</dt><dd>Nothing, unless an automation you approved sends it.</dd>
      </dl>
      {err && <div className="g-error">{err}</div>}
      <div className="g-rows" style={{ marginTop: 12 }}>
        {c && <Row status={c.ok ? 'ok' : 'warn'} lead={c.ok ? 'Ready for Obsidian' : `${c.problems.length} thing${c.problems.length > 1 ? 's' : ''} to fix for Obsidian`} detail={`${c.notes_checked} notes checked`} testid="data-compat" />}
        {c?.problems.slice(0, 8).map((p, i) => <Row key={i} status="warn" lead={p.path} detail={`${p.detail} ${p.fix_hint}`} />)}
      </div>
    </Panel>
  )
}

export function AboutSection({ version }: { version: string }) {
  return (
    <Panel title="About" testid="settings-about">
      <dl className="g-kv">
        <dt>Glacier</dt><dd>version {version}</dd>
        <dt>Licence</dt><dd>Apache-2.0, free and open source</dd>
        <dt>Fonts</dt><dd>Pixelify Sans and VT323 (SIL Open Font License)</dd>
        <dt>Source</dt><dd>github.com/benjaminanderson0802/glacier-lean</dd>
      </dl>
    </Panel>
  )
}
