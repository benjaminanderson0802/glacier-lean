/** Read a theme token (e.g. '--g-line') for libraries that need a literal colour (React Flow markers, xterm). */
export function tok(name: `--g-${string}`): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
