---
name: call-replay-check
description: Replay saved calls through Mila's guard with no model, switch each part off in turn, and report what changed.
---

# Call replay check

## If you're picking this up
- **What it is:** a text-only test of the safety net. It needs no voice and no brain, so it is safe while the Mac is busy.
- **Where the files are:** `$MILA_BUILD/src/` (`MILA_BUILD` = your voice build folder). Latest: `reply_guard_fix2_lib19.py`, `test_guarded_offline_fix2_lib19.py`, `ablate_fix2_lib19.py`. Saved calls are in `results/calls/*.json`.
- **How to run it:**
  ```bash
  cd "$MILA_BUILD" && source env.sh && nice -n 19 python -B src/test_guarded_offline_fix2_lib19.py --replay-out results/guard_offline/replay_<new name>
  ```
- **How to check it worked:** the last line reads `N/N checks passed`, and the new file appears in `results/guard_offline/`. If the name already exists, it refuses. Pick another.
- **What's next:** compare with the last version (below), then the switch-offs.
- **Rules:** never delete, new names only, one model job at a time. Copy files to new names before changing them. Never edit the shared library in the models folder.

## Steps
1. Copy the newest `reply_guard`, `shop_setup`, `brain_guarded`, `test_guarded_offline` and `ablate` files to new names, and change their imports.
2. Run the checks. A failing check is a real fault unless you changed the rule on purpose. If you did, say so in the report.
3. **Replay compare.** Run the replay of the old and the new version in separate processes (they share module names). Print every reply whose spoken text or booking result differs. Read them all.
4. **Switch-offs.** `python -B src/ablate_<version>.py` turns each part off in turn. A part whose removal breaks nothing is either not needed or not tested. If a test sets `OFF`, restore it afterwards or the result is wrong.
5. Add a test for every new fault, using the real words from the saved call.
6. Report: counts, what changed and why, faults found, what is not tested.

## Traps
- The library's own name finder can return nothing for "It's Unit twelve". Don't assume it heard a name.
- Number words in suburb names ("Five Dock", "Seven Hills") must not become digits.
- Test that a wrong address is refused both when it has a wrong number and when a number is missing.
