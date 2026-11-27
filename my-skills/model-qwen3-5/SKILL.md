---
name: model-qwen3-5
description: How to run, set up, test and tune Qwen3.5 (9B and 4B) on a 16 GB Apple Silicon Mac with Ollama or MLX - the right sampling settings, thinking on/off, memory limits and known traps. Use whenever Qwen3.5 is downloaded, served, benchmarked, prompted or fine-tuned.
---

# Qwen3.5 (9B and 4B) on the Mac

Researched 28 Nov 2026 from the official model cards (huggingface.co/Qwen/Qwen3.5-9B, Qwen/Qwen3.5-4B), the mlx-lm 0.32.2 source, and Ollama's MLX notes. Part of P4K Labs.

## House rules
- Never delete, move or overwrite anything. Only add. See `safe-mac-work`.
- Everything lives on `/Volumes/02-WORK`. The Mac's own disk is full.
- One heavy job at a time (use `quiet-mac-gate`). Headless only, no windows.
- Mila lane: original models only, never an abliterated or "distilled" upload.

## What it is
- Released Mar 2026, licence Apache-2.0 (commercial use fine).
- Multimodal: text + images + video. Text-only runtimes drop the vision part.
- Hybrid brain: of 32 layers, 24 are "Gated DeltaNet" (linear attention, fixed small memory) and 8 are normal attention. So long context costs far less memory than Qwen3-8B.
- Native context 262,144 tokens. Thinking mode is ON by default.
- Newer Qwen3.8 (Aug 2026) only comes in 27B and up: too big for 16 GB.

## Published scores (from the model card, Qwen's own runs: trust tag "weak" until we re-run them)
| Test | Qwen3.5-9B | Qwen3.5-4B |
|---|---|---|
| IFEval (following instructions) | 91.5 | 89.8 |
| MMLU-Pro (knowledge) | 82.5 | 79.1 |
| GPQA Diamond | 81.7 | 76.2 |
| BFCL-V4 (tool calls) | 66.1 | 50.3 |
| TAU2-Bench (agent, customer service) | 79.1 | 79.9 |
| OCRBench (reading images) | 89.2 | 85.0 |
| OmniDocBench1.5 (documents) | 87.7 | 86.2 |
TAU2 is the closest public test to a receptionist: 4B matches 9B there, so 4B is the speed candidate for Mila.

## Files (sizes checked on the Hub 28 Nov 2026)
| Use | Repo | File | Size |
|---|---|---|---|
| Ollama/llama.cpp | `unsloth/Qwen3.5-9B-GGUF` | `Qwen3.5-9B-Q4_K_M.gguf` | 5.68 GB |
| Ollama, higher quality | same | `Qwen3.5-9B-Q5_K_M.gguf` | 6.58 GB |
| Alternative quant | `bartowski/Qwen_Qwen3.5-9B-GGUF` | `Qwen_Qwen3.5-9B-Q4_K_M.gguf` | 6.17 GB |
| MLX 4-bit | `mlx-community/Qwen3.5-9B-4bit` | 2 safetensors | 5.95 GB |
| MLX 6-bit | `mlx-community/Qwen3.5-9B-6bit` | 2 safetensors | 8.19 GB |
| 4B | `Qwen/Qwen3.5-4B` (+ `mlx-community/Qwen3.5-4B-4bit`) | | |
Always check the SHA-256 against the Hub's LFS hash after download.

## Settings (official "best practices")
| Mode | temperature | top_p | top_k | min_p | presence_penalty |
|---|---|---|---|---|---|
| Thinking, general | 1.0 | 0.95 | 20 | 0 | 1.5 |
| Thinking, precise coding | 0.6 | 0.95 | 20 | 0 | 0.0 |
| No thinking, general (Mila, chat) | 0.7 | 0.8 | 20 | 0 | 1.5 |
| No thinking, reasoning | 1.0 | 1.0 | 40 | 0 | 2.0 |
- repetition_penalty 1.0 always. Never greedy (temperature 0) for real use: it loops.
- presence_penalty 0-2 stops repeating; too high can mix languages. Tune it, don't guess.
- The card's quickstart and best-practices sections disagree on "no thinking, reasoning" (top_p 0.95 vs 1.0, top_k 20 vs 40). Test both.
- Old Qwen3 settings (temp 0.6, top_p 0.95, presence 0) are NOT the right ones for 3.5. Our Modelfiles still have the old ones.

## Thinking on/off
- OpenAI-style API: `"chat_template_kwargs": {"enable_thinking": false}` in the request body.
- Ollama: `"think": false` in the request, or `/set nothink` in the CLI.
- mlx-lm: `--chat-template-config '{"enable_thinking": false}'` (same flag we used for Qwen3-8B).
- Mila must run with thinking OFF: thinking adds seconds before the first word.
- In chat history keep only final answers, never the `<think>` part (the template does this; custom code must too).

## Memory on 16 GB
- Keep the model plus cache under about 11 GB.
- The card says keep 128K context for best thinking. On 16 GB that is not possible with 9B; use 16K-32K and test long tasks separately.
- Because only 8 layers keep a normal cache, 32K context is cheap. Measure peak memory, don't assume.

## Running it
- Ollama (MLX engine by default from 0.40 on Apple Silicon): `ollama pull qwen3.5:9b` or `ollama create` from the GGUF with a Modelfile. Our SSD server is port 11435 (see P4K Labs runbook).
- mlx-lm 0.32.2 supports it (`mlx_lm/models/qwen3_5.py`, drops vision and MTP weights): `mlx_lm.server --model <path> --host 127.0.0.1 --port 8090`.
- Images or documents: use mlx-vlm 0.8.x (`mlx_vlm.generate ... --image`), the 4-bit repo was made with it.
- Tool calls: the card's servers use parser `qwen3_coder` (tool calls in XML-ish format). Test tool calling through Ollama before relying on it.

## Fine-tuning (only after settings and prompt tuning are maxed)
- mlx-lm LoRA works on its linear layers: `mlx_lm.lora --model <mlx path> --train --data <dir> --iters 300 --batch-size 1 --grad-checkpoint`.
- Use `mlx-lm-lora` 5.10.x for DPO/ORPO style tuning.
- Bigger runs (full bf16, 9B): rent one 48 GB GPU and use Unsloth 2026.11.x. See P4K Labs plan and `gpu-rental`.
- Lesson from Qwen3-8B run-01/run-02: narrow templated data made the model worse than untrained + shop card. Hand-written, varied data only, and every run must pass the no-drop gate.

## Family variants (same architecture, checked 28 Nov 2026)
| Model | What it is | Use |
|---|---|---|
| `Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B` | trained on ~250K math/science answers from DeepSeek-V4-Pro; maker reports +0.93 MMLU-Pro (math/physics/chem) and 36% fewer tokens per correct answer | personal lane, numbers work; blend ingredient |
| `xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic` | Heretic copy of the above; refusals 3/100, KL 0.042 | personal lane ONLY |
| `empero-ai/Qwen3.8-9B` | community distill of Qwen3.8 2.4T into Qwen3.5-9B. NOT an official Alibaba model. Own numbers inconsistent (GSM8K down 1.5) | test only |
- There is no official Qwen3.8 at 8B or 9B. Official Qwen3.8 = 27B, Flash-Next 180B, 2.4T.
- No real DeepSeek V4 model fits a 16 GB Mac (hundreds of billions of parameters). These distills are the DeepSeek option.
- Distills think with temperature 0.6, top_p 0.95, top_k 20 (their cards), not the official 1.0.
- Blending: same architecture, so mergekit (TIES/DARE/SLERP) works between them. Never blend an abliterated model into anything for Mila. Every blend goes through `p4k-labs-tune-loop`.

## Traps
- `presence_penalty` is not supported by every runtime: check the server actually applies it (compare outputs).
- Prefix caching with linear-attention layers is newer code: measure time to first word with the same long shop card twice. If the second call isn't faster, the cache isn't working.
- "Qwen3.5-9B-...-abliterated-heretic" and "Claude-distilled" uploads on the Hub are from small unknown uploaders. Not reputable. Make our own with `heretic-model-edit`.

## Checks before calling it done
1. SHA-256 matches the Hub.
2. Tokens per second, time to first word and peak memory measured at 16K context.
3. Our own tests (Mila brain bench, live call scripts) no lower than the current model.
4. Results written to the Benchmark Hub and the P4K Labs Results note.
