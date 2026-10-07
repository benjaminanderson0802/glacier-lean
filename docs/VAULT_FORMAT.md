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

Links may name the exact file, omit the `.md` extension, or use a file name by
itself when that name is unique in the folder. If two notes share a name, use
their folder paths so the intended note is clear. Embeds use the same form with
an exclamation mark, and the referenced file must be present in the vault:

```markdown
![[images/diagram.png]]
```

## File and folder names

For compatibility with Obsidian and Windows, do not use `:`, `*`, `?`, `"`,
`<`, `>`, or `|` in file or folder names. Names must not end in a dot or a
space. Keep attachments alongside the notes that use them or in a shared folder
such as `images/`.

## Check the folder

Glacier's `GET /api/memory/compat` endpoint checks note front matter, wiki links,
embedded files, and names. It returns `ok`, the number of Markdown notes checked,
and a list of problems with a plain-language suggestion for fixing each one.
