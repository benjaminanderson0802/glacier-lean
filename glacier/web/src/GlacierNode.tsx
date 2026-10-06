import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { NodeKind, NodeState } from './api.ts'

export type GNodeData = { config: Record<string, string>; state?: NodeState; label?: string; description?: string; summary?: string }
export type GNode = Node<GNodeData, NodeKind>

export function GlacierNode({ id, type, data, selected }: NodeProps<GNode>) {
  const state = data.state ?? 'none'
  return <div className={`gnode state-${state}${selected ? ' selected' : ''}`} data-testid={`node-${id}`} data-state={state} data-type={type}>
    <Handle type="target" position={Position.Left} data-testid={`handle-in-${id}`} aria-label={`Connect to ${data.label ?? type}`} />
    <div className="gnode-head"><span className="gnode-icon" aria-hidden="true">◇</span><span className="gnode-type">{data.label ?? type}</span><span className="gnode-id">{id}</span></div>
    <div className="gnode-body" title={data.summary || data.description}>{data.summary || 'Select to set up this step'}</div>
    <div className={`gnode-state${state === 'none' ? ' muted' : ''}`}>{state === 'none' ? 'Select to edit' : state}</div>
    <Handle type="source" position={Position.Right} data-testid={`handle-out-${id}`} aria-label={`Connect from ${data.label ?? type}`} />
  </div>
}
