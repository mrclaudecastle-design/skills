---
name: quiet-mac-gate
description: Run timed jobs only when the Mac is quiet, watch for other jobs during each one, and mark every result valid or not valid.
---

# Quiet-Mac gate

## If you're picking this up
- **What it is:** a way to run timed test calls (or any timed job) so the numbers mean something.
- **Where the files are:** `$MILA_BUILD` (your voice build folder). A working example is `run_round4d_timed_d_fix2_lib19.sh`.
- **How to run it:** start the script in the background with no arguments. It waits by itself.
- **How to check it worked:** read `logs/round4d_timed_d_fix2_lib19_<time>.txt`. Each call is one line. Only lines with `check=valid` count.
- **What's next:** write a dated note of the valid numbers; say which calls were not valid and why.
- **Rules:** never delete, new names only, one model job at a time, never touch another thread's jobs.

## Steps
1. Copy an existing queue script to a new name. Never edit one that is running.
2. Before each job, check all of these, twice, 30 seconds apart: load under 3, no Time Machine backup (`tmutil status`, `Running = 1`), no other model job, no OCR job, at least 30% memory free (`memory_pressure -Q`).
3. If any check fails, write one log line saying which one, wait 5 minutes, and try again. Stop after 8 hours.
4. While the job runs, sample every 5 seconds for Time Machine, OCR jobs and other model jobs. Write what you see to a file.
5. After the job, mark it NOT VALID if anything was seen during it, if it stalled (hearing or turn detection over 3 seconds), if the brain errored, or if too few caller lines were answered.
6. Save the load at start and end, and whether Time Machine was on at the end.

## Detector traps (each one cost time)
- Skip shell, search and download commands (`zsh sh awk grep tail find bfs curl`), or a waiting queue looks like a model job.
- `ollama serve` with no model loaded is idle. `ollama runner` is a loaded model: wait for it.
- A process that only mentions a model path isn't a model job.
- Log "valid" only after checking Time Machine at the end and during the job, not just before.

## If the Mac crashes or the drive drops
Re-check files, restart the queue (its working folder is gone after a drop), use a gentler gate (load under 8, no Time Machine, 50% memory free) for jobs that need no timing, and say so in the report.
