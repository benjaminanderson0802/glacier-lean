// Shared building blocks. Screens are made ONLY from these + Pixel.tsx, so the theme cannot drift.
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Icon, StatusIcon, type IconName, type StatusKind } from './Pixel.tsx'

export function HintBar({ children }: { children: ReactNode }) { return <div className="g-hintbar">{children}</div> }
export function Hint({ keyLabel, children }: { keyLabel: string; children: ReactNode }) { return <span><span className="g-key">{keyLabel}</span> {children}</span> }
export function NamedTextBox({ children, className = '', testid }: { children: ReactNode; className?: string; testid?: string }) { return <section className={`g-panel g-textbox ${className}`} data-testid={testid}>{children}<span className="g-more-arrow"/></section> }
type MenuItem = { id: string; label: ReactNode; icon?: IconName; testid?: string }
export function KeyboardMenu({ items, selected, onSelect, label, orientation = 'vertical' }: { items: MenuItem[]; selected: string; onSelect: (id: string) => void; label?: string; orientation?: 'horizontal' | 'vertical' }) {
 const list=useRef<HTMLDivElement>(null); const [focused,setFocused]=useState(selected); const firstId=items[0]?.id??'';
 useEffect(()=>setFocused(items.some(item=>item.id===selected)?selected:firstId),[selected,firstId]);
 const move=(event:KeyboardEvent<HTMLDivElement>)=>{const up=orientation==='vertical'?event.key==='ArrowUp':event.key==='ArrowLeft';const down=orientation==='vertical'?event.key==='ArrowDown':event.key==='ArrowRight';if(!up&&!down)return;event.preventDefault();event.stopPropagation();if(!items.length)return;const found=items.findIndex(item=>item.id===focused);const index=found<0?(down?-1:0):found;const next=(index+(down?1:items.length-1))%items.length;setFocused(items[next].id);list.current?.querySelectorAll<HTMLButtonElement>('.g-menu-item')[next]?.focus()};
 return <div ref={list} className="g-menu-list" role="listbox" aria-label={label} tabIndex={items.length?-1:undefined} onKeyDown={move} style={orientation==='horizontal'?{flexDirection:'row',flexWrap:'wrap'}:undefined}>{items.map(item=>{const active=focused===item.id||(!focused&&selected===item.id);return <button type="button" role="option" aria-selected={selected===item.id} tabIndex={active?0:-1} key={item.id} data-testid={item.testid} className={`g-menu-item${active?' active':''}`} style={orientation==='horizontal'?{width:'auto'}:undefined} onFocus={()=>setFocused(item.id)} onClick={()=>{setFocused(item.id);onSelect(item.id)}}><span className="g-menu-cursor"/>{item.icon&&<Icon name={item.icon}/ >}{item.label}</button>})}</div>
}


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
