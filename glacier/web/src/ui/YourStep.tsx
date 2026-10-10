import { useState } from 'react'
import { api, venturesApi, type HomeItem } from '../api.ts'
import { Btn } from './kit.tsx'
import { t } from '../i18n/index.ts'

export function YourStep({ item, onDone }: { item: HomeItem; onDone: () => void }) {
  const [value, setValue] = useState('')
  const [values, setValues] = useState<Record<string, string>>({})
  const [openedLink, setOpenedLink] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const links = [...new Set([...(item.links ?? []), ...(item.detail.match(/https?:\/\/[^\s<>()]+/g) ?? [])])]
    .filter(link => { try { return ['http:', 'https:'].includes(new URL(link).protocol) } catch { return false } })
  const secretFields = item.secrets?.length ? item.secrets : item.secret_name ? [{ name: item.secret_name, label: t('ventures.pasteKey') }] : []
  const needsSecrets = secretFields.length > 0
  const allSecretsEntered = secretFields.every(field => !!values[field.name]?.trim())
  const complete = async () => {
    setBusy(true); setError('')
    try {
      if (item.ref.venture_slug && item.ref.step_id) {
        if (item.secrets?.length) await venturesApi.completeStep(item.ref.venture_slug, item.ref.step_id, undefined, values)
        else await venturesApi.completeStep(item.ref.venture_slug, item.ref.step_id, item.secret_name ? value : undefined)
      } else if (item.ref.run_id && item.ref.node_id) {
        await api.approve(item.ref.run_id, item.ref.node_id, true)
      }
      setValue('')
      setValues({})
      onDone()
    } catch (reason) { setError(String(reason)) } finally { setBusy(false) }
  }
  return <div className="venture-step" data-testid={`your-step-${item.ref.step_id ?? item.ref.run_id ?? 'setup'}`}>
    <div className="venture-step-copy"><strong>{item.title}</strong><p>{item.instructions || item.detail}</p>
      {links.map(link => <a key={link} href={link} target="_blank" rel="noopener noreferrer" onClick={() => setOpenedLink(true)}>{link}</a>)}
      {openedLink && <span aria-live="polite">{t('ventures.linkOpened')}</span>}
    </div>
    {secretFields.map(field => <label className="venture-secret-field" key={field.name}>{field.label} · {t('ventures.pasteKey')}
      <input className="g-input" type="password" autoComplete="new-password"
        value={item.secrets?.length ? values[field.name] ?? '' : value}
        onChange={event => item.secrets?.length ? setValues(current => ({ ...current, [field.name]: event.target.value })) : setValue(event.target.value)}
        aria-label={`${field.label} · ${t('ventures.pasteKey')}`} data-testid={`venture-secret-${field.name}`} />
    </label>)}
    {error && <div className="g-error" role="alert">{error}</div>}
    <Btn primary disabled={busy || (needsSecrets && (item.secrets?.length ? !allSecretsEntered : !value.trim()))} onClick={() => void complete()} data-testid={`venture-step-done-${item.ref.step_id ?? item.ref.run_id ?? 'setup'}`}>
      {busy ? t('ventures.saving') : t('ventures.done')}
    </Btn>
  </div>
}
