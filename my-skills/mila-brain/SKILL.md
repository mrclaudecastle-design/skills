---
name: mila-brain
description: Run, teach and improve Mila's brain (Qwen 3 8B) on the Mac, including fine-tuning, connecting each shop's own info with LangChain, and the privacy rules for training data. Use when working on how Mila thinks, answers, learns or remembers.
---

# Mila brain

Mila's brain is Qwen 3 8B, running on the Mac (or a GPU server), taught to be a calm, capable receptionist for Australian sole traders.

## House rules
- Never delete, move or overwrite anything. Each training run goes in a new dated folder, and old versions are kept.
- Privacy is on by default and the shop owner never has to set anything up.

## What good looks like
Reasons through the request, receptionist-ready, replies fast enough for a live call, handles being interrupted, and never makes up prices, times or promises.

## Run it on the Mac
Use `mlx-lm` with the downloaded `Qwen/Qwen3-8B` (see the `mila-models` skill). Check the mlx-lm README for the current commands before running.

## Teaching it (fine-tuning)
1. **Training data is mainly made up (synthetic):** realistic calls and texts written by a stronger model (Kimi K3 Pro or Hermes), then checked.
2. **Real data only when allowed:** issues a shop reported, and examples a shop agreed to share, with names and numbers taken out. This is mainly the 3 friends' businesses on free trials, with their OK.
3. Anything marked "Don't learn from this" is never used.
4. Fine-tune with LoRA through mlx-lm, save to a new folder, then test against the same set of calls as the last version before switching.

## Each shop's own info (LangChain and RAG)
- Each shop's prices, hours, services and FAQs live in that shop's own locked data. Mila looks them up when needed instead of memorising them.
- One shop's info is never mixed with another's.
- The server passes data through and keeps nothing. Backups go to the Mila Vault.

## Learning from shops over time
A start-up questionnaire, then a weekly thumbs up or down on real replies. Keep a per-shop memory in that shop's locked data.

## Where the latest decisions are
The True Direction vault on the Mac, under `02 Mila AI/` (`Mila Brain.md`, `Mila Data and Privacy.md`). Read those first, because they change.
