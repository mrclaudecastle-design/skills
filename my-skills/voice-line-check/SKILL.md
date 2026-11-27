---
name: voice-line-check
description: Check a voice by having it say 72 call lines and 35 hard lines, then scoring each with a hearing model.
---

# Voice line check

## If you're picking this up
- **What it is:** a pass/fail check of how reliably a voice says lines, using a hearing model as the judge. It is not a listening test.
- **Where the files are:** `$MILA_BUILD/src/blend_fix_lab.py` (`MILA_BUILD` = your voice build folder). Results go to `results/blend_fixes/`.
- **How to run it** (a model job: only when nothing else is running):
  ```bash
  cd "$MILA_BUILD" && source env.sh && HF_HUB_OFFLINE=1 python src/blend_fix_lab.py 3clips phonon
  ```
- **How to check it worked:** a new file in `results/blend_fixes/` and two sample mp3s per variant. Open the samples and listen to them.
- **What's next:** compare the clean-line counts between voices. Then an owner listening test.
- **Rules:** never delete, new names only, one model job at a time, no downloads.

## Steps
1. Check no other model job is running.
2. Run the lab with the voice variants to compare. It is slow; run it in the background.
3. Scoring is the same for every voice: the 72 lines Mila says in calls and 35 hard lines. A line is clean when the **medium** hearing model hears at least 80% of the words and no silence is longer than 1.5 seconds.
4. The retry check uses the small hearing model, so the judge is not the same as the checker.
5. Report clean lines out of 72 and out of 35, by voice. Name the lines that fail.

## Traps
- A line the hearing model misses may still sound fine. Listen to failures before blaming the voice.
- Don't compare results from different hearing models.
- Text clean-up (dashes, "pm", stray digits) changes the score. Keep it the same for every variant.
