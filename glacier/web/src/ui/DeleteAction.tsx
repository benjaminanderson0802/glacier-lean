import { useEffect, useState } from 'react'
import { Btn, HintBar } from './kit.tsx'
import { t } from '../i18n/index.ts'

type UndoAction = { title: string; run: () => Promise<unknown> }

export function DeleteAction({ label, impact, testid, onDelete, onDeleted, onError }: {
  label: string
  impact: string
  testid: string
  onDelete: () => Promise<UndoAction | undefined>
  onDeleted: (undo?: UndoAction) => void
  onError: (error: unknown) => void
}) {
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!confirm) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Enter') { event.preventDefault(); void remove() } else if (event.key === 'Escape') setConfirm(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirm])
  const remove = async () => {
    setBusy(true)
    try { const undo = await onDelete(); setConfirm(false); onDeleted(undo) }
    catch (error) { onError(error) }
    finally { setBusy(false) }
  }
  return confirm ? (
    <span className="g-delete-confirm" data-testid={`${testid}-confirm`}>
      <span className="g-detail">{impact}</span>
      <span className="g-more-arrow" />
      <HintBar><span><b>Enter</b> {t('delete.confirm')}</span><span><b>Esc</b> {t('delete.cancel')}</span></HintBar>
      <Btn danger disabled={busy} onClick={() => void remove()} data-testid={`${testid}-yes`}>{t('delete.confirm')}</Btn>
      <Btn disabled={busy} onClick={() => setConfirm(false)} data-testid={`${testid}-cancel`}>{t('delete.cancel')}</Btn>
    </span>
  ) : <Btn onClick={() => setConfirm(true)} data-testid={testid}>{label}</Btn>
}

export function DeleteUndo({ action, onDone, onError }: {
  action: UndoAction | null
  onDone: () => void
  onError: (error: unknown) => void
}) {
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!action) return
    const timer = window.setTimeout(onDone, 5000)
    return () => window.clearTimeout(timer)
  }, [action, onDone])
  if (!action) return null
  const undo = async () => {
    setBusy(true)
    try { await action.run(); onDone() }
    catch (error) { onError(error); onDone() }
    finally { setBusy(false) }
  }
  return <div className="g-saved" role="status" data-testid="delete-undo-notice">
    <span>{action.title}</span><Btn disabled={busy} onClick={() => void undo()} data-testid="delete-undo">{t('delete.undo')}</Btn>
  </div>
}

export type { UndoAction }
