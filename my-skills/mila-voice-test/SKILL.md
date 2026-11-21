---
name: mila-voice-test
description: Compare Mila's voice and listening models (Phonon vs ZONOS3-Mini vs Kokoro, Moonshine vs Nemotron) for Australian accents, speed and naturalness, and help the owner pick. Use when asked to test, compare or choose Mila's voice or speech recognition.
---

# Mila voice test

Goal: pick the voice and the listening model that make Mila sound like a real Australian receptionist and answer fast enough to talk over naturally.

## House rules
- Never delete, move or overwrite anything. Save each test run in a new dated folder.
- The owner judges by ear. Give them clips to listen to and a short table, not technical detail.

## Before you start
Models must be downloaded first. Use the `mila-models` skill.

## Voice (text to speech)
1. Use the same 8 receptionist lines for every voice, for example:
   - "G'day, you've reached Birch and Co, this is Mila. How can I help?"
   - "No worries, I can book you in Thursday at 2. Does that work?"
   - "Sorry, could you say that again? The line cut out for a sec."
   - A long one with a name, address and phone number read back.
2. Make each line with ZONOS3-Mini, Phonon and Kokoro (and Qwen3-TTS if it's installed). Load each model the way its Hugging Face page shows.
3. For each clip, record: time to first sound, total time, and whether it sounds Australian.
4. Known numbers on an M1 Pro: Phonon about 20 ms and 16 calls at once; ZONOS3-Mini about 220 to 295 ms, 2 calls comfortable, 4 tight, 8 breaks. Check your results against these.
5. Put the clips on one page with a play button each and a "which sounds best?" choice, and share it with the owner.

## Listening (speech to text)
1. Use real Australian recordings: fast talkers, noisy job sites, names, street names, phone numbers. Only use recordings people agreed to share.
2. Run each through Moonshine streaming (CPU) and Nemotron streaming (GPU).
3. Record: words wrong per 100, delay before the words appear, and how it copes when someone talks over Mila.

## Scoring the listening test
Save what was really said and what each model heard in one file, then run
`python3 scripts/listening_score.py results.jsonl`. It prints, for each model, words wrong per 100, how often the important details (names, numbers, street names) came through intact, and the average delay. The file format is at the top of the script. Details kept matters more than overall word accuracy: a wrong street name costs a job, a missed "um" costs nothing.

## What to report
One short table per test with a clear pick, then one line on the next step. Save the full results in the run folder.
