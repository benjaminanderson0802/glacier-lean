# Start an Environment when something happens

Glacier supports local file and webhook starts. Both create ordinary Environment runs, so the starting step and its result appear in run history and later steps can use the result as `{prev_output}`.

## When a file appears

Add **When a file appears**, choose an existing folder outside Glacier's data folder, and optionally set a filename pattern such as `*.pdf`. Glacier checks the folder locally about once per second. Each matching file path starts one run; handled paths are saved in `triggers.sqlite` so a backend restart does not run them again. Files that arrive while Glacier is stopped are found after it starts again.

The `{trigger_file}` placeholder contains the full path. The trigger step also makes that path the previous output. In a Command step, the placeholder is inserted as one shell-quoted value; use it without adding quotes around it. Glacier refuses watched folders inside its own data folder, including the vault.

## When called from this computer

Add **When called from this computer** to an Environment. A local program can start it with:

```sh
curl -X POST http://127.0.0.1:8000/api/hooks/MY-FLOW \
  -H 'Authorization: Bearer INSTALL_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"event":"ready"}'
```

Use the install token shown by Glacier for this computer. The normal local request guard checks the token and same-origin rules before the route runs. Requests must contain JSON and may be at most 1 MiB. The response contains only the run ID. Values under keys named like `secret`, `token`, `password`, `credential`, or `api_key` are redacted before the run sees them.

Following steps can use `{trigger_body}` for compact JSON or `{prev_output}` for the same JSON. In a Command step, `{trigger_body}` is inserted as one shell-quoted value; use it without adding quotes around it. The run records that it started from a local webhook and which trigger step received the call.

## Pausing starts

Set the Environment's `enabled` field to `false` to pause file and webhook starts. Set it back to `true` (or remove the field) to resume them.
