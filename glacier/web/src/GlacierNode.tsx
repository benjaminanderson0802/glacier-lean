import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { NodeKind, NodeState } from './api.ts'

export type GNodeData = { config: Record<string, string>; state?: NodeState }
export type GNode = Node<GNodeData, NodeKind>

const ICON: Record<string, string> = { schedule: '⏱', command: '›_', codex: '◆', check: '?', approval: '✓', note: '✎', loop: '↻', flow: '⧉' }

function summary(kind: NodeKind, c: Record<string, string>): string {
  switch (kind) {
    case 'schedule': return c.cron || 'no cron'
    case 'command': return c.cmd || 'no command'
    case 'codex': return c.prompt || 'no prompt'
    case 'check': return c.expr || 'no expression'
    case 'approval': return c.prompt || 'no prompt'
    case 'note': return c.path || 'no path'
    case 'loop': return `${c.times || '1'} times`
    case 'flow': return c.env ? `runs ${c.env}` : 'no environment'
    default: return Object.values(c).find(Boolean) || ''
  }
}

export function GlacierNode({ id, type, data, selected }: NodeProps<GNode>) {
  const state = data.state ?? 'none'
  return (
    <div
      className={`gnode gnode-${type} state-${state}${selected ? ' selected' : ''}`}
      data-testid={`node-${id}`}
      data-state={state}
      data-type={type}
    >
      <Handle type="target" position={Position.Left} data-testid={`handle-in-${id}`} />
      <div className="gnode-head">
        <span className="gnode-icon">{ICON[type] ?? '•'}</span>
        <span className="gnode-type">{type === 'codex' ? 'codex worker' : type === 'flow' ? 'sub-flow' : type}</span>
        <span className="gnode-id">{id}</span>
      </div>
      <div className="gnode-body" title={summary(type, data.config)}>{summary(type, data.config)}</div>
      {state !== 'none' && <div className="gnode-state">{state}</div>}
      <Handle type="source" position={Position.Right} data-testid={`handle-out-${id}`} />
    </div>
  )
}

export const nodeTypes = {
  schedule: GlacierNode, command: GlacierNode, codex: GlacierNode, check: GlacierNode, approval: GlacierNode, note: GlacierNode, loop: GlacierNode, flow: GlacierNode,
}
