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
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) go('memory')
    }
    window.addEventListener('keydown', key)
    return () => { query.removeEventListener('change', update); window.removeEventListener('keydown', key) }
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
  const pixel = useMemo(() => Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--px')) || 2, [])

  return (
    <div className="g-memmap" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) calc(84 * var(--px))', gap: 'calc(2 * var(--px))', flex: 1, minHeight: 0 }}>
      <Panel title={t('memory.map')} className="g-map-panel" testid="memory-map">
        <div ref={box} className="g-map-box" style={{ flex: 1, minHeight: 0 }}>
          {err && <div className="g-error">{err}</div>}
          {data && graph.nodes.length === 0 && <Empty>{t('memoryMap.nothing')}</Empty>}
          {graph.nodes.length > 0 && (
            <ForceGraph2D ref={fg} onEngineStop={() => fg.current?.zoomToFit(300, 30)} graphData={graph} width={size.w} height={size.h} backgroundColor="transparent"
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
              }} linkCanvasObjectMode={() => 'replace'} linkWidth={() => 0} cooldownTicks={reducedMotion ? 0 : 90} warmupTicks={reducedMotion ? 0 : Math.min(24, Math.floor(graph.nodes.length / 25))}
              linkCanvasObject={(link: { source?: string | { x?: number; y?: number }; target?: string | { x?: number; y?: number } }, ctx: CanvasRenderingContext2D) => {
                if (!link.source || !link.target || typeof link.source !== 'object' || typeof link.target !== 'object') return
                const snap = (v: number) => Math.round(v / pixel) * pixel
                const x1 = snap(link.source.x ?? 0), y1 = snap(link.source.y ?? 0), x2 = snap(link.target.x ?? 0), y2 = snap(link.target.y ?? 0)
                const dx = x2 - x1, dy = y2 - y1
                const steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / pixel))
                ctx.fillStyle = line
                for (let i = 0; i <= steps; i++) ctx.fillRect(snap(x1 + dx * i / steps), snap(y1 + dy * i / steps), pixel, pixel)
              }}
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
                const s = pixel * (glowing ? 5 : n.kind === 'author' ? 4 : 3)
                const x = Math.round((n.x ?? 0) / pixel) * pixel, y = Math.round((n.y ?? 0) / pixel) * pixel
                const faded = highlighted && !highlighted.has(String(n.id ?? ''))
                ctx.globalAlpha = faded ? 0.16 : 1
                if (glowing) { ctx.fillStyle = colours.author; ctx.fillRect(x - s / 2 - pixel, y - s / 2 - pixel, s + pixel * 2, s + pixel * 2) }
                ctx.fillStyle = colours[n.kind ?? 'note'] ?? colours.note
                ctx.fillRect(x - s / 2, y - s / 2, s, s)
                if (scale > 1.4 || n.kind === 'author' || glowing) {
                  const fontSize = Math.max(pixel * 3, Math.round((14 / scale) / pixel) * pixel)
                  ctx.font = `${fontSize}px ${font}`
                  ctx.fillStyle = text
                  ctx.fillText(n.title ?? '', x + s, y + pixel)
                }
                ctx.globalAlpha = 1
              }} />
          )}
        </div>
      </Panel>
      <Panel title={t('memoryMap.stats')} testid="memory-stats" style={{ fontSize: 'calc(5 * var(--px))' }}>
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
