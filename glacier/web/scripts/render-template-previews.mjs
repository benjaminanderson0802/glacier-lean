import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
let dagre
const root = path.resolve(import.meta.dirname, '../../../')
const templatesDir = path.join(root, 'templates')
const outputDir = path.join(templatesDir, 'previews')
fs.mkdirSync(outputDir, { recursive: true })

function escape(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;')
}

for (const filename of fs.readdirSync(templatesDir).filter(name => name.endsWith('.json')).sort()) {
  const template = JSON.parse(fs.readFileSync(path.join(templatesDir, filename), 'utf8'))
  const sortKeys = value => Array.isArray(value) ? value.map(sortKeys)
    : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortKeys(value[key])])) : value
  const digest = crypto.createHash('sha256').update(JSON.stringify(sortKeys(template))).digest('hex')
  const pngPath = path.join(outputDir, `${template.id}.png`)
  const shaPath = path.join(outputDir, `${template.id}.sha256`)
  if (!process.argv.includes('--force') && fs.existsSync(pngPath) && fs.existsSync(shaPath)
      && fs.readFileSync(shaPath, 'utf8').trim() === digest) {
    console.log(`preview up to date ${template.id}`)
    continue
  }
  dagre ??= require('@dagrejs/dagre')
  const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: 'LR', nodesep: 32, ranksep: 55, marginx: 28, marginy: 28 })
  template.nodes.forEach(node => graph.setNode(node.id, { width: 190, height: 74 }))
  template.edges.forEach(edge => graph.setEdge(edge.source, edge.target, { label: edge.label || '' }))
  dagre.layout(graph)
  const { width, height } = graph.graph()
  const nodes = template.nodes.map(node => {
    const p = graph.node(node.id), x = p.x - 95, y = p.y - 37
    return `<g><rect class="node" x="${x}" y="${y}" width="190" height="74" rx="7"/><text class="name" x="${x + 12}" y="${y + 27}">${escape(node.id.slice(0, 24))}</text><text class="type" x="${x + 12}" y="${y + 51}">${escape(node.type)}</text></g>`
  }).join('')
  const edges = template.edges.map(edge => {
    const points = graph.edge(edge.source, edge.target).points
    const d = points.map((p, index) => `${index ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ')
    const mid = points[Math.floor(points.length / 2)]
    return `<path class="edge" d="${d}"/>${edge.label ? `<text class="label" x="${mid.x}" y="${mid.y - 5}">${escape(edge.label)}</text>` : ''}`
  }).join('')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#081226"/><defs><pattern id="dots" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#76a0ce"/></pattern></defs><rect width="100%" height="100%" fill="url(#dots)"/><style>.edge{fill:none;stroke:#a0c3e5;stroke-width:2;stroke-linecap:square;stroke-linejoin:miter}.node{fill:#deecf9;stroke:#14284a;stroke-width:3}.name{fill:#14284a;font:8px 'Press Start 2P',monospace}.type{fill:#22406c;font:6px 'Press Start 2P',monospace}.label{fill:#ffffff;font:6px 'Press Start 2P',monospace}</style>${edges}${nodes}</svg>`
  const { spawnSync } = await import('node:child_process')
  const venvPython = path.resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')
  const python = process.env.PYTHON ?? (fs.existsSync(venvPython) ? venvPython : process.platform === 'win32' ? 'python' : 'python3')
  const outputHeight = Math.round(1100 * height / width)
  const raster = spawnSync(python, ['-c', "import sys; import cairosvg; cairosvg.svg2png(bytestring=sys.stdin.buffer.read(), write_to=sys.argv[1], output_width=1100, output_height=int(sys.argv[2]))", pngPath, String(outputHeight)], { input: svg, encoding: 'utf8' })
  if (raster.status !== 0) throw new Error(`Could not rasterize ${template.id}: ${raster.stderr || 'CairoSVG is unavailable'}`)
  fs.writeFileSync(shaPath, `${digest}\n`)
  console.log(`rendered ${template.id}`)
}
