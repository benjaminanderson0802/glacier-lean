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
