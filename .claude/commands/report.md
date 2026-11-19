---
description: Show task data (throughput, time per task, discovered and remaining tasks)
argument-hint: "[--feature N] [--since YYYY-MM-DD] [--csv PATH]"
---
Run `python scripts/report.py $ARGUMENTS` and show the output as it is.

- **Data only.** Don't add forecasts, estimates or commentary on the numbers.
- If `--csv` is given, the path must be **outside the repository**. Task titles are public, but `*.csv` files are blocked from commits. Default to `~/job-search-data/reports/` if the user doesn't name one.
- If the Audit section lists problems, point the user to them, and offer `/sync-backlog`.
