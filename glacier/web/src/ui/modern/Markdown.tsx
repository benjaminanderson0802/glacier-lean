import { Fragment, useState, type ReactNode } from 'react'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import './thread.css'

hljs.registerLanguage('javascript', javascript)
hljs.registerAliases(['js', 'jsx'], { languageName: 'javascript' })
hljs.registerLanguage('typescript', javascript)
hljs.registerAliases(['ts', 'tsx'], { languageName: 'typescript' })
hljs.registerLanguage('bash', bash)
hljs.registerAliases(['sh', 'shell'], { languageName: 'bash' })
hljs.registerLanguage('css', css)
hljs.registerLanguage('json', json)
hljs.registerLanguage('python', python)
hljs.registerAliases(['py'], { languageName: 'python' })
hljs.registerLanguage('xml', xml)
hljs.registerAliases(['html'], { languageName: 'xml' })
hljs.registerLanguage('yaml', yaml)
hljs.registerAliases(['yml'], { languageName: 'yaml' })

const safeUrl = (value: string) => {
  try { const url = new URL(value, location.href); return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : undefined }
  catch { return undefined }
}

function highlightedChildren(parent: ParentNode): ReactNode[] {
  return Array.from(parent.childNodes).map((node, index) => {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? ''
    if (node instanceof HTMLElement && node.tagName === 'SPAN') {
      const classes = node.className.split(/\s+/).filter(value => /^hljs-[\w-]+$/.test(value))
      return <span className={classes.join(' ')} key={index}>{highlightedChildren(node)}</span>
    }
    return node.textContent ?? ''
  })
}

function highlight(code: string, language: string) {
  if (!language || !hljs.getLanguage(language.toLowerCase())) return code
  const result = hljs.highlight(code, { language: language.toLowerCase(), ignoreIllegals: true })
  const parsed = new DOMParser().parseFromString(result.value, 'text/html')
  return highlightedChildren(parsed.body)
}

function inline(text: string) {
  const tokens = text.split(/(`[^`]+`|\[[^\]]+\]\([^)]+\)|<[^>]*>)/g)
  return tokens.map((token, i) => {
    if (/^`[^`]+`$/.test(token)) return <code key={i}>{token.slice(1, -1)}</code>
    const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      const href = safeUrl(link[2])
      return href ? <a key={i} href={href} target="_blank" rel="noopener noreferrer">{link[1]}</a> : <span key={i}>{link[1]}</span>
    }
    // Raw HTML is displayed as text, never interpreted by the browser.
    if (/^<[^>]*>$/.test(token)) return <span key={i}>{token}</span>
    return token
  })
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [wrap, setWrap] = useState(false)
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1400) }
    catch { setCopied(false) }
  }
  return <div className={`thread-code${wrap ? ' is-wrapped' : ''}`} data-testid="code-block" data-wrap={wrap}>
    <div className="thread-code-head"><span>{language || 'plain text'}</span><div>
      <button type="button" onClick={() => setWrap(x => !x)} aria-label={wrap ? 'Unwrap code' : 'Wrap code'}>{wrap ? 'Unwrap' : 'Wrap code'}</button>
      <button type="button" onClick={copy} aria-label="Copy code">{copied ? 'Copied' : 'Copy'}</button>
    </div></div>
    <pre><code>{highlight(code, language)}</code></pre>
  </div>
}

function table(lines: string[]) {
  const rows = lines.filter(line => !/^\s*\|?\s*:?-{3,}/.test(line)).map(line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim()))
  return <div className="thread-table-scroll"><table><thead><tr>{(rows[0] ?? []).map((cell, i) => <th key={i}>{inline(cell)}</th>)}</tr></thead><tbody>{rows.slice(1).map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{inline(cell)}</td>)}</tr>)}</tbody></table></div>
}

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r/g, '').split('\n')
  const nodes: ReactNode[] = []
  for (let i = 0; i < lines.length;) {
    const line = lines[i]
    const fence = line.match(/^\s*```([\w+-]*)\s*$/)
    if (fence) {
      const code: string[] = []; i++
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) code.push(lines[i++])
      i++
      nodes.push(<CodeBlock key={`c${i}`} language={fence[1]} code={code.join('\n')} />); continue
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      const tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] as const
      const H = tags[heading[1].length - 1]
      nodes.push(<H key={i}>{inline(heading[2])}</H>); i++; continue
    }
    if (/^\s*>/.test(line)) {
      const quote: string[] = []
      while (i < lines.length && /^\s*>/.test(lines[i])) quote.push(lines[i++].replace(/^\s*>\s?/, ''))
      nodes.push(<blockquote key={`q${i}`}>{quote.map((row, j) => <p key={j}>{inline(row)}</p>)}</blockquote>); continue
    }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const rows = [line, lines[i + 1]]; i += 2
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++])
      nodes.push(<Fragment key={`t${i}`}>{table(rows)}</Fragment>); continue
    }
    if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = /^\s*\d/.test(line), items: string[] = []
      const re = ordered ? /^\s*\d+\.\s+/ : /^\s*[-*+]\s+/
      while (i < lines.length && re.test(lines[i])) items.push(lines[i++].replace(re, ''))
      const L = ordered ? 'ol' : 'ul'; nodes.push(<L key={`l${i}`}>{items.map((item, j) => <li key={j}>{inline(item)}</li>)}</L>); continue
    }
    if (line.trim()) {
      const paragraph = [line.trim()]; i++
      while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\s*>|\s*[-*+]\s+|\s*\d+\.\s+|\s*```|\s*\|)/.test(lines[i])) paragraph.push(lines[i++].trim())
      nodes.push(<p key={`p${i}`}>{inline(paragraph.join(' '))}</p>); continue
    }
    i++
  }
  return <div className="thread-markdown">{nodes}</div>
}
