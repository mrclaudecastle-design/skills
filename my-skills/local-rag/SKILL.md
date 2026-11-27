---
name: local-rag
description: Build, test and auto-tune a fully local RAG (look-up-then-answer) setup with LangChain/LangGraph, Qwen3 embedding and reranker models, and a single-file SQLite vector store, scored by Ragas. Use when an app must answer from its own documents (shop cards, Desk files, vault notes) or when RAG settings need tuning.
---

# Local RAG and RAG tuning

Researched 28 Nov 2026 from PyPI, the Qwen3-Embedding / Qwen3-Reranker / Qwen3-VL-Embedding model cards, and the LangChain and Ragas docs. Part of P4K Labs.

## House rules
- Never delete anything. Indexes are rebuilt into a new file, the old one kept.
- Everything local, on 127.0.0.1. Real customer data and personal notes never leave the Mac.
- Tracing off: `LANGSMITH_TRACING=false`, `LANGCHAIN_TRACING_V2=false`. Also `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `ORT_DISABLE_TELEMETRY=1`.
- No Google models (embeddinggemma is out). No non-commercial licences for Mila.

## Parts (versions checked 28 Nov 2026, pin them)
| Job | Pick | Licence | Why |
|---|---|---|---|
| Glue | `langchain` 1.5.2, `langchain-ollama` 1.2.0 | MIT | Mila already uses LangChain; plain chains |
| Multi-step flows | `langgraph` 1.2.24 | MIT | Steps with saved state, retries, a human-check step |
| Text embeddings | `Qwen/Qwen3-Embedding-0.6B` (GGUF version exists) | Apache-2.0 | Tiny, 32K input, 32-1024 dims, instruction-aware |
| Reranker | `Qwen/Qwen3-Reranker-0.6B` | Apache-2.0 | Re-sorts the top hits; big accuracy gain for little cost |
| Scans and pages (Desk) | `Qwen/Qwen3-VL-Embedding-2B` (+ `Qwen3-VL-Reranker-2B`) | Apache-2.0 | Embeds page images directly, up to 2048 dims |
| Store | `sqlite-vec` 0.1.9 + SQLite FTS5 | MIT/Apache | One file, no server, keyword + meaning search together |
| Store if it grows past ~1M chunks | `lancedb` 0.41 | Apache-2.0 | Embedded, hybrid search |
| Scoring | `ragas` 0.4.4 | Apache-2.0 | Faithfulness, answer relevance, context precision/recall |
Bigger embedders (Qwen3-Embedding-4B/8B) only if the 0.6B fails the gate: they cost RAM that the main model needs.

## How to use the Qwen3 embedder right
- Queries get an instruction, documents don't: `Instruct: <task in English>\nQuery:<question>`. The card says no instruction costs 1-5% accuracy.
- Write a task line per app, e.g. Mila: `Given a caller's question, find the shop facts that answer it`.
- Use 1024 dims to start. Try 512 in the tuning sweep (half the storage, often nearly the same).
- Serve with Ollama (`ollama create` from the GGUF) or sentence-transformers 6.3 on MPS. Measure which is faster on this Mac.

## Build steps
1. Collect sources into `<app>/rag/sources/` (copies only).
2. Chunk: start at 400 tokens with 50 overlap; headings stay with their text.
3. Embed into `<app>/rag/index-<date>.sqlite` (vec table + FTS5 table).
4. Query: hybrid search (FTS5 top 20 + vector top 20, merged with reciprocal rank fusion) -> reranker -> top 4 to the model.
5. The model must quote or cite the chunk it used. No chunk found = say "I'll check and get back to you" (Mila) or "Needs a check" (Desk). Never guess.

## RAG tuning (runs on its own, inside `p4k-labs-tune-loop`)
1. Make a test set once: 50-200 real questions with the right answer and the source chunk. Ragas can draft them from the documents (`TestsetGenerator`), a person or a strong model checks them.
2. Sweep, one change at a time: chunk size (200/400/800), overlap (0/50/100), dims (512/1024), hybrid on/off, rerank top-k (3/4/6), reranker on/off, instruction wording.
3. Score each with Ragas, judged by the local model (Qwen via Ollama), plus time per answer and RAM.
4. Keep the best. It must beat the current settings on faithfulness and context recall with no drop on others (no-drop rule).
5. Only if settings max out: fine-tune the embedder on our own question/chunk pairs with sentence-transformers (contrastive loss), on the Mac for 0.6B. Gate again.

## Floor (industry standard, checked by our runs)
- Faithfulness at least 0.90 (answers backed by the chunks).
- Context recall at least 0.85.
- Look-up plus rerank under 150 ms on the Mac for Mila (her total reply wait target is 1.12 s).

## Where it fits
- Mila: shop card and FAQ look-up when a card is too big for the prompt.
- The Desk app: the "Organise" step (search across 100+ pages, quoted evidence, unproven = "Needs a check").
- Personal: search the Obsidian vault. Never the user's Hermes chats.
