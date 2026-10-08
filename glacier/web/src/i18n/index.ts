import { en } from './en.ts'
import { es } from './es.ts'

export type Dictionary = Record<string, string>
export type Language = 'en' | 'es'
const LANGUAGE_KEY = 'glacier.language'
const dictionaries: Record<Language, Dictionary> = { en, es }
const savedLanguage = (() => {
  try { return localStorage.getItem(LANGUAGE_KEY) === 'es' ? 'es' : 'en' } catch { return 'en' }
})()
let language: Language = savedLanguage
let dictionary: Dictionary = dictionaries[language]
const missing = new Set<string>()
const subscribers = new Set<() => void>()

export function chooseDictionary(next: Language): void {
  language = next
  dictionary = dictionaries[next]
  try { localStorage.setItem(LANGUAGE_KEY, next) } catch { /* private window: applies until the app closes */ }
  subscribers.forEach(subscriber => subscriber())
}

export function getLanguage(): Language {
  return language
}

export function subscribeLanguage(subscriber: () => void): () => void {
  subscribers.add(subscriber)
  return () => subscribers.delete(subscriber)
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
