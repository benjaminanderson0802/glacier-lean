import { useState } from 'react'
import { api, venturesApi, type HomeItem } from '../api.ts'
import { Btn } from './kit.tsx'
import { t } from '../i18n/index.ts'

export function YourStep({ item, onDone }: { item: HomeItem; onDone: () => void }) {
  const [value, setValue] = useState('')
  const [openedLink, setOpenedLink] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const links = [...new Set([...(item.links ?? []), ...(item.detail.match(/https?:\/\/[^\s<>()]+/g) ?? [])])]
    .filter(link => { try { return ['http:', 'https:'].includes(new URL(link).protocol) } catch { return false } })
  const complete = async () => {
    setBusy(true); setError('')
    try {
      if (item.ref.venture_slug && item.ref.step_id) {
        await venturesApi.completeStep(item.ref.venture_slug, item.ref.step_id, item.secret_name ? value : undefined)
      } else if (item.ref.run_id && item.ref.node_id) {
        await api.approve(item.ref.run_id, item.ref.node_id, true)
      }
      setValue('')
      onDone()
    } catch (reason) { setError(String(reason)) } finally { setBusy(false) }
  }
  return <div className="venture-step" data-testid={`your-step-${item.ref.step_id ?? item.ref.run_id ?? 'setup'}`}>
    <div className="venture-step-copy"><strong>{item.title}</strong><p>{item.instructions || item.detail}</p>
      {links.map(link => <a key={link} href={link} target="_blank" rel="noopener noreferrer" onClick={() => setOpenedLink(true)}>{link}</a>)}
      {openedLink && <span aria-live="polite">{t('ventures.linkOpened')}</span>}
    </div>
    {item.secret_name && <label className="venture-secret-field">{t('ventures.pasteKey')}
      <input className="g-input" type="password" autoComplete="new-password" value={value} onChange={event => setValue(event.target.value)} aria-label={t('ventures.pasteKey')} data-testid={`venture-secret-${item.secret_name}`} />
    </label>}
    {error && <div className="g-error" role="alert">{error}</div>}
    <Btn primary disabled={busy || (!!item.secret_name && !value.trim())} onClick={() => void complete()} data-testid={`venture-step-done-${item.ref.step_id ?? item.ref.run_id ?? 'setup'}`}>
      {busy ? t('ventures.saving') : t('ventures.done')}
    </Btn>
  </div>
}
