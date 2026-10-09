export type RegisteredAction = {
  id: string
  label: string
  group: string
  icon?: string
  shortcut?: string
  keywords?: string[]
  run: () => void
}

export type RegisteredShortcut = {
  id: string
  label: string
  keys: string
  run: (event: KeyboardEvent) => void
  allowInInput?: boolean
}

const actions = new Map<string, RegisteredAction>()
const shortcuts = new Map<string, RegisteredShortcut>()
const listeners = new Set<() => void>()

const notify = () => listeners.forEach(listener => listener())
const normalise = (key: string) => key.toLowerCase().replace(/\s+/g, '')

export function registerAction(action: RegisteredAction): () => void {
  actions.set(action.id, action)
  notify()
  return () => { if (actions.get(action.id) === action) { actions.delete(action.id); notify() } }
}

export function registerShortcut(shortcut: RegisteredShortcut): () => void {
  const keys = normalise(shortcut.keys)
  const conflict = [...shortcuts.values()].find(item => normalise(item.keys) === keys && item.id !== shortcut.id)
  if (conflict) throw new Error(`Shortcut ${shortcut.keys} is already used by ${conflict.label}`)
  shortcuts.set(shortcut.id, shortcut)
  notify()
  return () => { if (shortcuts.get(shortcut.id) === shortcut) { shortcuts.delete(shortcut.id); notify() } }
}

export const getActions = () => [...actions.values()]
export const getShortcuts = () => [...shortcuts.values()]
export const subscribeRegistry = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }

export function matchesShortcut(event: KeyboardEvent, keys: string): boolean {
  const parts = normalise(keys).split('+')
  const key = parts.at(-1)
  const wantsMod = parts.includes('mod') || parts.includes('ctrl') || parts.includes('control')
  const wantsShift = parts.includes('shift')
  const wantsAlt = parts.includes('alt')
  const mod = /mac|iphone|ipad/i.test(navigator.platform) ? event.metaKey : event.ctrlKey
  const actual = event.key.toLowerCase()
  const shiftMatches = event.shiftKey === wantsShift || (key === '?' && event.shiftKey)
  return actual === key && mod === wantsMod && shiftMatches && event.altKey === wantsAlt
}

export function installGlobalShortcuts(onOpenPalette: () => void, onOpenNotifications: () => void): () => void {
  const builtins: RegisteredShortcut[] = [
    { id: 'palette', label: 'Open command palette', keys: 'Mod+K', run: onOpenPalette },
    { id: 'notifications', label: 'Open notifications', keys: 'Mod+Shift+N', run: onOpenNotifications },
    { id: 'shortcuts', label: 'Show keyboard shortcuts', keys: '?', run: () => window.dispatchEvent(new CustomEvent('glacier:shortcuts')) },
    { id: 'escape', label: 'Close open panels', keys: 'Escape', run: () => window.dispatchEvent(new CustomEvent('glacier:close-overlays')), allowInInput: true },
  ]
  const remove = builtins.map(registerShortcut)
  const listener = (event: KeyboardEvent) => {
    const target = event.target as HTMLElement | null
    const isInput = !!target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))
    const shortcut = getShortcuts().find(item => matchesShortcut(event, item.keys) && (!isInput || item.allowInInput || item.keys === '?'))
    if (!shortcut) return
    event.preventDefault()
    event.stopPropagation()
    shortcut.run(event)
  }
  window.addEventListener('keydown', listener, true)
  return () => { window.removeEventListener('keydown', listener, true); remove.forEach(fn => fn()) }
}

export function useRegistryVersion(): number {
  // Kept framework free so the registry is usable by any shell or test harness.
  return listeners.size
}
