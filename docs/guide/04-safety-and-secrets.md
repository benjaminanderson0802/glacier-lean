# Safety and secrets

Glacier is designed to keep its data on your computer by default. A step may still contact a website or an AI service if its instructions or settings ask it to. Review where a step sends information before you run it.

## Protect private information

Do not put passwords or access keys in a prompt, note, or command text. Glacier has a Secrets area for named values. A command step can use a saved secret by name, and Glacier hides recognized secret values in saved run output. AI steps cannot receive these saved secrets.

Use only free routes by default. A paid AI route needs the owner's approval first. If no free route is available, Glacier records a claim for review instead of using a paid route automatically.

## Limit what a step can do

AI steps can be set to read-only or allowed to write in their work folder. A sandbox is a boundary that limits where a step can work. The exact boundary depends on the step and how Glacier is installed; do not treat a setting as permission to expose private files.

An approval step pauses and asks before its connected action continues. Read the request carefully. Approve only actions you understand, such as moving selected files into a review folder. Reject anything unclear. A check can verify a result, but it does not replace your judgment about whether an action is safe.
