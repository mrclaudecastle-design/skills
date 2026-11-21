# My skills

Our own skills library, kept next to Anthropic's (in `skills/`). Nothing in Anthropic's folder was changed or removed.

| Skill | What it does |
|---|---|
| `mila-models` | Downloads Mila's tools from Hugging Face and GitHub onto the Mac, adding only and never deleting |
| `mila-voice-test` | Compares voices and listening models for Australian accents and speed, and helps pick one |
| `mila-brain` | Runs, teaches and improves Mila's brain (Qwen 3 8B), with the privacy rules for training |
| `mila-conversation` | Small building blocks for natural calls: spoken numbers, Australian and Canadian talk, voting on what was meant, the "press 1" fallback, timing, and a Qwen training starter kit |
| `owner-plain-words` | House rules for anything an owner or customer reads |

## Install in Claude Code
```
/plugin marketplace add mrclaudecastle-design/skills
/plugin install my-skills@anthropic-agent-skills
```

House rule for every skill here: never delete anything.
