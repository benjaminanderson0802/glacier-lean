# Deep Glacier — Glacier's design system (replaces the pixel theme)

Owner direction (2026-10-08): modern harness UI (like the current Claude, ChatGPT/Codex and Cursor desktop apps), liquid-glass feel, dark icy-blue shiny monochrome, keep the Glacier feel, macOS-quality motion, full modern features, completely functional. Reference render: `docs/design/deep-glacier-mockup.png` (source `deep-glacier-mockup.html` - the tokens and component styles there are the starting point). Owner mood images: dark ice cave, frosted crystal, frost palette #d0e4f8 #b4c9e8 #87adda #4675a3 #31527e, icy palette #f0f8fb #89c4e0 #468aae #194f70 #0b2133 #03070b.

## 1. Tokens (CSS custom properties in src/theme/tokens.css; nothing else may hard-code colours)
- Surfaces: --void #03070b (app background), --deep #0b2133, glass fill `linear-gradient(180deg, rgba(14,34,52,.62), rgba(6,16,26,.70))`, raised glass `rgba(20,44,66,.72)`, sunken `rgba(3,7,11,.35)`.
- Text: --ink #e8f3fa (primary), --ink2 #a9c3d6 (secondary), --ink3 #6f8ea6 (tertiary, never for body text). Body text must reach WCAG AA 4.5:1 on the worst-case glass; check it.
- Accent (the light in the ice; use sparingly - focus, active item, primary action, progress, live states): --ice #89c4e0, --glow #5fb3e0, --tropic #468aae. Success #7fd6c0, warning #e8c27a, danger #f08a8a (muted, icy-tinted; still distinguishable).
- Lines: --line rgba(150,200,235,.12), --line2 rgba(150,200,235,.22).
- Radius: 6 (chips/kbd), 10 (inputs, list items), 12-14 (cards), 16-18 (panels, composer), 999 (pills).
- Spacing: 4-pt grid (4 8 12 16 20 24 32). Type: Geist (bundled, OFL) 12.5/13/14/15/18/24 px; Geist Mono for code, ids, keys. Weights 400/500/600 only.
- Elevation = glass + rim light: `inset 0 1px 0 rgba(200,235,255,.22)` top rim, `inset 0 -1px 0 rgba(0,0,0,.4)`, outer `0 24px 60px -24px rgba(0,0,0,.9)`; popovers add a faint glow `0 0 0 1px var(--line2)`.

## 2. Glass rules (from current web research on liquid glass)
- backdrop-filter: blur(16-22px) saturate(160-180%) on chrome only: sidebar, panels, composer, popovers, dialogs, command palette, toasts. NOT on dense data (tables, logs, code) - those sit on a sunken solid layer for contrast.
- At most 3-4 glass layers visible at once (performance). Never animate blur radius; animate opacity/transform.
- Glacier's window is Chromium (WebView2), so an optional SVG displacement "refraction" lens may be used on the composer and command palette only; must be off under prefers-reduced-transparency and have a frosted fallback.
- Background: generated ice texture (SVG feTurbulence + diffuse/specular lighting, see mockup) under a dark vignette and one soft cyan glow; static (no animation), rendered once; no stock images. Settings > Appearance: texture intensity (off/low/normal) and "Reduce transparency" (solid surfaces).

## 3. Motion (macOS-quality; rules from Emil Kowalski's design-engineering guidance + Apple HIG)
- Animate only transform and opacity (and filter blur <= 2px for crossfades). Never `transition: all`.
- Easing: enter/exit `cubic-bezier(.23,1,.32,1)`; on-screen movement `cubic-bezier(.77,0,.175,1)`; drawers/sheets `cubic-bezier(.32,.72,0,1)`; hover/colour `ease`. Never ease-in.
- Durations: press 100-160ms (scale .97 on :active); tooltips 125-200ms; dropdowns/popovers 150-250ms (scale from .96 + fade, transform-origin at the trigger); dialogs/sheets 200-300ms (origin centre); toasts slide+fade 300-400ms; exits faster than enters.
- Springs (interruptible things: sidebar collapse, panel resize snap, drag on the canvas, palette open): Apple-style spring duration .45-.5s bounce .15-.2 (Web Animations API or a tiny spring util; no heavy animation library unless justified).
- Lists: new items stagger 30-50ms; streaming text fades in per chunk (opacity only); layout shifts use FLIP so nothing jumps.
- Never animate keyboard-driven actions (command palette open via Ctrl+K appears instantly or <=120ms; arrow navigation instant).
- Hover effects only under `@media (hover:hover) and (pointer:fine)`. `prefers-reduced-motion`: keep fades, remove movement.
- View changes: View Transitions API for route changes (shared element for the active nav pill), crossfade 180ms.

## 4. Modern harness features (all must actually work)
App shell: custom title bar (drag region, Windows min/max/close working, breadcrumb, global search field), collapsible glass sidebar (New build/chat Ctrl+N, nav with counts, Pinned, Recent threads with live status dots, rename/pin/delete via context menu, search), main area, optional right side panel (resizable, collapsible, remembers width), status of engines at sidebar foot.
Chat/Build thread: streaming markdown (headings, lists, tables, code blocks with language label + copy + wrap toggle, inline code, links), tool-call cards (collapsible, status, duration, output), inline choice buttons from the interviewer, approvals inline (Approve / Reject with reason), message actions (copy, edit & resend own message, regenerate, branch), stop generation, scroll-to-bottom pill, jump to latest, timestamps on hover, empty-state suggestions.
Composer: auto-growing textarea, Enter send / Shift+Enter newline, attachments (button + drag-and-drop + paste images/files, chips with remove), / slash commands menu (filterable), @ mentions (flows, notes, chats), engine picker (Subscription CLI / API / Local with status), mode picker (Chat / Build interview), context-usage meter, keyboard hints, disabled/busy states.
Global: command palette Ctrl+K (navigate, actions, recent items, fuzzy search), keyboard shortcut sheet (?), toasts with undo, tooltips, context menus, confirm dialogs, settings as a modal/sheet with left section list, notifications for finished runs/approvals, skeleton loaders (no layout jump), error states with retry, offline/engine-down banner.
Screens to cover: Home (overview + what needs you + running + recent), Build (interview chat, Spec, Team, Runs tabs as in the mockup), Automations (list + flow canvas editor + templates + run view; canvas nodes as glass cards, smooth pan/zoom, snapping kept), Memory (list, note editor with preview, memory map with physics in the ice palette), Settings (all sections), Claims, What's new.

## 5. Quality gate (strict - nothing "basic" ships)
A change is accepted only when ALL hold:
1. Screenshot of each touched screen at 1280x800 and 1920x1080 in evidence/ui/<card>-*.png, compared side by side with the mockup; the integrator rejects anything that looks like a generic template, has default browser controls, misaligned spacing, mixed radii, untinted greys, or text below AA contrast.
2. Theme lint (rewritten for this system) passes: colours only via tokens, no `transition: all`, no ease-in, no durations > 500ms (except spinners/progress), no font families other than Geist/Geist Mono, no remaining pixel-theme classes or sprites, no inline styles for colour/spacing.
3. Motion check: an e2e asserts key transitions exist with the right properties (computed transition-property excludes `all`, durations within the ranges) and that prefers-reduced-motion removes transforms.
4. Every visible control does something real (no dead buttons): an e2e clicks every button/menu item on each screen against the mock server and asserts a visible effect or navigation; console has no errors.
5. Full board `npm run check:ui` PASS and backend suite PASS; Spanish parity kept.
