# Safety and secrets

Glacier is designed to keep its data on your computer by default. A step may still contact a website or an AI service if its instructions or settings ask it to. Review where a step sends information before you run it.

## Protect private information

Do not put passwords or access keys directly in a prompt, note, or command text. AI step instructions can't use `{secret:...}`; a secret can only be used in a command step, and any saved secret that appears in output is hidden as `[secret name]` before it is saved or passed on.

Glacier uses free AI routes. When no free route is available and a paid route is configured, the step fails. Glacier files one policy claim per day in this case. It does not switch to a paid route without approval.

## Limit what a step can do

AI steps can be read-only or allowed to write in their work folder. Read-only means the AI can look at files but cannot change them. A sandbox limits where a step can work.

The person who installs Glacier can set `GLACIER_CODEX_SANDBOX`. When set, it overrides the setting on every Codex step, including steps marked read-only. This setting controls what those steps can change, so ask the installer if you are unsure.

An approval step pauses and asks before its connected action continues. Read the request carefully. Approve only actions you understand, such as moving selected files into a review folder. Reject anything unclear. A check can verify a result, but it does not replace your judgment about whether an action is safe.
