# Deadline tracker release check

Release only when `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/deadlines/tests` passes. Tests use supplied calendar dates as the fake clock and cover 60/90-day reminders, 30/120-day reminders, the Jan 2–Mar 2 OSHA window, a county-specific appeal window, exact-date firing, and no duplicate firing. Each due item exposes a native Glacier note node for the reminder and a durable Glacier approval node.
