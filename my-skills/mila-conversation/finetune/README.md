# Teaching Qwen to talk like Mila

A starter kit. It teaches style (short spoken replies, local talk, read-backs,
no made-up prices), using only made-up calls. Nothing here uses real customer data.

All commands run on the Mac, inside the `~/MilaModels/.venv` environment.
The settings file was checked against mlx-lm 0.32.2, but **the training itself
has not been run yet**, so treat the first run as a test.

## 1. Make a Mac-ready copy of Qwen (once)
The download is the full-size model. This makes a smaller copy that fits in memory.
It adds a new folder and leaves the download untouched.

    mlx_lm.convert --hf-path ~/MilaModels/Qwen__Qwen3-8B --mlx-path ~/MilaModels/Qwen3-8B-mlx-4bit -q --q-bits 4

That needs about 5 GB of free disk. Check space first.

## 2. Make the starter calls

    python3 make_seed_data.py --out data --count 300

This writes `data/train.jsonl` and `data/valid.jsonl`. It refuses to write over
an existing folder, so use a new `--out` name each time.

## 3. Train

Point `model:` in `lora_config.yaml` at the folder from step 1, then:

    mlx_lm.lora --config lora_config.yaml

Close other apps first. If the Mac runs out of memory, lower `num_layers` to 4.

## 4. Try it

    mlx_lm.generate --model ~/MilaModels/Qwen3-8B-mlx-4bit --adapter-path adapters/run-01 \
      --system-prompt "You are Mila, the receptionist for Birch and Co Plumbing..." \
      --prompt "G'day, my hot water's carked it, reckon someone could come this arvo?"

Compare the same lines with and without `--adapter-path` before keeping a run.

## Good to know
- **Thinking mode:** Qwen 3 can "think out loud" before answering, which adds delay
  on a call. Turn it off for voice (see the Qwen model page for the current switch).
- **300 templated calls is a seed, not a finished set.** They repeat patterns. Before a
  serious run, have a stronger model write a few thousand varied calls in the same format,
  and check a sample by hand.
- **Real calls** go in only under the privacy rules in the `mila-brain` skill.
- **Never overwrite a run.** New `adapter_path` each time, and keep the old ones.
