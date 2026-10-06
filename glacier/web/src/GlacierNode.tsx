import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { NodeKind, NodeState } from './api.ts'

export type GNodeData = { config: Record<string, string>; state?: NodeState; label?: string; description?: string; summary?: string }
export type GNode = Node<GNodeData, NodeKind>

export function GlacierNode({ id, type, data, selected }: NodeProps<GNode>) {
  const state = data.state ?? 'none'
  const isWorker = data.label?.toLowerCase().includes('worker') ?? false
  const stateLabel: Record<NodeState | 'none', string> = { none: 'Not started', pending: 'Waiting', running: 'Working', waiting: 'Needs your choice', done: 'Finished', failed: 'Needs a fix', skipped: 'Skipped' }
  return <div className={`gnode state-${state}${selected ? ' selected' : ''}`} data-testid={`node-${id}`} data-state={state} data-type={type}>
    <Handle type="target" position={Position.Left} data-testid={`handle-in-${id}`} aria-label={`Connect to ${data.label ?? type}`} />
    <div className="gnode-head"><span className="gnode-icon" aria-hidden="true">{isWorker ? '▣' : '◇'}</span><span className="gnode-type">{isWorker ? 'Worker' : data.label ?? type}</span>{isWorker && <details className="gnode-type-info"><summary>Type</summary><span>{data.label}</span></details>}<span className="gnode-id">{id}</span></div>
    <div className="gnode-body" title={data.summary || data.description}>{data.summary || 'Select to set up this step'}</div>
    <div className={`gnode-state${state === 'none' ? ' muted' : ''}`}>{stateLabel[state]}</div>
    <Handle type="source" position={Position.Right} data-testid={`handle-out-${id}`} aria-label={`Connect from ${data.label ?? type}`} />
  </div>
}
