// Settings sections beyond General / System check / Help: Models, Secrets, Usage, Data, About.
import { useEffect, useState } from 'react'
import { settingsApi, system, type Costs, type EffectiveSettings, type SystemCheck, type VaultCompat } from '../api.ts'
import { Btn, Empty, Panel, Row } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'
import { t } from '../i18n/index.ts'

export function ModelsSection() {
  const [c, setC] = useState<SystemCheck | null>(null)
  const [eff, setEff] = useState<EffectiveSettings | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { system.check().then(setC).catch(e => setErr(String(e))); system.settings().then(setEff).catch(() => {}) }, [])
  return (
    <Panel title={t('settingsSections.models')} testid="settings-models">
      {err && <div className="g-error">{err}</div>}
      {!c ? <Empty>{t('settingsSections.checking')}</Empty> : (
        <>
          <dl className="g-kv">
            <dt>{t('settingsSections.usingNow')}</dt><dd data-testid="model-in-use">{eff?.local_model ?? c.recommended.local_model}</dd>
            <dt>{t('settingsSections.mode')}</dt><dd>{(eff?.mode ?? c.recommended.mode) === 'low' ? t('settingsSections.lightSmall') : t('settingsSections.standard')}</dd>
            <dt>{t('settingsSections.runsAtOnce')}</dt><dd>{eff?.max_parallel_runs ?? c.recommended.max_parallel_runs}</dd>
            <dt>{t('settingsSections.askUses')}</dt><dd data-testid="ask-route">{eff?.ask_route === 'codex' ? t('settingsSections.codexPlan') : eff?.ask_route === 'local' ? t('settingsSections.localRoute', { name: eff.local_model }) : eff?.ask_route === 'unavailable' ? 'Nothing yet' : 'Checking…'}{eff?.ask_route_reason ? <div className="g-muted">{eff.ask_route_reason}</div> : null}</dd>
            <dt>{t('settingsSections.paidModels')}</dt><dd>{t('settingsSections.paidDescription')}</dd>
          </dl>
          <h3 className="g-panel-title" style={{ marginTop: 14 }}>{t('settingsSections.installed')}</h3>
          <div className="g-rows">
            {c.ollama_models.map(m => <Row key={m} status="ok" lead={m} when={m === (eff?.local_model ?? c.recommended.local_model) ? t('settingsSections.inUse') : ''} />)}
            {c.ollama_models.length === 0 && <Empty>{t('settingsSections.noLocalModels')}</Empty>}
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
    try { await settingsApi.setSecret(name.trim(), value); setMsg(t('settingsSections.savedSecret', { name: name.trim() })); setName(''); setValue(''); load() }
    catch (e) { setMsg(String(e).replace(/^Error: /, '')) }
  }
  return (
    <Panel title={t('settingsSections.secrets')} testid="settings-secrets">
      <div className="g-detail" style={{ marginBottom: 8 }}>{t('settingsSections.secretDescription')}</div>
      <div className="g-rows">
        {(names ?? []).map(n => (
          <div key={n} className="g-row" data-testid={`secret-${n}`}>
            <span className="g-ico"><Icon name="lock" /></span><span className="g-mid"><span className="g-lead">{n}</span><span className="g-detail">••••••••</span></span>
            <span className="g-when">{confirm === n
              ? <span style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}><span className="g-detail">{t('delete.secretImpact')}</span><Btn danger onClick={async () => { try { await settingsApi.deleteSecret(n); setConfirm(null); setMsg(t('delete.removed')); load() } catch (e) { setMsg(String(e).replace(/^Error: /, '')) } }} data-testid={`secret-del-yes-${n}`}>{t('delete.confirm')}</Btn><Btn onClick={() => setConfirm(null)}>{t('delete.cancel')}</Btn></span>
              : <Btn onClick={() => setConfirm(n)} data-testid={`secret-del-${n}`}>{t('settingsSections.remove')}</Btn>}</span>
          </div>
        ))}
        {names && names.length === 0 && <Empty>{t('settingsSections.noSecrets')}</Empty>}
      </div>
      <form className="g-ask-row" style={{ marginTop: 12 }} onSubmit={e => { e.preventDefault(); save() }}>
        <input className="g-input" style={{ width: 220 }} placeholder={t('settingsSections.namePlaceholder')} value={name} onChange={e => setName(e.target.value)} data-testid="secret-name" />
        <input className="g-input" style={{ flex: 1 }} type="password" autoComplete="new-password" placeholder={t('settingsSections.value')} value={value} onChange={e => setValue(e.target.value)} data-testid="secret-value" />
        <Btn primary type="submit" disabled={!name.trim() || !value} data-testid="secret-save">{t('settingsSections.save')}</Btn>
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
    <Panel title={t('settingsSections.usage')} aside={<span className="g-seg">{[7, 30, 90].map(d => <button key={d} className={`g-seg-btn${d === days ? ' active' : ''}`} onClick={() => setDays(d)}>{d}{t('settingsSections.daysSuffix')}</button>)}</span>} testid="settings-usage">
      {err && <div className="g-error">{err}</div>}
      {c && (
        <>
          <dl className="g-kv">
            <dt>{t('settingsSections.spent')}</dt><dd data-testid="usage-total">${c.total_usd.toFixed(2)}</dd>
            <dt>{t('settingsSections.paidLimit')}</dt><dd>${c.paid_cap_usd.toFixed(2)} {c.paid_cap_usd === 0 ? t('settingsSections.freeOnly') : ''}</dd>
            <dt>{t('settingsSections.doneHere')}</dt><dd>{t('settingsSections.localShare', { count: Math.round(c.local_share * 100) })}</dd>
          </dl>
          <table className="g-table" style={{ marginTop: 12 }}>
            <thead><tr><th>{t('settingsSections.model')}</th><th>{t('settingsSections.runs')}</th><th>{t('settingsSections.stepsLabel')}</th><th>{t('settingsSections.tokens')}</th><th>{t('settingsSections.cost')}</th></tr></thead>
            <tbody>{c.by_model.map(g => <tr key={g.model}><td className="g-lead">{g.model}</td><td>{g.runs}</td><td>{g.steps}</td><td>{tokens(g)}</td><td>${g.cost_usd.toFixed(2)}</td></tr>)}</tbody>
          </table>
          {c.by_model.length === 0 && <Empty>{t('settingsSections.noAiSteps')}</Empty>}
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
    <Panel title={t('settingsSections.data')} aside={<Btn onClick={load}>{t('settingsSections.checkAllKeys')}</Btn>} testid="settings-data">
      <dl className="g-kv">
        <dt>{t('settingsSections.yourMemory')}</dt><dd>{t('settingsSections.memoryDescription')}</dd>
        <dt>{t('settingsSections.openElsewhere')}</dt><dd>{t('settingsSections.openDescription')}</dd>
        <dt>{t('settingsSections.leavesComputer')}</dt><dd>{t('settingsSections.leavesNothing')}</dd>
      </dl>
      {err && <div className="g-error">{err}</div>}
      <div className="g-rows" style={{ marginTop: 12 }}>
        {c && <Row status={c.ok ? 'ok' : 'warn'} lead={c.ok ? t('settingsSections.readyObsidian') : t('settingsSections.thingsToFix', { count: c.problems.length, plural: c.problems.length > 1 ? 's' : '' })} detail={t('settingsSections.notesChecked', { count: c.notes_checked })} testid="data-compat" />}
        {c?.problems.slice(0, 8).map((p, i) => <Row key={i} status="warn" lead={p.path} detail={`${p.detail} ${p.fix_hint}`} />)}
      </div>
    </Panel>
  )
}

export function AboutSection({ version }: { version: string }) {
  const [update, setUpdate] = useState<{ version: string; notes: string } | null>(null)
  const [state, setState] = useState<'idle' | 'checking' | 'current' | 'available' | 'installing' | 'restart' | 'error'>('idle')
  const [error, setError] = useState('')
  const desktop = typeof window !== 'undefined' && Boolean(window.glacierUpdater)
  const checkForUpdates = async () => {
    if (!window.glacierUpdater) return
    setState('checking'); setError(''); setUpdate(null)
    try {
      const found = await window.glacierUpdater.check()
      setUpdate(found)
      setState(found ? 'available' : 'current')
    } catch {
      setState('error'); setError(t('settingsSections.updateError'))
    }
  }
  const installUpdate = async () => {
    if (!update || !window.glacierUpdater) return
    setState('installing'); setError('')
    try { await window.glacierUpdater.install(update.version); setState('restart') }
    catch { setState('error'); setError(t('settingsSections.installError')) }
  }
  useEffect(() => {
    if (desktop) void checkForUpdates()
  }, [desktop])
  return (
    <Panel title={t('settingsSections.about')} testid="settings-about">
      <dl className="g-kv">
        <dt>{t('settingsSections.glacier')}</dt><dd data-testid="settings-version">{t('settingsSections.version', { version })}</dd>
        <dt>{t('settingsSections.licence')}</dt><dd>{t('settingsSections.licenceValue')}</dd>
        <dt>{t('settingsSections.fonts')}</dt><dd>{t('settingsSections.fontsValue')}</dd>
        <dt>{t('settingsSections.source')}</dt><dd>{t('settingsSections.repo')}</dd>
      </dl>
      <h3 className="g-panel-title" style={{ marginTop: 14 }}>{t('settingsSections.updates')}</h3>
      {!desktop ? <div className="g-detail" data-testid="update-browser">{t('settingsSections.updateDesktopOnly')}</div> : (
        <div className="g-stack" style={{ gap: 8 }}>
          <div className="g-detail">{state === 'checking' && t('settingsSections.updateChecking')}{state === 'current' && <span data-testid="update-current">{t('settingsSections.upToDate')}</span>}{state === 'available' && <span>{t('settingsSections.updateAvailable', { version: update?.version ?? '' })}</span>}{state === 'installing' && t('settingsSections.updateInstalling')}{state === 'restart' && <span data-testid="update-restart">{t('settingsSections.updateRestart')}</span>}{state === 'error' && <span data-testid="update-error">{error}</span>}</div>
          {state === 'available' && update && <div className="g-detail" data-testid="update-notes" style={{ whiteSpace: 'pre-wrap' }}>{update.notes}</div>}
          {state === 'available' && <Btn primary onClick={installUpdate} data-testid="update-install">{t('settingsSections.updateInstall')}</Btn>}
          {state !== 'installing' && <Btn onClick={checkForUpdates} disabled={state === 'checking'} data-testid="update-check">{t('settingsSections.updateCheck')}</Btn>}
        </div>
      )}
    </Panel>
  )
}
