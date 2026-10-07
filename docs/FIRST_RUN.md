# First-run setup

Glacier's first-run proposal is available offline at `GET /api/starter`. It checks
the computer and installed tools locally, then explains the recommended run mode
and local model, reports coding agents found on `PATH`, and lists up to three
reviewed starter automations whose required tools are present. The proposal also
lists up to three free, open-source tools that could be useful, with their
licenses and official download pages. It does not install anything or contact
the internet.

Send selected template ids and a mode (`low` or `standard`) to
`POST /api/starter/apply`. Glacier validates and saves the flows through the
same environment validation and vault history used by the template gallery.
Repeating the request does not create a second copy of a template already
chosen. The selected mode and local model are saved in `GLACIER_HOME/settings.json`
and are returned by `GET /api/system/settings`.

Low mode uses one run at a time and recommends `qwen3:0.6b`. Standard mode
recommends `granite3.3:2b`. Glacier reuses an installed model when it is in its
evaluated model list, or the smallest installed chat model, as described in
[`LOW_RESOURCE.md`](LOW_RESOURCE.md).
