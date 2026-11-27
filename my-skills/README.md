# My skills

Our own skills library, kept next to Anthropic's (in `skills/`). Nothing in Anthropic's folder was changed or removed.

| Skill | What it does |
|---|---|
| `mila-models` | Downloads Mila's tools from Hugging Face and GitHub onto the Mac, adding only and never deleting |
| `mila-voice-test` | Compares voices and listening models for Australian accents and speed, and helps pick one |
| `mila-brain` | Runs, teaches and improves Mila's brain (Qwen 3 8B), with the privacy rules for training |
| `mila-conversation` | Small building blocks for natural calls: spoken numbers, Australian and Canadian talk, voting on what was meant, the "press 1" fallback, timing, and a Qwen training starter kit |
| `mila-image-local` | Makes photo-real or stylised character pictures with local, open-source image models (ComfyUI + Z-Image-Turbo on a Mac, SSD-1B on CPU), with the lessons learned |
| `quiet-mac-gate` | Runs timed jobs only when the Mac is quiet, watches for other jobs during each one, and marks every result valid or not valid |
| `call-replay-check` | Replays saved calls through Mila's safety net with no model, switches each part off in turn, and reports what changed |
| `voice-line-check` | Scores a voice on 72 call lines and 35 hard lines, with a hearing model as the judge |
| `safe-mac-work` | House rules for working on the owner's Mac and drive: add only, never delete, report anything refused |
| `p4k-labs-tune-loop` | P4K Labs' hands-off loop: find, test, tune, gate and freeze local AI models with the no-drop rule |
| `model-qwen3-5` | How to run, set up and tune Qwen3.5 (9B, 4B) and its DeepSeek and Qwen3.8 distills on a 16 GB Mac |
| `model-qwen3-8b` | Settings, file locations and lessons for Qwen3-8B, the model in use today |
| `heretic-model-edit` | Make our own abliterated or less-sloppy model copy with Heretic on a rented GPU (personal use only) |
| `local-rag` | Local look-up-then-answer (LangChain, Qwen3 embedding and reranker, SQLite) and how to auto-tune it with Ragas |
| `owner-plain-words` | House rules for anything an owner or customer reads |

## Install in Claude Code
```
/plugin marketplace add mrclaudecastle-design/skills
/plugin install my-skills@anthropic-agent-skills
```

House rule for every skill here: never delete anything.
