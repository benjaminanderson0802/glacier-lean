// Templates gallery (mockup panel 9): start a flow from a reviewed template.
import { useEffect, useState } from 'react'
import { api, slugify, templatesApi, type TemplateItem } from '../api.ts'
import { Btn, Empty, PageHead, Panel } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'

export function Templates() {
  const [items, setItems] = useState<TemplateItem[] | null>(null)
  const [tag, setTag] = useState(t('templates.all'))
  const [pick, setPick] = useState<TemplateItem | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { templatesApi.list().then(setItems).catch(e => setErr(String(e))) }, [])
  const tags = [t('templates.all'), ...new Set((items ?? []).flatMap(t => t.template?.tags ?? []))]
  const shown = (items ?? []).filter(item => tag === t('templates.all') || item.template?.tags?.includes(tag))

  const use = async (t: TemplateItem) => {
    if (!t.template) return
    setBusy(true)
    try {
      const taken = new Set((await api.listEnvs()).map(e => e.id))
      const base = slugify(t.name)
      let id = base
      for (let i = 2; taken.has(id); i++) id = `${base}-${i}`
      await api.saveEnv({ ...t.template, id, name: t.name })
      go(`automations/build/${id}`)
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  return (
    <>
      <PageHead title={t('templates.title')} crumb={t('templates.crumb')} sub={t('templates.subtitle')} side={<Btn onClick={() => go('automations')}>{t('templates.back')}</Btn>} />
      {err && <div className="g-error">{err}</div>}
      {tags.length > 1 && <div className="g-seg" style={{ alignSelf: 'flex-start' }}>{tags.map(t => <button key={t} className={`g-seg-btn${t === tag ? ' active' : ''}`} onClick={() => setTag(t)}>{t}</button>)}</div>}
      <div className="g-cards" data-testid="template-grid">
        {shown.map(t => (
          <button key={t.id} type="button" className={`g-card${pick?.id === t.id ? ' sel' : ''}`} onClick={() => setPick(t)} data-testid={`tpl-${t.id}`} disabled={!t.installable}>
            <span className="g-card-ico"><Icon name="automations" /></span>
            <span className="g-card-text"><span className="g-lead">{t.name}</span>
              <span className="g-detail">{t.description && t.description !== t.name ? t.description : `${t.template?.nodes.length ?? 0} steps`}</span></span>
          </button>
        ))}
      </div>
      {items && shown.length === 0 && <Empty>{t('templates.noTemplates')}</Empty>}
      {pick && (
        <Panel title={pick.name} aside={`${pick.author ?? 'Glacier'} · ${pick.license ?? ''} · ${pick.review_status}`} testid="template-detail">
          <div className="g-ask-row">
            <span className="g-detail" style={{ flex: 1 }}>{t('templates.steps', { value: (pick.template?.nodes ?? []).map(n => n.type).join(' → ') })}</span>
            <Btn primary onClick={() => use(pick)} disabled={busy || !pick.installable} data-testid="tpl-use">{t('templates.use')}</Btn>
          </div>
        </Panel>
      )}
    </>
  )
}
