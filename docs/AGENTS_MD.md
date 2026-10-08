# Project instructions for coding agents

AGENTS.md is a plain text file that gives a coding agent directions for a project. Glacier looks for the closest `AGENTS.md` when it starts a coding step. A file in a nearer folder takes priority over one in a parent folder. In a Git project, Glacier searches up to the project root. Outside Git, it checks only the selected folder.

Glacier reads no more than 64 KB. It will not read an `AGENTS.md` link that points outside the project tree. If there is no file, the step continues normally.

Codex and OpenCode read project instructions themselves, so Glacier does not copy those instructions into their task text. The Run view output shows the file name, its first heading, and its path so a person can see which directions applied.

The Local AI step has an optional **Project folder** setting. When it is filled in, Glacier adds the matching file to the request in a clearly marked “Project instructions” section. The selected model receives that text as part of its request.

## Flow exports

A flow export can include an `agents_md` text section. It describes the automation goal, its steps, and its checks in ordinary words. This section is optional and is only guidance for another agent tool. Import reads and validates the flow itself and ignores this extra section, including when it is absent in an older export.
