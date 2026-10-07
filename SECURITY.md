# Security policy

Glacier handles local files, automation steps, secrets, claims, and memory. We welcome reports that help keep users and their data safe.

## Reporting a vulnerability

Please do not open a public issue for an unpatched vulnerability. While this repository is not yet public, contact the project owner using the contact address or private contact route provided with the repository. Include steps to reproduce, the affected version or commit, impact, and any safe proof of concept. Do not include real secrets or other people's private data.

Once the repository is public and GitHub private vulnerability reporting is enabled, use the repository's **Security → Report a vulnerability** form. The owner will acknowledge the report, coordinate a fix and disclosure timeline with the reporter, and publish an advisory after users have a reasonable opportunity to update. Do not send vulnerability reports to ordinary public issue trackers.

## Supported versions

Before the first usable public release, there are no published supported release versions; reports against the current development branch are welcome. After release, security fixes target the latest stable release. Older versions are supported only when a release notice explicitly says so.

## Scope

Reports are in scope when they show a security impact in Glacier's supported code or documented setup, including:

- sandbox escape, unintended file access, or network access outside configured allowlists;
- secrets exposed in files, memory, logs, prompts, or worker output;
- unsafe claim handling, including disclosure or tampering with claim evidence;
- unauthorized access to the memory API or exposure/change of stored notes;
- unauthenticated network listeners or bypasses of approval and audit controls.

The security benchmark is the prompt-injection and lethal-trifecta suite tracked by M-SECURITY. Its target is 100% of benchmark cases passing and zero unauthenticated listeners. That target is not met yet: the local API currently has no authentication. Reports should include a reproducible case when possible.
