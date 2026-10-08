// Shared building blocks. Screens are made ONLY from these + Pixel.tsx, so the theme cannot drift.
import type { ReactNode } from 'react'
import { Icon, StatusIcon, type IconName, type StatusKind } from './Pixel.tsx'

export function Window({ title, children, className = '', testid }: { title?: ReactNode; children: ReactNode; className?: string; testid?: string }) {
  return <section className={`g-panel ${className}`} data-testid={testid}>{title && <h2 className="g-panel-title">{title}</h2>}{children}</section>
}

export function MenuList({ items, selected, onSelect }: { items: { id: string; label: ReactNode; icon?: IconName }[]; selected: string; onSelect: (id: string) => void }) {
  return <div className="g-menu-list">{items.map(item => <button type="button" key={item.id} className={`g-menu-item${selected === item.id ? ' active' : ''}`} onClick={() => onSelect(item.id)}><span className="g-menu-cursor"/>{item.icon && <Icon name={item.icon}/ >}{item.label}</button>)}</div>
}

export function HintBar({ children }: { children: ReactNode }) { return <div className="g-hintbar">{children}</div> }
export function Button({ children, primary, ...props }: { children: ReactNode; primary?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) { return <button {...props} className={`g-btn${primary ? ' primary' : ''} ${props.className ?? ''}`}>{children}</button> }
export function Bar({ value, max, tone = 'ok' }: { value: number; max: number; tone?: 'ok' | 'warn' | 'bad' }) { const pct = max ? Math.max(0, Math.min(100, value / max * 100)) : 0; return <div className="g-progress" role="progressbar" aria-valuenow={value} aria-valuemax={max}><i className={tone} style={{ width: `${pct}%` }}/></div> }
export function TextBox({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`g-panel g-textbox ${className}`}>{children}<span className="g-more-arrow"/></section> }
export function TableRows({ children }: { children: ReactNode }) { return <div className="g-rows g-table-rows">{children}</div> }
export function TitleBar({ title, onMinimize, onClose }: { title: ReactNode; onMinimize?: () => void; onClose?: () => void }) { return <div className="g-titlebar"><strong>{title}</strong><span/><Button onClick={onMinimize}>_</Button><Button onClick={onClose}>×</Button></div> }

export function PageHead({ title, sub, crumb, side }: { title: string; sub?: string; crumb?: string; side?: ReactNode }) {
  return (
    <header className="g-pagehead">
      <div className="g-titles">
        {crumb && <span className="g-crumb">{crumb}</span>}
        <h1 className="g-title" data-testid="page-title">{title}</h1>
        {sub && <span className="g-sub">{sub}</span>}
      </div>
      {side && <div className="g-headside">{side}</div>}
    </header>
  )
}

export function Panel({ title, aside, children, testid, className, style }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; testid?: string; className?: string; style?: React.CSSProperties }) {
  return (
    <section className={`g-panel ${className ?? ''}`} data-testid={testid} style={style}>
      {title && <h2 className="g-panel-title">{title}{aside && <span className="g-aside">{aside}</span>}</h2>}
      {children}
    </section>
  )
}

type RowProps = { status?: StatusKind; icon?: IconName; lead: ReactNode; detail?: ReactNode; when?: ReactNode; onClick?: () => void; testid?: string; className?: string }
export function Row({ status, icon, lead, detail, when, onClick, testid, className }: RowProps) {
  const inner = (
    <>
      <span className="g-ico">{status ? <StatusIcon kind={status} /> : icon ? <Icon name={icon} /> : null}</span>
      <span className="g-mid"><span className="g-lead">{lead}</span>{detail != null && <span className="g-detail">{detail}</span>}</span>
      <span className="g-when">{when}</span>
    </>
  )
  return onClick
    ? <button type="button" className={`g-row ${className ?? ''}`} data-testid={testid} onClick={onClick}>{inner}</button>
    : <div className={`g-row ${className ?? ''}`} data-testid={testid}>{inner}</div>
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.max(4, (value / max) * 100)) : 0
  return <div className="g-progress" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}><i style={{ width: `${pct}%` }} /></div>
}

export function Btn({ children, primary, danger, icon, ...rest }: { children: ReactNode; primary?: boolean; danger?: boolean; icon?: IconName } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" {...rest} className={`g-btn${primary ? ' primary' : ''}${danger ? ' danger' : ''} ${rest.className ?? ''}`}>{icon && <Icon name={icon} />}{children}</button>
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="g-empty">{children}</div>
}
