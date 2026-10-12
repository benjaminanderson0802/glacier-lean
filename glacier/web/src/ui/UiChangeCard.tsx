import { useMemo, useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'
import type { ChatProposal } from '../api.ts'
import { t } from '../i18n/index.ts'
import { Btn } from './kit.tsx'
import './ui-change-card.css'

export type UiChangeResult = {
  applied?: boolean
  branch?: string
  changed_files?: string[]
  passed?: boolean
  error?: string
  check_results?: Record<string, { passed?: boolean; output?: string }>
}

type Props = {
  proposal: ChatProposal
  state: 'open' | 'approved' | 'rejected' | 'applying' | 'discarded'
  result?: UiChangeResult
  error?: string
  onApprove: () => void
  onDiscard: () => void
  onRefine: (feedback: string) => void
}

function pathsFromDiff(diff: string): string[] {
  return [...new Set([...diff.matchAll(/^\+\+\+ b\/(.+)$/gm)].map(match => match[1]))]
}

function diffSides(diff: string): { original: string; modified: string } {
  const original: string[] = []
  const modified: string[] = []
  for (const line of diff.split('\n')) {
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('\\ No newline')) continue
    if (line.startsWith('@@')) continue
    if (line.startsWith('-')) original.push(line.slice(1))
    else if (line.startsWith('+')) modified.push(line.slice(1))
    else if (line.startsWith(' ')) { original.push(line.slice(1)); modified.push(line.slice(1)) }
  }
  return { original: original.join('\n'), modified: modified.join('\n') }
}

export function UiChangeCard({ proposal, state, result, error, onApprove, onDiscard, onRefine }: Props) {
  const [refining, setRefining] = useState(false)
  const [feedback, setFeedback] = useState('')
  const diff = String(proposal.diff ?? '')
  const sides = useMemo(() => diffSides(diff), [diff])
  const files = result?.changed_files?.length ? result.changed_files : pathsFromDiff(diff)
  const checkResults = result?.check_results ?? {}
  const status = state === 'open' ? t('uiChange.proposed')
    : state === 'applying' ? t('uiChange.applying')
      : state === 'approved' ? t('uiChange.applied')
        : state === 'discarded' || state === 'rejected' ? t('uiChange.discarded') : state

  return (
    <section className="g-ui-change-card" data-testid="ui-change-card" aria-label={t('uiChange.title')}>
      <header className="g-ui-change-head">
        <h3>{t('uiChange.title')}</h3>
        <span className="g-chip">{status}</span>
      </header>
      <p className="g-ui-change-explanation" data-testid="ui-change-explanation">{proposal.explanation || t('uiChange.noExplanation')}</p>
      <div className="g-ui-change-section">
        <h4>{t('uiChange.files')}</h4>
        <ul data-testid="ui-change-files">{files.map(file => <li key={file}>{file}</li>)}</ul>
      </div>
      <div className="g-ui-change-section">
        <h4>{t('uiChange.diff')}</h4>
        <div className="g-ui-change-diff" data-testid="ui-change-diff">
          <DiffEditor
            height="280px"
            language="plaintext"
            theme="vs-dark"
            original={sides.original}
            modified={sides.modified}
            options={{ readOnly: true, minimap: { enabled: false }, scrollBeyondLastLine: false, wordWrap: 'on', automaticLayout: true }}
          />
        </div>
      </div>
      {typeof proposal.related_spec === 'string' && <p className="g-ui-change-spec">{t('uiChange.relatedSpec', { path: proposal.related_spec })}</p>}
      {state === 'open' && <div className="g-actions g-ui-change-actions">
        <Btn primary onClick={onApprove} data-testid="ui-change-approve">{t('uiChange.approve')}</Btn>
        <Btn onClick={() => setRefining(value => !value)} data-testid="ui-change-refine">{t('uiChange.refine')}</Btn>
        <Btn onClick={onDiscard} data-testid="ui-change-discard">{t('uiChange.discard')}</Btn>
      </div>}
      {refining && state === 'open' && <form className="g-ui-change-feedback" onSubmit={event => { event.preventDefault(); const value = feedback.trim(); if (value) onRefine(value) }}>
        <label htmlFor={`ui-change-feedback-${proposal.id}`}>{t('uiChange.feedbackLabel')}</label>
        <textarea id={`ui-change-feedback-${proposal.id}`} value={feedback} onChange={event => setFeedback(event.target.value)} data-testid="ui-change-feedback" />
        <Btn primary type="submit" disabled={!feedback.trim()} data-testid="ui-change-send-feedback">{t('uiChange.sendFeedback')}</Btn>
      </form>}
      {error && <p className="g-error" data-testid="ui-change-error">{error}</p>}
      {result && <div className="g-ui-change-result" data-testid="ui-change-result">
        {result.branch && <p data-testid="ui-change-branch">{t('uiChange.branch', { branch: result.branch })}</p>}
        {result.passed !== undefined && <p data-testid="ui-change-checks">{result.passed ? t('uiChange.checksPassed') : t('uiChange.checksFailed')}</p>}
        {Object.entries(checkResults).map(([name, check]) => <p key={name} className={check.passed ? 'g-ui-check-pass' : 'g-ui-check-fail'}>{name}: {check.passed ? t('uiChange.pass') : t('uiChange.fail')}</p>)}
      </div>}
    </section>
  )
}
