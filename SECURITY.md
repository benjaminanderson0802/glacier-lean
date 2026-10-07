# Security policy

Glacier runs on your computer and can handle files, secrets, automated actions, and connections to other agents. Please report security problems privately so they can be fixed before details become public.

## Supported versions

Until the first release, only the `main` branch is supported. After a release, support for released versions will be stated with that release.

## Report a vulnerability

Use GitHub's private vulnerability reporting for this repository: open the **Security tab** > **Report a vulnerability**. Do not post an unpatched vulnerability in a public issue.

Include the affected commit or version, the steps needed to reproduce the problem, its likely impact, and a small proof of concept if it is safe to share. Remove real secrets and other people's private data. The project will acknowledge a report within 7 days and provide a fix or a plan within 30 days. We will coordinate public disclosure with the reporter after users have had a reasonable chance to update.

## Scope

Reports are in scope when they demonstrate a security issue in supported Glacier code, including:

- engine install-token disclosure or a way to bypass the token check;
- bypasses of the local Host or Origin guard;
- sandbox escapes or unintended file or network access;
- secrets exposed in files, memory, logs, prompts, or worker output;
- bypasses of the **Read a web page** step's allowed-site and egress rules;
- unauthorized A2A access, including starting or reading flows that were not explicitly shared.

Out of scope are general bugs without a security impact, vulnerabilities in unsupported third-party software without a Glacier-specific impact, and attacks requiring access the reporter already has by design. Please still report a concrete security impact in Glacier's supported code.

## Safe harbour

We will not pursue legal action against people who make a good-faith effort to follow this policy, avoid privacy violations and service disruption, and report findings privately through the stated route.
