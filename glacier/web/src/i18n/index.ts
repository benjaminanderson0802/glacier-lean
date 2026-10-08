import { en } from './en.ts'

export type Dictionary = Record<string, string>
let dictionary: Dictionary = en
const missing = new Set<string>()

export function chooseDictionary(next: Dictionary): void {
  dictionary = next
}

export function t(key: string, vars?: Record<string, string | number>): string {
  let value = dictionary[key] ?? en[key]
  if (value === undefined) {
    if (import.meta.env.DEV && !missing.has(key)) {
      missing.add(key)
      console.warn(`Missing translation: ${key}`)
    }
    value = key
  }
  return vars ? value.replace(/\{(\w+)\}/g, (match, name: string) => String(vars[name] ?? match)) : value
}
