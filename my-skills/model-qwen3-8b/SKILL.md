---
name: model-qwen3-8b
description: Settings, files and lessons for Qwen3-8B, the model Mila and the personal Hermes setup run today (original + mlabonne abliterated). Use when running, testing or comparing against Qwen3-8B, or before replacing it.
---

# Qwen3-8B (current model)

Researched 28 Nov 2026 from huggingface.co/Qwen/Qwen3-8B and our own runs. Part of P4K Labs. Its likely successor is in `model-qwen3-5`.

## House rules
Never delete. Mila keeps her own copy. Abliterated copy is personal lane only.

## Where our copies are
- Mila: `/Volumes/02-WORK/MilaModels/Qwen3-8B-mlx-4bit` (MLX 4-bit, 4.3 GB). Read-only master in `Mila-Frozen-Master/2026-11-23`.
- Personal: `/Volumes/02-WORK/Everything - Local AI/models/original-Qwen3-8B/Qwen3-8B-Q4_K_M.gguf` and `models/abliterated-Qwen3-8B/mlabonne_Qwen3-8B-abliterated-Q4_K_M.gguf`, served by the SSD Ollama on 127.0.0.1:11435 (`start-local-ai.command`), Hermes profile `local-qwen`.

## Facts
- Licence Apache-2.0. Native context 32,768 tokens; 131,072 only with YaRN. Our Modelfiles set `num_ctx 64000`: past 32K this needs YaRN, so treat answers past 32K as untested (WHERE-THINGS-ARE says 40,960).
- Thinking ON by default. Turn off with `enable_thinking=False` or `/no_think` in the message.

## Settings (official)
- Thinking: temperature 0.6, top_p 0.95, top_k 20, min_p 0. Never greedy.
- No thinking (Mila): temperature 0.7, top_p 0.8, top_k 20, min_p 0.
- Our Modelfiles use the thinking set (0.6/0.95) for both. For no-thinking chat, test 0.7/0.8.

## Our numbers (this Mac, 16 GB)
- About 30-35 tokens/s (MLX 4-bit); peak memory about 5.3 GB during LoRA; about 10 GB loaded at 64K context in Ollama.
- Mila reply wait 2.05 s to first word on 27 Nov (target 1.12 s), measured on a busy Mac.
- run-01 and run-02 LoRA were worse than untrained + shop card. Untrained + shop card + guard is the base.

## Before replacing it
Run `p4k-labs-tune-loop` with this model as "current". The new model must match or beat it on every core score.
