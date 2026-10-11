# Portal filer setup

The portal filer uses a private, worktree-local Playwright installation. This keeps its browser runner available in a clean checkout without depending on `glacier/web/node_modules` or desktop packaging.

From the repository root, install the pinned Node dependencies:

```sh
npm ci --prefix ventures/blocks/filer
```

Install the Chromium browser once on a machine that does not already have the Playwright browser cached:

```sh
npx --prefix ventures/blocks/filer playwright install chromium
```

Then run the local mock portal checks with Glacier's project Python interpreter:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests
```

The checks use a local mock portal and synthetic credentials. They cover prepare without submission, submission approval, and idempotent confirmation replay. They do not test a real portal or authorize a filing.
