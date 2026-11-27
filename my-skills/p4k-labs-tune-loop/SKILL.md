---
name: p4k-labs-tune-loop
description: P4K Labs' hands-off loop that finds, tests, tunes, gates and freezes local AI models and settings with the no-drop rule. Use when upgrading or tuning any local model (LLM, embedder, voice), when running the weekly lab check, or when deciding whether a new model may replace the current one.
---

# P4K Labs tune loop

P4K Labs is the owner's local AI lab. This is its one procedure. Plan: `P4K Labs - Plan (28 Nov).md` (vault notes in `/Volumes/02-WORK/P4K Labs/Notes/`).

## House rules
- Never delete anything. Old models move to `parked/` with a line in `parked/LOG.md`.
- One heavy job at a time: take `/Volumes/02-WORK/.heavy-job.lock` (see `quiet-mac-gate`). Mac on power and idle. Headless only, never open windows.
- Two lanes never mix: **Mila lane** (original models only) and **Personal lane** (may use abliterated models; never read the owner's Hermes chats).
- Benchmarks are a floor, not a target. No result that drops any core score is kept.

## Folders (`/Volumes/02-WORK/P4K Labs/`)
- `stack.env`: the one setting every app reads: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FALLBACK`, `EMBED_MODEL`.
- `candidates/<date>-<name>/`: downloads waiting to be tested.
- `runs/<date>-<what>/`: every test run, with `result.json` and the exact command.
- `frozen/<date>-<name>/`: kept results, read-only, `SHA256SUMS.txt`.
- `parked/`: losers and replaced models, with `LOG.md`.
- Models that already exist stay in `/Volumes/02-WORK/Everything - Local AI/` (Ollama store, port 11435) and `/Volumes/02-WORK/MilaModels/`.

## The loop
1. **Watch** (weekly, read-only): new versions of the models and tools listed in the Parts list note, on Hugging Face and PyPI.
2. **Fetch** into `candidates/`. Check SHA-256 against the Hub's LFS hash. Mismatch = stop, report.
3. **Test**: the same tests on the same Mac for current and candidate:
   - speed: time to first word, tokens per second, peak memory (16K context);
   - floor: lm-evaluation-harness 0.4.13 `ifeval`, `gsm8k`, `mmlu_pro` (fixed subset, fixed seed);
   - our own: Mila brain bench + live call scripts (`mila-voice-test`, `call-replay-check`), RAG set (`local-rag`).
4. **Tune**, cheapest first, stop as soon as the target is met:
   a. settings (sampling per `model-qwen3-5`, context size, quant Q4/Q5/6-bit, KV cache type);
   b. prompt (DSPy 3.5 GEPA rewrites the system prompt or shop card, scored by step 3's own tests, local model as judge);
   c. model choice (e.g. Qwen3.5-4B vs 9B);
   d. LoRA (mlx-lm on the Mac, Unsloth on a rented GPU) only with hand-checked varied data.
5. **Gate**: keep only if every core score is equal or better and the floor passes. Otherwise write why in `runs/.../result.json` and park it.
6. **Freeze**: copy to `frozen/<date>-<name>/`, write `SHA256SUMS.txt`, `chmod -R a-w`. Record the exact settings in `frozen/.../CARD.md`.
7. **Offer / swap**:
   - Mila lane: write a short note for the Mila thread. Never auto-swap Mila's model.
   - Personal lane: update `stack.env`; keep the previous entry as `LLM_FALLBACK`.
8. **Report**: add the numbers to the Benchmark Hub seed (`/Volumes/02-WORK/Benchmarks/kit/seed/apps.json`) and to `P4K Labs - Results.md`.

## Trust tags for every number
- strong: our test set, this Mac, independent tool.
- fair: our hardware but the maker's test, or our test on a rental.
- weak: a model card or blog claim not re-run by us.

## If blocked
Retry up to 5 times with growing waits and a workaround between tries. Then move on and list the block once for the owner. Never force past a safety check, password or licence.
