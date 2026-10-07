import { useCallback, useEffect, useState } from 'react'
import { ago, loadHome, subscribeEvents, type HomeItem, type HomeSummary } from '../api.ts'
import { Empty, PageHead, Panel, Progress, Row } from '../ui/kit.tsx'
import { StatusIcon } from '../ui/Pixel.tsx'
import { go } from '../route.ts'

const KIND_TITLE: Record<HomeItem['kind'], string> = { approval: 'approval waiting', claim: 'claim to review', failed_run: 'failed run' }

export function HomeScreen() {
  const [data, setData] = useState<HomeSummary | null>(null)
  const [err, setErr] = useState('')
  const refresh = useCallback(() => { loadHome().then(d => { setData(d); setErr('') }).catch(e => setErr(String(e))) }, [])
  useEffect(() => {
    refresh()
    let t: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(() => { clearTimeout(t); t = setTimeout(refresh, 400) }, () => {})
    const iv = setInterval(refresh, 15000)
    return () => { off(); clearInterval(iv); clearTimeout(t) }
  }, [refresh])

  const open = (it: HomeItem) => {
    if (it.ref.env_id) go(`automations/build/${it.ref.env_id}${it.ref.run_id ? `/${it.ref.run_id}` : ''}`)
  }

  return (
    <>
      <PageHead title="Home" sub="Today at a glance." side={
        <div className="g-statusbox" data-testid="home-status">
          <div>{(() => {
            const on = data?.local_ai.online
            const cls = on ? '' : on === false ? ' off' : ' wait'
            const label = on ? 'Local AI Online' : on === false ? 'Local AI Offline' : 'Checking local AI…'
            return <span className={`g-online${cls}`} title={data?.local_ai.model ?? undefined} data-testid="local-ai"><i className="g-dot" />{label}</span>
          })()}</div>
          <div>
            <span data-testid="count-running">{data?.counts.running ?? 0} Running</span>
            <span data-testid="count-need-you">{data?.counts.need_you ?? 0} Need You</span>
          </div>
        </div>
      } />
      {err && <div className="g-error">{err}</div>}
      <div className="g-grid-2" style={{ flex: 1 }}>
        <Panel title="Needs you" testid="needs-you">
          <div className="g-rows">
            {data?.needs_you.length === 0 && <Empty>Nothing needs you. Nice.</Empty>}
            {data?.needs_you.map((it, i) => (
              <Row key={i} status="bad" lead={`1 ${KIND_TITLE[it.kind] ?? it.title}`} detail={it.detail} when={ago(it.at)} onClick={() => open(it)} testid={`need-${i}`} />
            ))}
          </div>
        </Panel>
        <div className="g-stack">
          <Panel title="Running now" testid="running-now">
            <div className="g-rows">
              {data?.running.length === 0 && <Empty>Nothing running.</Empty>}
              {data?.running.map(r => (
                <Row key={r.run_id} status={r.status === 'queued' ? 'warn' : 'run'} lead={r.name}
                  detail={r.status === 'queued' ? undefined : `step ${r.step}/${r.steps}`}
                  when={r.status === 'queued' ? 'queued' : <Progress value={r.step} max={r.steps} />}
                  onClick={() => go(`automations/build/${r.env_id}/${r.run_id}`)} testid={`running-${r.run_id}`} />
              ))}
            </div>
          </Panel>
          <Panel title="Recent notes" testid="recent-notes" style={{ flex: 1 }}>
            <div className="g-rows">
              {data?.recent_notes.length === 0 && <Empty>No notes yet.</Empty>}
              {data?.recent_notes.map(n => (
                <Row key={n.path + n.at} icon="note" lead={n.summary} when={ago(n.at)} onClick={() => go(`memory/${encodeURIComponent(n.path)}`)} testid={`note-${n.path}`} />
              ))}
            </div>
          </Panel>
        </div>
      </div>
      {!data && !err && <div className="g-empty"><StatusIcon kind="run" /> Loading…</div>}
    </>
  )
}
