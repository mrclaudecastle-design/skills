---
name: mila-conversation
description: Small independent building blocks that make Mila sound human on a live call - natural spoken numbers and addresses, understanding Australian and Canadian everyday talk, voting on what the caller most likely meant, a "press 1 if that's what you meant" fallback, timing, and a Qwen fine-tuning starter kit. Use when building, wiring up or improving how Mila listens, answers and recovers from misunderstandings.
---

# Mila conversation kit

Each part ("node") is one small file that does one job, has no dependencies, and can be run, tested or swapped on its own. Wire them into the call pipeline (Pipecat) in the order below. Small parts load fast and a problem in one doesn't take the call down.

## House rules
- Never delete, move or overwrite anything. New training runs and data go in new folders.
- Mila **understands** local talk and goes along with it. She **never starts** slang.
- She never invents a price, a time or a promise. When unsure, she checks or offers a call back.

## The nodes, in call order

| Step | Node | Job |
|---|---|---|
| Caller speaks | `nodes/lingo.py` | Turns local talk into plain meaning ("yeah nah" is no, "this arvo" is this afternoon) and notes signals like yes, no, broken, busy. Countries are files in `lingo/` (`au.json` first, then `ca.json`). |
| Deciding what was meant | `nodes/plausibility.py` | Several voters (the ears' top guesses, the brain's reading, plain rules) vote. Sanity checks knock out nonsense, like a day the shop is closed. Returns the winner, how sure she is, and `act`, `confirm` or `repair`. |
| Not sure | `nodes/repair.py` | The second approach. Miss 1: say her best guess back. Miss 2: "press 1 for Thursday at two, press 2 for Tuesday at two". Miss 3: take a message and promise a call back. |
| Waiting | `nodes/fillers.py` | Listening sounds ("mm-hm") and holding lines ("let me check the diary"), never the same twice in a row. |
| Mila replies | `nodes/say_it.py` | Turns "0412 345 678", "$85", "2:30pm" and "3/14 Smith St" into the words a person would say, just before the voice reads them. |
| Every turn | `nodes/stopwatch.py` | Times hearing, thinking and speaking against limits, and flags the slow step. |

Run any node by itself to see it work: `python3 nodes/say_it.py`.
Run all checks: `python3 tests/test_nodes.py`.

## How sure is sure enough
`plausibility.py` uses two lines: at 0.80 or above she carries on, from 0.50 she reads it back first, below that she goes to the repair ladder. A reading backed by only one voter is never treated as certain. Tune these from real calls, not by feel.

## Adding a country
Copy `lingo/au.json` to a new file such as `nz.json`, and fill in the phrases, what each means, and the few light phrases she may mirror. No code changes.

## Teaching Qwen the same habits
`finetune/` has a starter kit: a script that writes made-up training calls (Australia about three in four, Canada the rest), the training settings for the Mac, and step-by-step notes in `finetune/README.md`. The training has not been run yet. For the privacy rules on real calls, see the `mila-brain` skill.

## Not built yet
These need the live call pipeline, so they are not in this kit: knowing when the caller has finished (Pipecat Smart Turn), stopping the moment she is interrupted, speaking the first sentence while the rest is still being worked out, and noise filtering. Check each tool's current docs before wiring it in.
