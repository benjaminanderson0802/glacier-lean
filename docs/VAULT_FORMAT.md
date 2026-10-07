# Opening the Glacier vault in a Markdown editor

The vault is a normal folder of Markdown notes and attachments. It lives at
`GLACIER_HOME/vault` (the app's local data folder). You can open that folder as
a vault in Obsidian or as a folder in Zettlr. Notes and files remain readable
without Glacier; the `.git` folder stores history and can be used with ordinary
Git tools.

## Notes and metadata

Each note is a UTF-8 `.md` file. Glacier writes a YAML front matter block at the
start of service-managed notes:

```yaml
---
title: "Project notes"
author: owner
run_id: ""
created: "2026-10-07T12:00:00+00:00"
updated: "2026-10-07T12:00:00+00:00"
tags: [planning, research]
---
# Project notes
Your note text goes here.
```

The lines between the opening and closing `---` markers are YAML. JSON-style
quoted values are valid YAML too, so notes written by Glacier's claim system
also open in standard YAML front matter readers. Notes may use ordinary
Markdown headings, lists, links, code blocks, and `#tags` in their body.

## Links and attachments

Use Obsidian-style wiki links to connect notes. A full folder path is clearest:

```markdown
[[projects/roadmap]]
[[projects/roadmap.md|Roadmap]]
```

Links may use `[[name]]`, `[[folder/name]]`, `[[name|shown text]]`,
`[[name#heading]]`, `[[name#^block]]`, or `[[name.md]]`. Note embeds such as
`![[name]]` and standard Markdown links such as `[Roadmap](folder/roadmap.md)`
are also recognized. Markdown links may encode spaces as `%20`. Link matching
is case-insensitive. Link examples inside fenced code blocks or inline code do
not create links, and web URLs are not vault links.

For a bare name that matches more than one note, Glacier prefers a match in
the source note's folder. Otherwise it selects the matching note with the
shortest vault path; ties are resolved in alphabetical path order. Folder
paths in wiki links identify that path directly. Unresolved note links remain
visible as “not written yet” and are not counted as notes. Embeds may also
refer to attachments; only Markdown notes appear as note links in the map.

The note reader and map use the same link resolution rules. The reader returns
the canonical extensionless target in `links_out` and adds its `resolved` or
`unresolved` state in `links_out_status`.

An embed can refer to an attachment in the vault:

```markdown
![[images/diagram.png]]
```

## File and folder names

For compatibility with Obsidian and Windows, do not use `:`, `*`, `?`, `"`,
`<`, `>`, `|`, or `\` in file or folder names. Names must not contain control
characters (0–31), end in a dot or a space, or use Windows device names such as
`CON`, `NUL`, `COM1`, or `LPT1` (including names with extensions). For reliable
Obsidian links, also avoid `#`, `^`, `[` and `]`. Keep attachments alongside the
notes that use them or in a shared folder such as `images/`.

Wiki links in normal Markdown text are checked; examples inside inline code and
fenced code blocks are treated as examples and are not checked as links.

## Check the folder

Glacier's `GET /api/memory/compat` endpoint checks note front matter, wiki links,
embedded files, and names. It returns `ok`, the number of Markdown notes checked,
and a list of problems with a plain-language suggestion for fixing each one.
