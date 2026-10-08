# Starter flows

- Daily report: records a short daily summary in memory.
- Website monitor: checks a website and asks before triggering the configured failure alert; the final `false` is intentional so a failed check ends the run as failed and sends the alert.
- Test and fix: runs tests, asks Codex to fix failures, and checks the result for up to three attempts.
- Weekly research: asks Codex for a weekly research summary and saves it in memory.
- Folder cleanup: reviews temporary files, asks for approval, then moves approved items to a review folder.
- Sort incoming messages: puts incoming text into one of three choices and saves the result.
- Folder backup: copies the flow's working folder into a new dated backup folder and compares the copy with the original.
- Run another flow: starts the daily report flow from inside a second flow.
- Nightly job: runs the test command each night with retries and a time limit.
- Explain an error: asks Codex to explain an error in plain language and saves the explanation.
- Summarise a document into a note: reads a local document, asks a local model for a short summary, and saves it in memory.
- Weekly tidy of my Downloads folder: lists files older than seven days in a review note. It never moves or deletes anything; you decide what to do with the list.
- Turn meeting notes into a task list: turns a local meeting-notes file into checkbox tasks with a local model.
- Watch a web page for changes: reads one approved page, compares it with the last saved copy, and records a change note.
- Morning brief from my notes: finds notes changed yesterday, summarises them with a local model, and saves a brief.
- Check my backups ran: checks whether a recent file is present in the backup folder and saves a clear status or stale-backup alert note.

These six templates are designed for local models or ordinary steps; none needs a paid service. Replace the example document paths with your own files. The Downloads and backup folder settings start at `$HOME/Downloads` and `$HOME/Backups`. Open **Templates** and choose **Use this template** to add one to your flows. Each template checks for a fresh, non-empty result note; meeting tasks also checks for a checkbox or a clear no-tasks result. A stale backup is reported in its note and does not make the run fail.
