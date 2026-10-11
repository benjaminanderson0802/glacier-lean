# Outreach batch — 2026-10-11

This folder contains individually prepared written pitches for the ventures with a pitch and a prepared prospect list. The batch has 29 records: 3 SAM amendment digest, 1 Alabama bid triage, 11 Alabama license roster checks, and 14 FBA fee checks. This includes 26 public business email addresses and 3 contact-form-only routes. No usable job-closeout route was found: its three listed sites exposed service/appointment intake only. Gaines Family Farmstead exposed a newsletter signup but no business contact route, so it was dropped. Freight claims, warranty, co-op postcards, and property tax had no `prospects.csv`.

The contact address or form and its source URL are recorded per row. The queue excludes personal email addresses and prospects whose public route could not be verified. Email bodies retain only the requested `{{POSTAL_ADDRESS}}` placeholder; fill it with the accurate business postal address before any owner sends a message. Offer copy follows the local venture pilot terms because the new public pilot pages could not be verified from this environment.

## Sending rules

- Drafts only. `send_queue.py` validates the CSV and writes Gmail-draft-ready JSON; it has no send integration and never sends messages.
- The owner reviews and sends each email or submits each contact form manually. Keep to **30 sends per day maximum** across all ventures.
- Send one initial message to each business, then at most one polite follow-up on day 5. Stop on any reply, decline, or opt-out; never send the follow-up after a reply or opt-out.
- Check `suppression.csv` before preparing/sending a batch and add every opted-out or otherwise suppressed business/email there. The validator rejects a suppressed email or business, case-insensitively. Record a manual send in `last_sent_at` with `reason=sent`; the validator blocks that business/email for seven days. Use `reason=opt_out` for permanent suppression.
- Contact-form rows are placed in `contact_form_queue` in the JSON for manual use; the script does not open or submit forms.
- No phone calls, guessed addresses, tracking pixels, or automatic sending/follow-up.

## Files

- `batch-2026-10-11.csv` — prepared messages and contact provenance.
- `suppression.csv` — suppression and recent-send history, with columns `contact_email,business,last_sent_at,reason` (`last_sent_at` uses `YYYY-MM-DD`).
- `send_queue.py` — queue validator and JSON formatter.
- `tests/test_send_queue.py` — validator unit tests.

Generate the draft data with:

```sh
~/w/glacier-lean/.venv/bin/python ventures/outreach/send_queue.py
```

The default output is `gmail-drafts-2026-10-11.json` in this folder. The JSON marks follow-ups as manual review and `not_before_day: 5`; it does not schedule them.
