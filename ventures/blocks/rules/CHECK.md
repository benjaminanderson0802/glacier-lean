# Rules checker release check

The spec release check is to accept every known-good sample and reject every
hand-made bad sample. Run:

```sh
python -m pytest -q ventures/blocks/rules/tests
```

Every individual result must carry the official source citation used by its
ruleset. Missing fields are `uncertain`; explicitly present malformed values
are `fail`. A `pass` means the supplied values satisfy the cited data-field
checks; it is not a legal determination or government certification.
