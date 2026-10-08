import { useCallback, useEffect, useState } from 'react'
import { teamsApi, type BuildTeam, type TeamPlan } from '../api.ts'
import { Bar, Btn, HintBar, PageHead, Panel, TextBox } from '../ui/kit.tsx'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'
import './build-teams.css'

type Stage = 'interview' | 'spec' | 'plan'
type ChatLine = { who: 'you' | 'ai'; text: string }
const initialSpec: TeamPlan['spec'] = { requirements: [], out_of_scope: [], acceptance: [] }

export function BuildTeamsScreen({ teamId }: { teamId?: string }) {
  const [stage, setStage] = useState<Stage>('interview')
  const [engine, setEngine] = useState('codex')
  const [conv] = useState(() => crypto.randomUUID())
  const [lines, setLines] = useState<ChatLine[]>([])
  const [message, setMessage] = useState('')
  const [vision, setVision] = useState<Record<string, unknown>>({ goal: '', done: [] })
  const [spec, setSpec] = useState<TeamPlan['spec']>(initialSpec)
  const [visionPath, setVisionPath] = useState('')
  const [plan, setPlan] = useState<TeamPlan | null>(null)
  const [team, setTeam] = useState<BuildTeam | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const refreshTeam = useCallback(() => { if (teamId) teamsApi.get(teamId).then(setTeam).catch(e => setError(String(e))) }, [teamId])
  useEffect(() => { refreshTeam() }, [refreshTeam])
  useEffect(() => { if (!teamId) return; const id = setInterval(refreshTeam, 2200); return () => clearInterval(id) }, [teamId, refreshTeam])

  const send = async () => {
    if (!message.trim() || busy) return
    const text = message.trim(); setMessage(''); setLines(v => [...v, { who: 'you', text }]); setBusy(true); setError('')
    try {
      const result = await teamsApi.interview(text, conv, engine)
      setLines(v => [...v, { who: 'ai', text: result.reply }])
      setVision(v => ({ ...v, goal: String(v.goal || text), done: Array.isArray(v.done) && v.done.length ? v.done : [text] }))
      setSpec(v => ({ ...v, requirements: [...v.requirements, `The project shall ${text.replace(/[.!?]+$/, '')}.`] }))
    } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  const approveSpec = async () => {
    setBusy(true); setError('')
    try {
      const goal = String(vision.goal || lines.find(x => x.who === 'you')?.text || 'New project')
      const done = Array.isArray(vision.done) ? vision.done as string[] : []
      const v = await teamsApi.vision({ ...vision, goal, done: done.length ? done : spec.acceptance.map(String) })
      setVisionPath(v.path)
      const accepted = await teamsApi.spec({ ...spec, acceptance: spec.acceptance.length ? spec.acceptance : done })
      setSpec(accepted.spec)
      setStage('spec')
    } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  const approvePlan = async () => {
    if (!plan) return
    setBusy(true); setError('')
    try { const saved = await teamsApi.create(plan, visionPath); await teamsApi.start(saved.team_id); go(`automations/team/${saved.team_id}`) }
    catch (e) { setError(String(e)) } finally { setBusy(false) }
  }


  if (teamId) return <TeamDetail team={team} error={error} onRefresh={refreshTeam} />

  return <>
    <PageHead title={t('team.buildTitle')} sub={t('team.buildSub')} side={<label className="bt-engine">{t('team.engine')} <select data-testid="build-engine" value={engine} onChange={e => setEngine(e.target.value)}><option value="codex">{t('team.subscription')}</option><option value="api">{t('team.api')}</option><option value="local">{t('team.local')}</option></select></label>} />
    <div className="bt-workspace">
      <Panel title={t('team.steps')} className="bt-step-panel"><button className={`g-menu-item${stage === 'interview' ? ' active' : ''}`} onClick={() => setStage('interview')}>▸ {t('team.interview')}</button><button className={`g-menu-item${stage === 'spec' ? ' active' : ''}`} onClick={() => setStage('spec')} disabled={!visionPath}>▸ {t('team.specApproval')}</button><button className={`g-menu-item${stage === 'plan' ? ' active' : ''}`} onClick={() => setStage('plan')} disabled={!plan}>▸ {t('team.planTeam')}</button><button className="g-menu-item" data-testid="build-open-chat" onClick={() => go('ask/chat')}>▸ {t('team.chat')}</button></Panel>
      {stage === 'interview' ? <Panel title={t('team.interview')} className="bt-chat" testid="build-interview">
        <div className="bt-chat-log" data-testid="build-chat-log">{lines.length === 0 && <TextBox>{t('team.startPrompt')}</TextBox>}{lines.map((line, i) => <div className={`bt-line ${line.who}`} key={i}><b>{line.who === 'you' ? t('team.you') : t('team.interviewer')}</b><p>{line.text}</p></div>)}</div>
        <form className="bt-composer" onSubmit={e => { e.preventDefault(); void send() }}><textarea data-testid="build-message" value={message} onChange={e => setMessage(e.target.value)} placeholder={t('team.messagePlaceholder')} /><Btn primary type="submit" disabled={busy || !message.trim()} data-testid="build-send">{busy ? '…' : t('team.send')}</Btn></form>
        <HintBar><span><kbd>Enter</kbd> {t('team.send')}</span><span>{t('team.currentEngine')} {engine === 'codex' ? t('team.subscription') : engine === 'local' ? t('team.local') : t('team.api')}</span></HintBar>
      </Panel> : stage === 'spec' ? <Panel title={t('team.specApproval')} className="bt-stage" testid="build-spec">
        <label>{t('team.goal')}<textarea value={String(vision.goal ?? '')} onChange={e => setVision(v => ({ ...v, goal: e.target.value }))} /></label>
        <label>{t('team.requirements')}<textarea value={spec.requirements.map(String).join('\n')} onChange={e => setSpec(s => ({ ...s, requirements: e.target.value.split('\n').filter(Boolean) }))} /></label>
        <label>{t('team.acceptance')}<textarea value={spec.acceptance.map(String).join('\n')} onChange={e => setSpec(s => ({ ...s, acceptance: e.target.value.split('\n').filter(Boolean) }))} /></label>
        <label>{t('team.outOfScope')}<textarea value={spec.out_of_scope.join('\n')} onChange={e => setSpec(s => ({ ...s, out_of_scope: e.target.value.split('\n').filter(Boolean) }))} /></label>
        <div className="bt-actions"><Btn onClick={() => setStage('interview')}>{t('team.keepTalking')}</Btn><Btn primary disabled={busy} onClick={async () => { try { await teamsApi.spec(spec); const proposed = await teamsApi.plan(visionPath, engine); setSpec(proposed.plan.spec); setPlan(proposed.plan); setStage('plan') } catch (e) { setError(String(e)) } }}>{t('team.approveSpec')}</Btn></div>
      </Panel> : <Panel title={t('team.proposedPlan')} className="bt-stage" testid="build-plan">
        {plan && <><h3>{t('team.roles')}</h3><div className="bt-roles">{plan.team.roles.map(role => <article key={role.id}><b>{role.id}</b><p>{role.charter}</p></article>)}</div><p>{t('team.runMode')} <b>{plan.team.worker_mode === 'sequential' ? t('team.sequential') : t('team.parallel')}</b></p><p>{t('team.cycles', { count: plan.features.length })}</p>
          <h3>{t('team.lockedFeatures')}</h3><ul>{plan.features.map(f => <li key={f.id}>{f.title}</li>)}</ul><h3>{t('team.harness')}</h3><pre>{JSON.stringify(plan.harness, null, 2)}</pre><h3>{t('team.tasks')}</h3><ul>{plan.tasks.map(task => <li key={task.id}>{task.title} · {task.role}</li>)}</ul></>}
        <div className="bt-actions"><Btn onClick={() => { setMessage(t('team.feedbackPrefix')); setStage('interview') }}>{t('team.editFeedback')}</Btn><Btn primary disabled={busy || !plan} onClick={() => void approvePlan()}>{t('team.startTeam')}</Btn></div>
      </Panel>}
      <Panel title={t('team.understood')} className="bt-understood" testid="build-understood"><p>{t('team.readiness')}</p><Bar value={(message ? 0 : 10) + (lines.some(x => /who|for|audience/i.test(x.text)) ? 20 : 0) + (spec.requirements.length ? 25 : 0) + (spec.acceptance.length || Array.isArray(vision.done) && (vision.done as string[]).length ? 25 : 0) + (spec.out_of_scope.length ? 20 : 0)} max={100} /><h3>{t('team.requirements')}</h3><ol>{spec.requirements.map((line, i) => <li key={i}><input aria-label={t('team.editLine')} value={String(line)} onChange={e => setSpec(s => ({ ...s, requirements: s.requirements.map((x, j) => i === j ? e.target.value : x) }))} /></li>)}</ol><h3>{t('team.doneList')}</h3><ol>{(Array.isArray(vision.done) ? vision.done as string[] : []).map((line, i) => <li key={i}><input aria-label={t('team.editLine')} value={line} onChange={e => setVision(v => ({ ...v, done: (v.done as string[]).map((x, j) => i === j ? e.target.value : x) }))} /></li>)}</ol><button className="g-link" onClick={() => void approveSpec()}>{t('team.reviewSpec')}</button></Panel>
    </div>
    {error && <div className="g-error" data-testid="team-error">{error}</div>}
  </>
}

function TeamDetail({ team, error, onRefresh }: { team: BuildTeam | null; error: string; onRefresh: () => void }) {
  if (!team) return <><PageHead title={t('team.title')} /><Panel>{error || t('team.loading')}</Panel></>
  const plan = team.plan
  const roles = plan.team.roles
  const tasks = Object.entries(team.tasks ?? {})
  const waiting = tasks.find(([, value]) => value.status === 'awaiting_approval')
  const passing = Object.values(team.features ?? {}).filter(f => f.status === 'passing').length
  const total = plan.features.length
  return <><PageHead title={String(plan.vision.goal ?? t('team.title'))} sub={`${t('team.status')}: ${team.status}`} side={<div className="bt-actions"><Btn onClick={onRefresh}>{t('build.refresh')}</Btn></div>} />
    <div className="bt-team-grid"><Panel title={t('team.roles')}><div className="bt-roles">{roles.map(role => { const owned = tasks.filter(([id]) => plan.tasks.find(x => x.id === id)?.role === role.id); return <article key={role.id}><b><i className={`bt-light ${owned.some(([, v]) => v.status === 'running') ? 'run' : owned.every(([, v]) => v.status === 'done') ? 'ok' : ''}`} />{role.id}</b><p>{role.charter}</p><small>{owned.map(([id, v]) => `${id}: ${String(v.status)}`).join(' · ')}</small></article> })}</div></Panel>
      <Panel title={t('team.features')} testid="team-features"><p>{t('team.passing', { passing, total })}</p><Bar value={passing} max={total} />{plan.features.map(feature => <div className="bt-feature" key={feature.id}><b>{feature.title}</b><span>{team.features?.[feature.id]?.status === 'passing' ? t('team.pass') : t('team.pending')}</span>{team.features?.[feature.id]?.evaluator_evidence && <small>{team.features[feature.id].evaluator_evidence}</small>}</div>)}</Panel>
      <Panel title={t('team.currentContract')} className="bt-contract" testid="team-current-contract"><p>{waiting ? plan.tasks.find(x => x.id === waiting[0])?.title : t('team.noApproval')}</p><pre>{JSON.stringify(waiting ? plan.tasks.find(x => x.id === waiting[0])?.acceptance : plan.harness.checks ?? [], null, 2)}</pre>{waiting && <div className="bt-actions"><Btn primary onClick={() => void teamsApi.approveTask(team.team_id, waiting[0], true).then(onRefresh)}>{t('team.approve')}</Btn><Btn danger onClick={() => void teamsApi.approveTask(team.team_id, waiting[0], false).then(onRefresh)}>{t('team.reject')}</Btn></div>}</Panel>
      <Panel title={t('team.progress')}><TextBox className="bt-log"><pre>{String(team.progress_log ?? t('team.noProgress')).slice(-1800)}</pre></TextBox><p>{t('team.stalls')}: {tasks.reduce((n, [, v]) => n + Number(v.attempts ?? 0), 0)} {t('team.attempts')} · {tasks.reduce((n, [, v]) => n + Number(v.replans ?? 0), 0)} {t('team.replans')}</p></Panel></div>
    {error && <div className="g-error">{error}</div>}
  </>
}
