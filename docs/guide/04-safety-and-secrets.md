# To protect data and secrets

Glacier is designed to keep its data on your computer by default. A step may still contact a website or an AI service if its instructions or settings ask it to. Review where a step sends information before you run it.

## Protect private information

Do not put passwords or access keys directly in a prompt, note, or command text. AI step instructions can't use `{secret:...}`; a secret can only be used in a command step, and any saved secret that appears in output is hidden as `[secret name]` before it is saved or passed on.

Glacier uses the Codex subscription CLI by default. OpenAI-compatible and Anthropic API engines are only used when you choose one in **Settings** > **Models**, save your own key, and set a monthly spending cap. Glacier shows spending and stops at the cap. Local models are another option; see [Choose an AI engine](06-engines.md).

For ordinary automation steps, Glacier uses free AI routes. If none is available, the step fails and Glacier files one policy claim per day. This is separate from the API engines you choose for Build and assistant conversations.

## Limit what a step can do

AI steps can be read-only or allowed to write in their work folder. Read-only means the AI can look at files but cannot change them. A sandbox limits where a step can work.

The person who installs Glacier can set `GLACIER_CODEX_SANDBOX` as the default for Codex steps that do not choose a mode. A step's own setting, including read-only, takes precedence.

An approval step pauses and asks before its connected action continues. Read the request carefully. Approve only actions you understand, such as moving selected files into a review folder. Reject anything unclear. A check can verify a result, but it does not replace your judgment about whether an action is safe.
