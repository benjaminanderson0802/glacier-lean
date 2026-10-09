# Ask engines and context

Ask uses the same Glacier context for every engine. A repo-derived, cached pack reads the mission in `NORTHSTAR.yaml`, the owner's `notes/about-me.md` (or saved preferences note), the screen guide, API routes in the contracts, and the UI source layout. It explains Home, Build, Automations, Memory and Settings, along with the UI rules for tokens, Nunito, test labels, theme lint and related tests. Source changes invalidate the cache. Small local models such as `granite3.3:2b` receive a compact pack; subscription CLIs, configured APIs and larger models receive the full pack. Ask also includes live tool and flow status, relevant Memory search results, and (when enabled) recent chats. Memory and chat text are redacted before it is sent. The overall context remains capped at 5,000 characters for small models and 16,000 for other engines.

Chat requests may include `screen` and `focus`, for example `{"screen":"build","focus":"interview"}`, `{"screen":"automations/build","focus":"<flow id>"}`, or `{"screen":"memory","focus":"<note>"}`. Ask tells the assistant where the owner is and what they are viewing, and asks it to open with the relevant help.

The saved engine defaults to the signed-in Codex CLI. Ask checks Codex, Claude Code, Gemini CLI, Ollama with installed models, and configured APIs. If the selected engine is unavailable, Ask explains why and uses the next ready engine. Change a ready engine beside the Ask title; Settings → Models contains the full configuration.

## API settings

OpenAI-compatible APIs need a base address, model name, secret name saved in Settings → Secrets, monthly spending cap, and the provider's input/output prices per million tokens. Anthropic uses `https://api.anthropic.com/v1/messages` with the same settings except for the base address. Secret values stay in the operating-system keychain. The secret name is the only credential reference stored in settings. Glacier shows the current month's estimated spend. Before each request it reserves a conservative prompt estimate and the full 1,200-token answer allowance; it sends no request if the cap is missing or the reservation would reach or cross it. Successful calls replace the reservation with an estimate based on returned token counts. Failed calls retain the reservation because the provider may have charged for them.

API hosts must be listed in `GLACIER_ALLOWED_HOSTS`. Calls use Glacier's pinned, proxy-free egress and reject redirects. The API destination is visible in the base address field. Local Ollama choices come only from installed models.

## Previous chats

“Remember previous chats” is on by default. When enabled, recent saved exchanges are included as context and redacted. Turn it off to keep existing saved chats out of future requests. **Forget chats** removes saved Ask conversations from the local Memory vault and turns chat context off. The setting can be turned on again later.

## Verification

Backend tests use temporary vaults and stand-ins for the provider calls. They check shared context delivery to Codex, Claude, Gemini, OpenAI-compatible, Anthropic and Ollama adapters, compact/full pack generation and cache invalidation, screen/focus prompts, context size limits, redaction, disabled history, fallback reporting, and settings persistence without contacting a model service. The card's live check also sends a screen-aware greeting through the local model and Codex CLI on the configured machine.
