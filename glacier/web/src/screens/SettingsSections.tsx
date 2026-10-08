// Settings sections beyond General / System check / Help: Models, Secrets, Usage, Data, About.
import { useEffect, useState } from 'react'
import { askSettingsApi, settingsApi, system, type AskSettings, type Costs, type EffectiveSettings, type SystemCheck, type VaultCompat } from '../api.ts'
import { Btn, Empty, Panel, Row } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'
import { t } from '../i18n/index.ts'

export function ModelsSection() {
  const [c, setC] = useState<SystemCheck | null>(null)
  const [eff, setEff] = useState<EffectiveSettings | null>(null)
  const [err, setErr] = useState('')
  const [ask, setAsk] = useState<AskSettings | null>(null)
  const [secretNames, setSecretNames] = useState<string[]>([])
  const [notice, setNotice] = useState('')
  useEffect(() => { system.check().then(setC).catch(e => setErr(String(e))); system.settings().then(setEff).catch(() => {}); askSettingsApi.get().then(setAsk).catch(() => {}); settingsApi.secrets().then(setSecretNames).catch(() => {}) }, [])
  const updateAsk = async (partial: Partial<AskSettings>) => {
    if (!ask) return
    try { setAsk(await askSettingsApi.save({ ...ask, ...partial })); setNotice('') }
    catch (e) { setNotice(String(e)) }
  }
  const forget = async () => {
    try { await askSettingsApi.forget(); window.dispatchEvent(new Event('glacier:forget-ask-chats')); setAsk(await askSettingsApi.get()); setNotice(t('settingsSections.chatsForgotten')) }
    catch (e) { setNotice(String(e)) }
  }
  return (
    <Panel title={t('settingsSections.models')} testid="settings-models">
      {err && <div className="g-error">{err}</div>}
      {!c ? <Empty>{t('settingsSections.checking')}</Empty> : (
        <>
          <dl className="g-kv">
            <dt>{t('settingsSections.usingNow')}</dt><dd data-testid="model-in-use">{eff?.local_model ?? c.recommended.local_model}</dd>
            <dt>{t('settingsSections.mode')}</dt><dd>{(eff?.mode ?? c.recommended.mode) === 'low' ? t('settingsSections.lightSmall') : t('settingsSections.standard')}</dd>
            <dt>{t('settingsSections.runsAtOnce')}</dt><dd>{eff?.max_parallel_runs ?? c.recommended.max_parallel_runs}</dd>
            <dt>{t('settingsSections.askUses')}</dt><dd data-testid="ask-route">{eff?.ask_route ? t(`settingsSections.askRoute.${eff.ask_route}`, { name: eff.local_model }) : t('settingsSections.checking')}</dd>
            <dt>{t('settingsSections.paidModels')}</dt><dd>{t('settingsSections.paidDescription')}</dd>
          </dl>
          <h3 className="g-panel-title" style={{ marginTop: 14 }}>{t('settingsSections.installed')}</h3>
          <div className="g-rows">
            {c.ollama_models.map(m => <Row key={m} status="ok" lead={m} when={m === (eff?.local_model ?? c.recommended.local_model) ? t('settingsSections.inUse') : ''} />)}
            {c.ollama_models.length === 0 && <Empty>{t('settingsSections.noLocalModels')}</Empty>}
          </div>
          {ask && <>
            <h3 className="g-panel-title" style={{ marginTop: 18 }}>{t('settingsSections.askEngine')}</h3>
            <div className="g-rows">
              <label className="g-row"><span className="g-mid"><span className="g-lead">{t('settingsSections.defaultEngine')}</span><span className="g-detail">{t('settingsSections.chooseEngineHelp')}</span></span>
                <select className="g-input" value={ask.engine} onChange={e => updateAsk({ engine: e.target.value })} data-testid="settings-ask-engine">
                  {ask.engines.map(engine => <option key={engine.id} value={engine.id}>{t(`ask.engine${engine.id[0].toUpperCase()}${engine.id.slice(1)}`)}{engine.available ? '' : ` — ${t('settingsSections.unavailable')}`}</option>)}
                </select>
              </label>
              <div className="g-detail" data-testid="ask-engine-reason">{ask.engines.find(x => x.id === ask.engine)?.available ? t('settingsSections.engineReady') : t(`settingsSections.engineUnavailable.${ask.engines.find(x => x.id === ask.engine)?.reason_code ?? 'missing'}`)}</div>
              {ask.engine === 'openai' && <>
                <label className="g-row"><span className="g-lead">{t('settingsSections.apiAddress')}</span><input className="g-input" value={ask.openai_base_url} onChange={e => setAsk({ ...ask, openai_base_url: e.target.value })} onBlur={() => updateAsk({ openai_base_url: ask.openai_base_url })} data-testid="openai-base-url" /></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.model')}</span><input className="g-input" value={ask.openai_model} onChange={e => setAsk({ ...ask, openai_model: e.target.value })} onBlur={() => updateAsk({ openai_model: ask.openai_model })} data-testid="openai-model" /></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.secretName')}</span><select className="g-input" value={ask.openai_secret_name} onChange={e => updateAsk({ openai_secret_name: e.target.value })} data-testid="openai-secret">{secretNames.map(n => <option key={n}>{n}</option>)}</select></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.monthlyApiCap')}</span><input type="number" min="0.01" step="0.01" className="g-input" value={ask.openai_monthly_cap_usd} onChange={e => setAsk({ ...ask, openai_monthly_cap_usd: e.target.value })} onBlur={() => updateAsk({ openai_monthly_cap_usd: ask.openai_monthly_cap_usd })} data-testid="openai-monthly-cap" /></label>
                <div className="g-detail">{t('settingsSections.apiSpendSoFar', { spent: Number(ask.openai_spend_usd).toFixed(4), cap: Number(ask.openai_monthly_cap_usd || 0).toFixed(2) })}</div>
                <label className="g-row"><span className="g-mid"><span className="g-lead">{t('settingsSections.inputPrice')}</span><span className="g-detail">{t('settingsSections.priceHelp')}</span></span><input type="number" min="0" step="0.01" className="g-input" value={ask.openai_input_usd_per_million} onChange={e => setAsk({ ...ask, openai_input_usd_per_million: e.target.value })} onBlur={() => updateAsk({ openai_input_usd_per_million: ask.openai_input_usd_per_million })} data-testid="openai-input-price" /></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.outputPrice')}</span><input type="number" min="0" step="0.01" className="g-input" value={ask.openai_output_usd_per_million} onChange={e => setAsk({ ...ask, openai_output_usd_per_million: e.target.value })} onBlur={() => updateAsk({ openai_output_usd_per_million: ask.openai_output_usd_per_million })} data-testid="openai-output-price" /></label>
              </>}
              {ask.engine === 'anthropic' && <>
                <label className="g-row"><span className="g-lead">{t('settingsSections.model')}</span><input className="g-input" value={ask.anthropic_model} onChange={e => setAsk({ ...ask, anthropic_model: e.target.value })} onBlur={() => updateAsk({ anthropic_model: ask.anthropic_model })} data-testid="anthropic-model" /></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.secretName')}</span><select className="g-input" value={ask.anthropic_secret_name} onChange={e => updateAsk({ anthropic_secret_name: e.target.value })} data-testid="anthropic-secret">{secretNames.map(n => <option key={n}>{n}</option>)}</select></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.monthlyApiCap')}</span><input type="number" min="0.01" step="0.01" className="g-input" value={ask.anthropic_monthly_cap_usd} onChange={e => setAsk({ ...ask, anthropic_monthly_cap_usd: e.target.value })} onBlur={() => updateAsk({ anthropic_monthly_cap_usd: ask.anthropic_monthly_cap_usd })} data-testid="anthropic-monthly-cap" /></label>
                <div className="g-detail">{t('settingsSections.apiSpendSoFar', { spent: Number(ask.anthropic_spend_usd).toFixed(4), cap: Number(ask.anthropic_monthly_cap_usd || 0).toFixed(2) })}</div>
                <label className="g-row"><span className="g-mid"><span className="g-lead">{t('settingsSections.inputPrice')}</span><span className="g-detail">{t('settingsSections.priceHelp')}</span></span><input type="number" min="0" step="0.01" className="g-input" value={ask.anthropic_input_usd_per_million} onChange={e => setAsk({ ...ask, anthropic_input_usd_per_million: e.target.value })} onBlur={() => updateAsk({ anthropic_input_usd_per_million: ask.anthropic_input_usd_per_million })} data-testid="anthropic-input-price" /></label>
                <label className="g-row"><span className="g-lead">{t('settingsSections.outputPrice')}</span><input type="number" min="0" step="0.01" className="g-input" value={ask.anthropic_output_usd_per_million} onChange={e => setAsk({ ...ask, anthropic_output_usd_per_million: e.target.value })} onBlur={() => updateAsk({ anthropic_output_usd_per_million: ask.anthropic_output_usd_per_million })} data-testid="anthropic-output-price" /></label>
              </>}
              {ask.engine === 'local' && <label className="g-row"><span className="g-lead">{t('settingsSections.installedModel')}</span><select className="g-input" value={ask.local_model || (c?.ollama_models.includes(c.recommended.local_model) ? c.recommended.local_model : c?.ollama_models[0] ?? '')} onChange={e => updateAsk({ local_model: e.target.value })} data-testid="ask-local-model">{(c?.ollama_models ?? []).map(model => <option key={model}>{model}</option>)}</select></label>}
              <label className="g-row"><span className="g-mid"><span className="g-lead">{t('settingsSections.rememberChats')}</span><span className="g-detail">{t('settingsSections.rememberChatsHelp')}</span></span><input type="checkbox" checked={ask.remember_previous_chats} onChange={e => updateAsk({ remember_previous_chats: e.target.checked })} data-testid="remember-previous-chats" /></label>
              <div className="g-row"><span className="g-detail">{t('settingsSections.forgetChatsHelp')}</span><Btn danger onClick={forget} data-testid="forget-previous-chats">{t('settingsSections.forgetChats')}</Btn></div>
              {notice && <div className="g-detail" role="status">{notice}</div>}
            </div>
          </>}
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
              ? <span style={{ display: 'flex', gap: 8 }}><Btn danger onClick={async () => { await settingsApi.deleteSecret(n); setConfirm(null); load() }} data-testid={`secret-del-yes-${n}`}>{t('settingsSections.remove')}</Btn><Btn onClick={() => setConfirm(null)}>{t('settingsSections.keep')}</Btn></span>
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
