// Templates gallery (mockup panel 9): start a flow from a reviewed template.
import { useEffect, useState } from 'react'
import { api, slugify, templatesApi, type TemplateItem } from '../api.ts'
import { Btn, Empty, PageHead, Panel } from '../ui/kit.tsx'
import { Icon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import { DeleteAction, DeleteUndo, type UndoAction } from '../ui/DeleteAction.tsx'

export function Templates() {
  const [items, setItems] = useState<TemplateItem[] | null>(null)
  const [tag, setTag] = useState(t('templates.all'))
  const [pick, setPick] = useState<TemplateItem | null>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [deleteUndo, setDeleteUndo] = useState<UndoAction | null>(null)
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
      <DeleteUndo action={deleteUndo} onDone={() => setDeleteUndo(null)} onError={e => setErr(String(e))} />
      {tags.length > 1 && <div className="g-seg" style={{ alignSelf: 'flex-start' }}>{tags.map(value => <button key={value} className={`g-seg-btn${value === tag ? ' active' : ''}`} onClick={() => setTag(value)}>{value}</button>)}</div>}
      <div className="g-cards" data-testid="template-grid">
        {shown.map(item => (
          <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button type="button" className={`g-card${pick?.id === item.id ? ' sel' : ''}`} style={{ flex: 1 }} onClick={() => setPick(item)} data-testid={`tpl-${item.id}`} disabled={!item.installable}>
              <span className="g-card-ico"><img className="template-thumb" src={`/templates/previews/${item.id}.png`} alt="" loading="lazy" /><Icon name="automations" /></span>
              <span className="g-card-text"><span className="g-lead">{item.name}</span>
                <span className="g-detail">{item.description && item.description !== item.name ? item.description : t('templates.stepCount', { count: item.template?.nodes.length ?? 0 })}</span>
                <span className="template-needs">{t('templates.needs')}: {requires(item.template)}</span>
                <span className="template-needs">{t('templates.produces')}: {produces(item.template)}</span></span>
            </button>
            {item.review_status === 'approved' && <DeleteAction label={t('templates.deleteImported')} impact={t('delete.templateImpact')} testid={`template-delete-${item.id}`}
              onDelete={async () => { const result = await templatesApi.delete(item.id); return { title: t('delete.removed'), run: async () => { await templatesApi.undoDelete(result.undo_id); setItems(await templatesApi.list()) } } }}
              onDeleted={action => { setDeleteUndo(action ?? null); setItems(current => current?.filter(row => row.id !== item.id) ?? null) }}
              onError={e => setErr(String(e))} />}
          </div>
        ))}
      </div>
      {items && shown.length === 0 && <Empty>{t('templates.noTemplates')}</Empty>}
      {pick && (
        <Panel title={pick.name} aside={`${pick.author ?? 'Glacier'} · ${pick.license ?? ''} · ${pick.review_status}`} testid="template-detail">
          <img className="template-full-preview" src={`/templates/previews/${pick.id}.png`} alt={`${pick.name} ${t('templates.preview').toLowerCase()}`} />
          <div className="g-ask-row">
            <span className="g-detail" style={{ flex: 1 }}>{t('templates.needs')}: {requires(pick.template)}<br />{t('templates.produces')}: {produces(pick.template)}<br />{t('templates.steps', { value: (pick.template?.nodes ?? []).map(n => n.type).join(' → ') })}</span>
            <Btn primary onClick={() => use(pick)} disabled={busy || !pick.installable} data-testid="tpl-use">{t('templates.use')}</Btn>
          </div>
        </Panel>
      )}
    </>
  )
}

function requires(template: TemplateItem['template']): string {
  if (!template) return ''
  const values = new Set<string>()
  for (const node of template.nodes) for (const [key, value] of Object.entries(node.config)) {
    if (!value) continue
    if (/path|folder|file|directory/i.test(key)) values.add(String(value))
    else if (node.type === 'http_request' && key === 'url') values.add(String(value))
    else if (node.type === 'schedule' && key === 'cron') values.add(String(value))
  }
  return [...values].slice(0, 3).join(', ') || t('templates.none')
}

function produces(template: TemplateItem['template']): string {
  if (!template) return ''
  const values = new Set(template.nodes.filter(node => ['note', 'command', 'codex'].includes(node.type)).map(node => node.config.path || node.config.name).filter(Boolean))
  return [...values].slice(0, 3).join(', ') || template.description || template.name
}
