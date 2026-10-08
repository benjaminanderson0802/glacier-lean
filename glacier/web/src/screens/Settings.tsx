import { useEffect, useState } from 'react'
import { system, type SystemCheck } from '../api.ts'
import { Btn, Empty, Hint, HintBar, KeyboardMenu, PageHead, Panel, Row, Window } from '../ui/kit.tsx'
import { go } from '../route.ts'
import { setLayout, useLayout, type Layout } from '../layout.ts'
import { AboutSection, DataSection, ModelsSection, SecretsSection, UsageSection } from './SettingsSections.tsx'
import { chooseDictionary, getLanguage, subscribeLanguage, t, type Language } from '../i18n/index.ts'

const SECTION_LABELS: Record<string, string> = {
  general: 'settings.general', models: 'settings.models', secrets: 'settings.navSecrets', usage: 'settings.usage',
  data: 'settings.data', system: 'settings.navSystem', help: 'settings.navHelp', about: 'settings.about',
}

export function SettingsScreen({ section = 'general' }: { section?: string }) {
  const layout = useLayout()
  const [check, setCheck] = useState<SystemCheck | null>(null)
  const [err, setErr] = useState('')
  const [language, setLanguage] = useState<Language>(getLanguage())
  const load = () => { setCheck(null); system.check().then(setCheck).catch(e => setErr(String(e))) }
  useEffect(load, [])
  useEffect(() => subscribeLanguage(() => setLanguage(getLanguage())), [])
  const sections = Object.entries(SECTION_LABELS).map(([id, key]) => ({ id, label: t(key) }))
  const cur = sections.find(s => s.id === section) ?? sections[0]

  return (
    <>
      <PageHead title={t('settings.title')} sub={cur.id === 'system' ? t('settings.systemSubtitle') : t('settings.subtitle')} />
      <div className="g-settings" style={{ display: 'grid', gridTemplateColumns: 'calc(88 * var(--px)) minmax(0, 1fr)', gap: 'calc(2 * var(--px))', flex: 1 }}>
        <Window className="g-sidenav" title={t('settings.sections')}>
          <KeyboardMenu label={t('settings.sections')} items={sections.map(s => ({ id: s.id, label: s.label, testid: `settings-${s.id}` }))} selected={cur.id} onSelect={id => go(`settings/${id}`)} />
        </Window>
        {cur.id === 'general' && (
          <Panel title={t('settings.general')} testid="settings-general" className="g-scroll">
            {err && <div className="g-error">{err}</div>}
            {!check ? <Empty>{t('settings.checkingComputer')}</Empty> : (
              <dl className="g-kv">
                <dt>{t('settings.mode')}</dt><dd>{check.recommended.mode === 'low' ? t('settings.light') : t('settings.standard')}</dd>
                <dt>{t('settings.localModel')}</dt><dd>{check.recommended.local_model}</dd>
                <dt>{t('settings.runsAtOnce')}</dt><dd>{check.recommended.max_parallel_runs}</dd>
                <dt>{t('settings.theme')}</dt><dd>{t('settings.retroTheme')}</dd>
                <dt>{t('settings.language')}</dt><dd>
                  <select className="g-input" value={language} onChange={e => chooseDictionary(e.target.value as Language)} aria-label={t('settings.language')}>
                    <option value="en">{t('settings.languageEnglish')}</option>
                    <option value="es">{t('settings.languageSpanish')}</option>
                  </select>
                </dd>
                <dt>{t('settings.detailLevel')}</dt><dd>
                  <div className="g-seg" data-testid="layout-switch">
                    {([['simple', t('settings.simple')], ['standard', t('settings.standard')], ['full', t('settings.full')]] as [Layout, string][]).map(([v, l]) =>
                      <button key={v} className={`g-seg-btn${v === layout ? ' active' : ''}`} onClick={() => setLayout(v)} data-testid={`layout-${v}`}>{l}</button>)}
                  </div>
                  <div className="g-muted">{layout === 'simple' ? t('settings.fewerSettings') : layout === 'full' ? t('settings.fullSettings') : t('settings.usualView')}</div>
                </dd>
              </dl>
            )}
          </Panel>
        )}
        {cur.id === 'system' && (
          <Panel title={t('settings.system')} aside={<Btn onClick={load} data-testid="system-recheck">{t('settings.runCheckAgain')}</Btn>} testid="settings-system" className="g-scroll">
            {err && <div className="g-error">{err}</div>}
            {!check ? <Empty>{t('settings.checking')}</Empty> : (
              <div className="g-rows">
                <Row status={check.ollama_models.length ? 'ok' : 'warn'} lead={t('settings.localModels')} detail={check.ollama_models.join(', ') || t('settings.noneInstalled')} when={check.ollama_models.length ? t('settings.ready') : t('settings.missing')} />
                {Object.entries(check.tools).map(([k, tool]) => <Row key={k} status={tool.found ? 'ok' : 'warn'} lead={k} detail={tool.version || t('settings.notFound')} when={tool.found ? t('settings.ready') : t('settings.missing')} />)}
                <Row status={check.disk_free_gb != null && check.disk_free_gb < 10 ? 'warn' : 'ok'} lead={t('settings.storage')} detail={check.disk_free_gb != null ? t('settings.gbFree', { count: check.disk_free_gb }) : t('settings.unknown')} />
                <Row status="ok" lead={t('settings.memory')} detail={check.memory_gb != null ? t('settings.gb', { count: check.memory_gb }) : t('settings.unknown')} when={check.cpu_cores ? t('settings.cores', { count: check.cpu_cores }) : ''} />
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
          <Panel title={t('settings.help')} testid="settings-help">
            <dl className="g-kv">
              <dt>{t('settings.ctrlKShort')}</dt><dd>{t('settings.ctrlK')}</dd>
              <dt>{t('settings.ctrlTab')}</dt><dd>{t('settings.nextTab')}</dd>
              <dt>{t('settings.altTabs')}</dt><dd>{t('settings.tabList')}</dd>
              <dt>{t('settings.f1')}</dt><dd>{t('settings.thisPage')}</dd>
            </dl>
          </Panel>
        )}
      </div>
      <HintBar><Hint keyLabel="↑↓">{t('hint.changeSection')}</Hint><Hint keyLabel="Enter">{t('hint.open')}</Hint></HintBar>
    </>
  )
}
