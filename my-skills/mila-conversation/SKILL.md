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
| New shop joins | `nodes/shop_card.py` | Turns the shop's answered questionnaire into Mila's instructions, greeting and checks. No training needed. |
| Before she speaks | `nodes/guard.py` | The safety net. Checks every reply from the brain and fixes it if needed: a number the caller gave is read back, no price that isn't on the card, no time that isn't a free diary spot, no call back promised without a number, no made-up deadlines, no lists, not too long. |
| Mila replies | `nodes/say_it.py` | Turns "0412 345 678", "$85", "2:30pm" and "3/14 Smith St" into the words a person would say, just before the voice reads them. |
| Every turn | `nodes/stopwatch.py` | Times hearing, thinking and speaking against limits, and flags the slow step. |

`nodes/turn.py` joins them into one step of a call, text in and text out, so the whole conversation logic can be tried without any voice models. Run `python3 nodes/turn.py` to read through a practice call that goes from a clear line to a bad one and ends on the keypad.

Run any node by itself to see it work: `python3 nodes/say_it.py`.
Run all checks: `python3 tests/test_nodes.py`.

## Plug and play: one Mila, a card per shop
Mila is trained once, as a receptionist. A new shop does not get its own training. It answers a short questionnaire (`shop/questionnaire.json`, 14 plain-word questions, only 4 of them required) and `nodes/shop_card.py` turns the answers into everything that changes per shop: her instructions, the greeting, the country for lingo, and sanity checks such as the days the shop works. Everything unanswered gets a safe default, for example no prices means she never quotes one.

    card = ShopCard.load("shop/examples/birch-and-co.json")
    card.missing()                 # what's still needed, in the owner's words
    call = Call(card=card)         # the whole call now follows this shop's answers

The training calls in `finetune/data-v2` each carry a different shop's card, so the brain learns to follow whatever card it is given rather than memorising one shop. Shop-specific tweaks go in the card; receptionist manners go in training.

## Habits in code, polish in training
Two training runs (see `finetune/README.md`) showed that the untrained brain with a good shop card already answers well, and that training alone does not reliably keep must-do habits. So the split is: anything that must be right every time lives in `guard.py`, where it is checked on every reply; training is only for tone and brevity. `Call.speak(reply, diary)` runs a brain reply through the guard and then `say_it`.

## How sure is sure enough
`plausibility.py` uses two lines: at 0.80 or above she carries on, from 0.50 she reads it back first, below that she goes to the repair ladder. A reading backed by only one voter is never treated as certain. Tune these from real calls, not by feel.

## Adding a country
Copy `lingo/au.json` to a new file such as `nz.json`, and fill in the phrases, what each means, and the few light phrases she may mirror. No code changes.

## Teaching Qwen the same habits
`finetune/` has a starter kit: a script that writes made-up training calls (Australia about three in four, Canada the rest), the training settings for the Mac, and step-by-step notes in `finetune/README.md`. The training has not been run yet. For the privacy rules on real calls, see the `mila-brain` skill.

## Not built yet
These need the live call pipeline, so they are not in this kit: knowing when the caller has finished (Pipecat Smart Turn), stopping the moment she is interrupted, speaking the first sentence while the rest is still being worked out, and noise filtering. Check each tool's current docs before wiring it in.
