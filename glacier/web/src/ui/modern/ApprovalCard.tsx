import { useState } from 'react'

export function ApprovalCard({ title, detail, status = 'pending', onApprove, onReject }: { title: string; detail?: string; status?: 'pending' | 'approved' | 'rejected'; onApprove: (reason: string) => void; onReject: (reason: string) => void }) {
  const [reason, setReason] = useState('')
  return <section className="thread-approval" data-testid="approval-card">
    <div className="thread-approval-heading"><span className="thread-approval-icon">◇</span><div><strong>{title}</strong>{detail && <p>{detail}</p>}</div>
      <span className={`thread-status ${status}`}>{status === 'approved' ? 'Approved' : status === 'rejected' ? 'Rejected' : 'Needs your choice'}</span></div>
    {status === 'pending' && <>
      <label className="thread-reason"><span>Reason (optional)</span><input value={reason} onChange={e => setReason(e.target.value)} placeholder="Add a note" /></label>
      <div className="thread-approval-actions"><button className="thread-primary" type="button" onClick={() => onApprove(reason)}>Approve</button><button type="button" onClick={() => onReject(reason)}>Reject</button></div>
    </>}
  </section>
}
