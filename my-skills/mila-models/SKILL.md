---
name: mila-models
description: Download and set up Mila's own AI tools (Qwen brain, ZONOS3-Mini, Phonon and Kokoro voices, Moonshine and Nemotron listening) from Hugging Face and GitHub onto the Mac. Use when asked to get, install, update or list Mila's models or tools.
---

# Mila models: get your tools

Mila runs on free, open models. This skill downloads them from Hugging Face and installs the code libraries from GitHub, without touching anything already on the machine.

## House rules (always)
- **Never delete, move or overwrite anything.** Only add. If something is in the way, stop and ask.
- Keep messages to the owner short and in plain words.

## What gets downloaded
The full list, with licences, is in `models.json` next to this file:
- **brain:** Qwen 3 8B (about 16 GB; the owner may already have it, so ask before downloading).
- **voice_out:** ZONOS3-Mini (and its Mac version), Phonon, Kokoro.
- **ears:** Moonshine streaming (medium and small), NVIDIA Nemotron streaming.
- **GitHub libraries:** Pipecat (live calls), mlx-lm (Qwen on Mac), mlx-audio (voices on Mac), LangChain (shop info).

## Steps
1. Show the list: `python3 scripts/download_models.py --list`
2. Check where Qwen already lives on the Mac before getting it again. Search the usual places (`~/.cache/huggingface`, `~/.ollama`, `~/.lmstudio`) and reuse it if found.
3. Download, starting with the small voice and listening models:
   `python3 scripts/download_models.py --group voice_out ears --dest ~/MilaModels`
   Add `brain` only if Qwen isn't already there. If a download stalls, stop it with Ctrl+C and run the same command again: it picks up where it stopped. It checks there's enough free disk first.
4. Install the libraries in a separate Python environment so nothing else on the Mac changes:
   ```
   python3 -m venv ~/MilaModels/.venv && source ~/MilaModels/.venv/bin/activate
   pip install -U huggingface_hub pipecat-ai mlx-lm mlx-audio langchain
   ```
5. Before running a model, read its Hugging Face page for how to load it. These models are new, so check the page rather than guessing the code.
6. Tell the owner in one or two lines what was added and where.

## Watch out for
- The **Nemotron** licence isn't a standard open licence. Read it before using Mila with paying customers.
- The Phonon German, French and Spanish versions are non-commercial. Use only `phonon-31m-en`.
- A model page can change. If an id stops working, search Hugging Face for the name and update `models.json`.
