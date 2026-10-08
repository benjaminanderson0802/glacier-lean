# Translating Glacier

Glacier keeps its screen text in `glacier/web/src/i18n/`. `en.ts` is the source dictionary and `es.ts` is the Spanish dictionary. The `t()` helper looks up the selected dictionary and replaces values such as `{name}` with data from the screen. English is the default; the language selected in Settings > General is saved in this browser and takes effect immediately.

To add a language:

1. Copy `src/i18n/en.ts` to a new file named with a two-letter language code, such as `fr.ts`.
2. Translate every value while keeping every key exactly the same. Keep each `{placeholder}` unchanged, including its spelling.
3. Export the dictionary using the same shape as `en.ts`, then import it in `src/i18n/index.ts` and add it to the language dictionary map. Add a language option to Settings > General using its existing settings row and select styles.
4. Run `node scripts/check-i18n.mjs` from `glacier/web/`. It checks that every dictionary has exactly the English keys and matching placeholders.
5. Run `npm run check:ui` and review the screens for natural wording and labels that fit.

Use plain, familiar words. Keep product names, keyboard shortcuts, code, and values supplied by the backend unchanged unless a screen specifically owns that text. Do not change theme styles or layout to accommodate a translation; shorten the wording instead.

## Engine supplied text

Some text comes from the engine rather than from the screen, including starter reasons, template names, and run explanations. These values remain in English for now; screen-owned labels and controls use the selected language.
