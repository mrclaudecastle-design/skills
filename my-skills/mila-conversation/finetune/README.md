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

    python3 make_calls_v3.py --out data-v4 --count 1200

It refuses to write over an existing folder, so use a new `--out` name each time.
Two sets are already here: `data/` (the first 300, plain instructions) and `data-v2/`
(400 calls where every shop has its own questionnaire card, and Mila follows it for
days, prices, bookings and what the shop does). 
`data-v3/` (1,200 calls, from `make_calls_v3.py`) replaces both for training. The first
training run on `data-v2` copied the templates' wording (it kept asking "Can I get your
name?") and dropped read-backs and call-back offers. In v3 every line Mila says has many
wordings, the order she gathers details changes, each booking call lists the free diary
spots in her instructions, and three habits are in every call where they apply: a phone
number is always read back, when she doesn't know she offers a call back, and she never
asks for something the caller already gave. Train on `data-v3`.

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
- **A few hundred templated calls is a seed, not a finished set.** They repeat patterns. Before a
  serious run, have a stronger model write a few thousand varied calls in the same format,
  and check a sample by hand.
- **Real calls** go in only under the privacy rules in the `mila-brain` skill.
- **Never overwrite a run.** New `adapter_path` each time, and keep the old ones.

## What the first run taught us (run-01, 23 Nov 2026)
100 steps on `data-v2` took about 7 minutes on a 16 GB Mac, with no memory trouble, and
she replies at about 30 words a second. The loss fell very low very fast, which meant she
was memorising the templates. Judge a run by the five test lines before and after, not by
the loss. Keep the "before" answers: the untrained model already offers call backs and
reads numbers back, so a trained run must not lose those.

## What the second run taught us (run-02, 23 Nov 2026)
300 steps on `data-v3` took about 22 minutes. Replies were shorter and more natural, and she
kept to the diary's free spots, but she still skipped reading a caller's number back and once
promised a call back without taking details. The untrained model with the shop card and a
"Free spots in the diary" line answered as well or better. Decision: ship the untrained model
with the card, enforce must-do habits in `nodes/guard.py`, and fine-tune later only for tone,
on hand-written calls rather than templates. Results are on the SSD in `MilaModels/runs/`.
