# Polar Precision

## Acceptance test, recorded before implementation

At 1440×900 and 1920×1080, capture Build interview with inspector, Home, Automations with an active run, Command palette over Build, and Settings → Engines. The prototype must support palette filtering (Ctrl/⌘K), sidebar collapse, a streaming answer, expanding a tool card, toast undo, Build tabs, view changes, and the requested motion and reduced-motion behavior. Save ten screenshots and a 20–40 second Playwright WebM.

## Concept (five lines)

Glacier reads as a precise local workbench: durable, inspectable, and ready to hand off work.
A compact left rail holds the five areas; the top strip keeps active project threads close.
Build pairs the live interview with requirements, proposed workers, and acceptance checks in a sliding inspector.
Home prioritizes human decisions, automation health, and recent memory; Automations exposes its live graph and run evidence.
Faceted navy planes, thin glacial edges, and restrained ice light carry the interface without softening its alignment.

## Palette and type scale

- Base `#070d15`; raised surfaces `#0b1420` / `#101c2a`; facet surface `#142438`.
- Ice accent `#89c4e0`, highlight `#c8e7f4`; borders `#24394c`, bright edge `#42637c`; body `#e6f0f8`, secondary `#9cb0c2`.
- One accent hue: ice blue. Status uses the same hue with labels and symbols.
- Geist Sans for interface text: 9–10px metadata, 11–13px controls/body, 14px project titles, 22px page titles. Geist Mono for ids, shortcuts, statuses, and measurements.

## Glass recipe

Use opaque, layered navy for work surfaces: two angular linear gradients, a faint inset white edge, and a 1px blue-grey border. Bundle Geist Sans and Geist Mono locally as WOFF2 under `fonts/`; both render through local `@font-face`. The page backdrop uses the deep-glacier SVG facets and crack filters with a 22% crack layer, one cyan bloom and a dark vignette. Sidebar, top strip, inspector, palette and overlays use a 9px blur, rim highlight and restrained angular sheen. Body copy stays on solid or near-solid surfaces.

## Motion recipe

Enter/exit uses `cubic-bezier(.23,1,.32,1)` with opacity and small transforms; the palette scales from `.96` in 220ms. Close immediately or faster than open. Sidebar collapse and canvas drag use short Web Animations API springs. Keyboard navigation suppresses motion; reduced-motion disables transitions and animation.

## Five deliberate choices against generic UI

1. Facet planes live in the work surfaces and page backdrop, rather than a large gradient wash.
2. EARS requirements, route, model, run id, and independent checks appear as real product information.
3. Thread tabs and compact mono labels make this a workbench rather than a large chat landing page.
4. The flow canvas uses explicit schedule → read → check → note nodes with a live run inspector.
5. Controls share a 4–7px radius system, hairline borders, and compact spacing; no emoji, purple, or teal template gradients.

## Self-critique and corrections

### Round 1 — first screenshots, 1440×900

**Harsh critique.** The first pass showed the main work views clipped after their eyebrow. The hidden thread strip removed its grid track, leaving Home, Automations, and Settings only 42px tall. That makes the interface look broken, not precise. Build itself reads well, but the tiny metadata is too dim, completion states introduce green and amber into a monochrome brief, the automation wire ends float over nodes instead of meeting their ports, and the second sidebar group repeats “Workspace.”

**Corrections applied.** Keep the thread-strip row reserved while hidden; raise secondary text contrast; consolidate status color to the ice-blue accent; connect each automation path to exact node edges; rename the lower navigation group “System.” The small-click press state now gives controls a clear response, and keyboard-driven view/tab selection skips entrance motion.

### Round 2 — after the first corrections, 1440×900

**Harsh critique.** All five states now paint and the hierarchy reads, but the running automation panel and completed nodes still pull green against the ice-blue system. Home has a large empty lower band that makes the dense workbench direction feel unfinished. The command palette keeps its last command below the visible list, so the command-first promise looks clipped.

**Corrections applied.** Shifted live-run surfaces and completion marks fully into icy blue; added a three-row recent activity table based on real run events to fill Home; expanded the palette list so every command is visible at the target desktop size.

### Round 3 — after the second corrections, 1440×900

**Harsh critique.** The content and color now hold together, but event ids in Home are still undersized, the failure alert node floats without an edge in the canvas, and the palette scrim makes its context too indistinct. Those details weaken the precision and glass direction even though the core screens work.

**Corrections applied.** Raised event row and id type by one pixel; connected the alert to the check node with a labeled failure branch; reduced palette blur from 5px to 4px and its scrim opacity from 48% to 38%. Reduced-motion now disables animation and transitions outright.

### Round 4 — layout and product-scope audit

**Harsh critique.** The polished Build view still reads as three permanent columns, which is too close to the rejected canvas mockup. Its inspector should feel like a tool that comes forward only when needed. The collapsed rail also hid its own expand control, and the Memory navigation landed on a placeholder instead of the promised notes and graph.

**Corrections applied.** Made the inspector a dismissible right-side overlay that slides over the chat; kept the expand control visible in the collapsed rail; built a local Markdown note reader and force-directed linked map; added answer choices to the interview. Sidebar and node springs, and streamed text, now respect reduced-motion settings. The Home event table and command palette remain inside their desktop bounds.



### Integrator critique — follow-up round 1

**Harsh critique.** The earlier artifact missed the world brief: its CSS wash made the tool read like a generic dashboard, remote Inter/DM Mono could fall back on the target machine, visible shortcut hints used the macOS command glyph, and scattered unicode marks made some controls look like placeholders. Automations still left too much dead canvas and had an oversized empty inspector. The surfaces also lacked the requested glass rim and fracture-plane sheen.

**Corrections applied.** Added the source mockup's filtered SVG crystal backdrop (fractal facets, specular crack layer, one upper-right cyan bloom and dark vignette) behind opaque high-contrast work surfaces. Bundled local Geist Sans and Geist Mono WOFF2 faces and confirmed both loaded in Chromium. Replaced icon glyphs with a consistent stroked inline SVG set; keyboard hints now use Ctrl. Automation canvas now fills the available area, centers the flow at readable scale, and includes a compact live-run panel and overview. Added glass treatment to navigation and overlays, plus subtle angular sheens on active tabs and panel headers. Re-shot all five requested states at 1440×900 and 1920×1080 and recorded the interaction walkthrough.
