// Memory map (mockup panel 10): pixel-square graph of everything Glacier knows. Colours from tokens only.
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d'
import { forceManyBody, forceLink, type SimulationNodeDatum, type SimulationLinkDatum } from 'd3-force'
import { memoryMore, subscribeEvents, type GraphEdge, type GraphNode, type MemoryEvent } from '../api.ts'
import { Empty, Panel } from '../ui/kit.tsx'
import { tok } from '../ui/tok.ts'
import { go } from '../route.ts'
import { t } from '../i18n/index.ts'

const KIND_TOKEN: Record<string, `--g-${string}`> = { note: '--g-accent', run: '--g-ok', flow: '--g-warn', claim: '--g-bad', author: '--g-head' }
const KIND_LABEL: Record<string, string> = { note: t('memory.viewsNotes'), run: t('run.pastRuns'), flow: t('build.flows'), claim: t('claims.title'), author: t('memoryMap.writers') }

export function MemoryMap() {
  const [data, setData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null)
  const [err, setErr] = useState('')
  const box = useRef<HTMLDivElement>(null)
  const fg = useRef<ForceGraphMethods | undefined>(undefined)
  const clickTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const [size, setSize] = useState({ w: 600, h: 400 })
  const [reducedMotion, setReducedMotion] = useState(() => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [hovered, setHovered] = useState<string | null>(null)
  // Notes light up for a few seconds when anything (you, an automation, an AI worker) writes them.
  const [lit, setLit] = useState<Record<string, number>>({})
  useEffect(() => {
    const load = () => memoryMore.graph(1500).then(setData).catch(e => setErr(String(e)))
    load()
    let t: ReturnType<typeof setTimeout> | undefined
    const off = subscribeEvents(ev => {
      const m = ev as unknown as MemoryEvent
      if (m.type !== 'memory') return
      setLit(x => ({ ...x, [m.path.replace(/\.md$/, '')]: Date.now() }))
      clearTimeout(t); t = setTimeout(load, 300)
    }, () => {})
    const fade = setInterval(() => setLit(x => Object.fromEntries(Object.entries(x).filter(([, at]) => Date.now() - at < 4000))), 500)
    return () => { off(); clearTimeout(t); clearInterval(fade) }
  }, [])
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReducedMotion(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    const el = box.current; if (!el) return
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el); return () => ro.disconnect()
  }, [])
  const graph = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const ids = new Set(data.nodes.map(n => n.id))
    const authors = [...new Set(data.edges.filter(e => e.kind === 'wrote' && !ids.has(e.target)).map(e => e.target))].filter(Boolean)
    const nodes = [...data.nodes.map(n => ({ ...n })), ...authors.map(a => ({ id: a, title: a, kind: 'author', author: '' }))]
    const all = new Set(nodes.map(n => n.id))
    return { nodes, links: data.edges.filter(e => all.has(e.source) && all.has(e.target)).map(e => ({ ...e })) }
  }, [data])
  useEffect(() => {
    if (!fg.current || graph.nodes.length === 0) return
    fg.current.d3Force('center', null)
    fg.current.d3Force('link', forceLink().id((n: SimulationNodeDatum & { id?: string | number }) => String(n.id)).distance((edge: SimulationLinkDatum<SimulationNodeDatum> & { kind?: string }) => edge.kind === 'link' ? 52 : 72).strength((edge: SimulationLinkDatum<SimulationNodeDatum> & { kind?: string }) => edge.kind === 'link' ? 0.55 : 0.08))
    fg.current.d3Force('charge', forceManyBody().strength(-32).theta(0.9).distanceMax(240))
  }, [graph])
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const n of graph.nodes) c[n.kind] = (c[n.kind] ?? 0) + 1
    return c
  }, [graph])
  const colours = useMemo(() => Object.fromEntries(Object.entries(KIND_TOKEN).map(([k, t]) => [k, tok(t)])), [])
  const font = useMemo(() => tok('--g-font-body'), [])
  const line = useMemo(() => tok('--g-line-dim'), [])
  const text = useMemo(() => tok('--g-text'), [])
  const highlighted = useMemo(() => {
    if (!hovered) return null
    const ids = new Set([hovered])
    for (const edge of graph.links) {
      const source = typeof edge.source === 'object' ? (edge.source as { id: string }).id : edge.source
      const target = typeof edge.target === 'object' ? (edge.target as { id: string }).id : edge.target
      if (source === hovered) ids.add(target)
      if (target === hovered) ids.add(source)
    }
    return ids
  }, [graph.links, hovered])

  return (
    <div className="g-memmap">
      <Panel className="g-map-panel" testid="memory-map">
        <div ref={box} className="g-map-box">
          {err && <div className="g-error">{err}</div>}
          {data && graph.nodes.length === 0 && <Empty>{t('memoryMap.nothing')}</Empty>}
          {graph.nodes.length > 0 && (
            <ForceGraph2D ref={fg} onEngineStop={() => fg.current?.zoomToFit(300, 30)} graphData={graph} width={size.w} height={size.h} backgroundColor="transparent" // theme-lint-ignore (library keyword, not a colour)
              d3AlphaDecay={0.035} d3VelocityDecay={0.38} d3AlphaMin={0.001}
              nodeRelSize={4} linkColor={(l: { source: string | { id: string }; target: string | { id: string } }) => {
                if (!highlighted) return line
                const source = typeof l.source === 'object' ? l.source.id : l.source
                const target = typeof l.target === 'object' ? l.target.id : l.target
                return source === hovered || target === hovered ? tok('--g-accent') : 'transparent'
              }} linkWidth={(l: { source: string | { id: string }; target: string | { id: string } }) => {
                if (!highlighted) return 1
                const source = typeof l.source === 'object' ? l.source.id : l.source
                const target = typeof l.target === 'object' ? l.target.id : l.target
                return source === hovered || target === hovered ? 2 : 0
              }} cooldownTicks={reducedMotion ? 0 : 90} warmupTicks={reducedMotion ? 0 : Math.min(24, Math.floor(graph.nodes.length / 25))}
              enableNodeDrag autoPauseRedraw nodePointerAreaPaint={(n: { x?: number; y?: number }, color: string, ctx: CanvasRenderingContext2D) => { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(n.x ?? 0, n.y ?? 0, 9, 0, Math.PI * 2); ctx.fill() }}
              onNodeClick={(n: { id?: string | number; kind?: string }, event: MouseEvent) => {
                if (event.detail > 1) {
                  clearTimeout(clickTimer.current)
                  const pinned = graph.nodes.find(node => node.id === n.id) as (typeof graph.nodes[number] & { fx?: number; fy?: number }) | undefined
                  if (pinned) { pinned.fx = undefined; pinned.fy = undefined; if (!reducedMotion) fg.current?.d3ReheatSimulation() }
                  return
                }
                clearTimeout(clickTimer.current)
                clickTimer.current = setTimeout(() => { if (n.kind === 'note') go(`memory/${encodeURIComponent(`${n.id}.md`)}`) }, 260)
              }}
              onNodeHover={(n: { id?: string | number } | null) => setHovered(n?.id == null ? null : String(n.id))}
              onNodeDragEnd={(n: { fx?: number; fy?: number; x?: number; y?: number }) => { n.fx = n.x; n.fy = n.y }}
              nodeCanvasObject={(n: { id?: string | number; x?: number; y?: number; kind?: string; title?: string }, ctx: CanvasRenderingContext2D, scale: number) => {
                const glowing = lit[String(n.id ?? '')]
                const s = glowing ? 9 : n.kind === 'author' ? 7 : 5
                const faded = highlighted && !highlighted.has(String(n.id ?? ''))
                ctx.globalAlpha = faded ? 0.16 : 1
                if (glowing) { ctx.fillStyle = colours.author; ctx.fillRect(Math.round((n.x ?? 0) - s / 2 - 2), Math.round((n.y ?? 0) - s / 2 - 2), s + 4, s + 4) }
                ctx.fillStyle = colours[n.kind ?? 'note'] ?? colours.note
                ctx.fillRect(Math.round((n.x ?? 0) - s / 2), Math.round((n.y ?? 0) - s / 2), s, s)
                if (scale > 1.4 || n.kind === 'author' || glowing) {
                  ctx.font = `${Math.max(8, 14 / scale)}px ${font}`
                  ctx.fillStyle = text
                  ctx.fillText(n.title ?? '', (n.x ?? 0) + s, (n.y ?? 0) + 3)
                }
                ctx.globalAlpha = 1
              }} />
          )}
        </div>
      </Panel>
      <Panel title={t('memoryMap.stats')} testid="memory-stats">
        <dl className="g-kv g-kv-tight">
          {Object.entries(KIND_LABEL).filter(([k]) => counts[k]).map(([k, label]) => (
            <Fragment key={k}><dt><i className="g-swatch" style={{ background: `var(${KIND_TOKEN[k]})` }} />{label}</dt><dd>{counts[k]}</dd></Fragment>
          ))}
          <dt>{t('memoryMap.links')}</dt><dd>{graph.links.filter(l => l.kind === 'link').length}</dd>
        </dl>
        <div className="g-detail" style={{ marginTop: 10 }}>{t('memoryMap.hint')}</div>
        {Object.keys(lit).length > 0 && <div className="g-saved" data-testid="memory-live">{t('memoryMap.writing', { value: Object.keys(lit).slice(0, 3).join(', ') })}</div>}
      </Panel>
    </div>
  )
}
