# Translating Glacier

Glacier currently ships with English text in `glacier/web/src/i18n/en.ts`. The `t()` helper looks up a key in the selected dictionary, substitutes simple `{name}` values, and falls back to the English entry when a translation is missing. Unknown keys fall back to the key itself and are logged once while developing.

To add a language:

1. Copy the English dictionary into a new file such as `fr.ts` and translate each value. Keep the keys unchanged.
2. Import that dictionary where the language is selected and pass it to `chooseDictionary()` from `src/i18n/index.ts`.
3. Run `npm run check:ui` and review the screens to make sure labels fit and text reads naturally.

Keep variable names inside braces unchanged (for example, `{name}`), since the screen supplies those values. Use plain, familiar words. Do not translate product names, keyboard shortcuts, code, or values supplied by the backend unless a screen specifically owns that text.
