---
name: heretic-model-edit
description: Make our own abliterated (uncensored) or less-sloppy/less-sycophantic copy of an open model with Heretic, scored automatically, on a rented GPU. Use when an abliterated model is wanted for the personal lane, or to test Heretic's terse/noslop/nosyco edits.
---

# Heretic: edit a model without training

Researched 28 Nov 2026: github.com/p-e-w/heretic README, PyPI `heretic-llm` 2.1.0 (8 Nov 2026), licence AGPL-3.0-or-later. Part of P4K Labs.

## House rules
- Never delete anything. Results go to `/Volumes/02-WORK/P4K Labs/candidates/`.
- **Abliterated models are for the personal lane only. Never for Mila or customers.**
- AGPL is fine for using the tool. The edited model keeps its base licence (Qwen3.5 = Apache-2.0). Don't ship Heretic code inside a product.
- Rented GPU: only the public model goes up. No customer data, no personal chats.

## What it does
- Finds the "refusal direction" in the model and removes it (directional ablation). No training.
- Optuna searches the settings and scores each try on two things: refusal rate (lower is better) and KL divergence from the original (lower = less brain damage). Pick the try with few refusals AND low KL.
- Other ready configs in the repo: `config.noslop.toml` (less filler), `config.nosyco.toml` (less flattery), `config.terse.toml` (shorter answers), `config.nohumor.toml`, `config.emotions.toml`.
- Heretic 1.x configs do not work in 2.x.
- Hybrid models like Qwen3.5 are supported from 2.x ("many modern hybrid models"); 1.0 did not support them. Use 2.1.0 or newer.

## Where to run it
- A 4B model takes about 30-40 min on an RTX 3090 (README). A 9B in bf16 needs about 24 GB of GPU memory: rent one 48 GB card (RTX A6000, RunPod Secure Cloud, about US$0.6-0.7/h). Budget 2 hours.
- `quantization = "bnb_4bit"` lowers memory to roughly a 4-bit model's size, at a small accuracy cost. This needs NVIDIA (bitsandbytes), so it is not a Mac option.
- Not for the 16 GB Mac: 9B bf16 doesn't fit.

## Steps (on the rented GPU)
```sh
python3 -m venv ~/h && . ~/h/bin/activate
pip install "heretic-llm==2.1.0"          # pin the version
export HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
heretic Qwen/Qwen3.5-9B                   # default = refusal removal
```
- At the end it offers: save, upload, chat, benchmark. Choose **save** only. Never upload.
- Save to `/workspace/out/Qwen3.5-9B-heretic-<date>/`.
- Write down the chosen try's refusal count and KL value.
- Convert to GGUF on the rental (llama.cpp `convert_hf_to_gguf.py` then `llama-quantize ... Q4_K_M`) and MLX on the Mac (`mlx_lm.convert --q-bits 4`).
- `sha256sum` every file, copy home with rsync over SSH, check sums match, then stop the rental.

## Gate (must pass, or it's parked)
- Refusals under 5 of 100 on Heretic's harmful-prompt set.
- KL divergence under 0.1. For scale: Heretic's own Gemma-3-12B run scored 0.16 vs 0.45-1.04 for older hand-made abliterations (v1 README); a community Heretic run on Qwen3.5-4B reports 0.04 (coder3101/Qwen3.5-4B-heretic card, unverified).
- IFEval and MMLU-Pro subset no more than 1 point below the original Qwen3.5-9B on the same Mac.
- Must beat or match the current fallback, mlabonne Qwen3-8B abliterated, on the same tests.

## After it passes
- Freeze it (`p4k-labs-tune-loop` step 6), then add it to the SSD Ollama store with a Modelfile using the Qwen3.5 settings from `model-qwen3-5`.
- Point the Hermes `local-qwen` profile at it only after the gate. Keep the old model for rollback. Never read the user's Hermes chats.
