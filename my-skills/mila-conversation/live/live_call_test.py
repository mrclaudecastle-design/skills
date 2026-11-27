#!/usr/bin/env python3
"""Live check: the real brain, a shop's card, scripted callers, and the safety net.

Loads the model once, plays a set of scripted calls against it, and for every
reply records what the brain said, what Mila would actually say after the
guard, which rules stepped in, and how long the brain took. Read-only apart
from the two result files it writes into --out (a new folder).

    python live_call_test.py --model /Volumes/02-WORK/MilaModels/Qwen3-8B-mlx-4bit \\
        --out /Volumes/02-WORK/MilaModels/runs/live-01 [--adapter-path ...]
"""
import argparse
import copy
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "nodes"))
from guard import PHONE, guard, is_urgent   # noqa: E402
from lingo import understand            # noqa: E402
from shop_card import ShopCard          # noqa: E402

DIARY = [("Tuesday", "9:30am"), ("Thursday", "2:00pm"), ("Friday", "11:00am")]
CALLS = {   # name -> what the caller says, turn by turn
    "booking, casual": ["G'day, my hot water's carked it, reckon someone could come this arvo?", "Yeah nah, Tuesday's no good, I'm flat out.",
                        "Nah yeah, Thursday works.", "It's Shane, 14 Banksia Crescent.", "0412 345 678."],
    "booking, formal": ["Hello, I have a blocked drain. Could someone come out this week?", "Yes, Friday is fine.",
                        "My name is Linda Park and the number is 0498 111 222."],
    "call back in one breath": ["Can you get Dave to call me back? It's Bec, 0412 345 678.", "Just tell him it's about the quote."],
    "price, not on card": ["How much do you reckon it'd be to fix a leaking tap?", "Yeah alright, get him to call me.", "0433 987 654."],
    "price, on card": ["Is there a call-out fee?", "And what would the whole job cost, roughly?"],
    "not offered": ["Do you guys do roofing as well?", "What about gas fitting?"],
    "unknown service": ["Do you do gutter cleaning?", "Yeah, get Dave to ring me. It's Tom on 0455 222 333."],
    "closed day": ["Any chance someone could come out Sunday?", "Righto, what have you got then?"],
    "urgent": ["There's water pouring through my ceiling!", "22 Old Coach Road.", "0411 000 999."],
    "wants a time that isn't free": ["Can I book Wednesday at 10am?", "Okay, Thursday then."],
    "pushy on price": ["Just give me a ballpark, mate, fifty bucks? A hundred?", "Come on, you must have some idea."],
    "off topic": ["Can you recommend a good electrician?", "No worries. Bye."],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter-path", default=None)
    ap.add_argument("--card", default=str(ROOT / "shop" / "examples" / "birch-and-co.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--no-cache", action="store_true", help="re-read the shop card on every reply (the old, slower way)")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already has files. Pick a new --out folder so nothing is overwritten.")
    out.mkdir(parents=True, exist_ok=True)

    from mlx_lm import load, stream_generate
    card = ShopCard.load(args.card)
    system = card.instructions() + "\n- Free spots in the diary: " + "; ".join(f"{d} {t}" for d, t in DIARY) + ". Offer only these."
    t0 = time.perf_counter()
    model, tokenizer = load(args.model, adapter_path=args.adapter_path)
    load_s = time.perf_counter() - t0

    def render(messages):
        try:
            out = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            out = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
        return list(out["input_ids"] if hasattr(out, "keys") else out)

    # Read the shop card once and keep it, so each reply only has to read the call so far.
    warm, prefix, cache_note = None, [], "off"
    if not args.no_cache:
        try:
            import mlx.core as mx
            from mlx_lm.models.cache import make_prompt_cache
            a = render([{"role": "system", "content": system}, {"role": "user", "content": "Hello"}])
            b = render([{"role": "system", "content": system}, {"role": "user", "content": "What time is it?"}])
            same = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            prefix = a[:same]
            warm = make_prompt_cache(model)
            model(mx.array(prefix)[None], cache=warm)
            mx.eval([c.state for c in warm])
            cache_note = f"on ({len(prefix)} of the card's tokens read once)"
        except Exception as e:                      # any trouble: carry on the old way and say so
            warm, prefix, cache_note = None, [], f"off (could not set up: {e})"

    results, fixes, lines = [], Counter(), [f"Model: {args.model}  adapter: {args.adapter_path}  load: {load_s:.1f}s  card kept ready: {cache_note}", "", system, ""]
    for name, caller_lines in CALLS.items():
        messages, have_number, urgent = [{"role": "system", "content": system}], False, False
        heard_so_far, last_reply = "", ""
        lines.append(f"=== {name} ===")
        for said in caller_lines:
            messages.append({"role": "user", "content": said})
            tokens = render(messages)
            t = time.perf_counter()
            cache, send = None, tokens
            if warm is not None and tokens[:len(prefix)] == prefix:
                cache, send = copy.deepcopy(warm), tokens[len(prefix):]   # the card is already read: only the call so far is new
            brain, first = "", None
            for part in stream_generate(model, tokenizer, send, max_tokens=args.max_tokens, **({"prompt_cache": cache} if cache else {})):
                brain += part.text
                if first is None and re.search(r"[.!?](?:\s|$)", brain):
                    first = time.perf_counter() - t                  # when the voice could start speaking
            secs = time.perf_counter() - t
            first = secs if first is None else first
            brain = brain.strip()
            if "</think>" in brain:                      # in case thinking could not be switched off
                brain = brain.split("</think>")[-1].strip()
            urgent = urgent or is_urgent(said)
            g = guard(brain, said, card, DIARY, have_number, urgent, heard_so_far, last_reply)
            heard_so_far, last_reply = heard_so_far + " " + said, g.text
            have_number = have_number or bool(PHONE.search(said))
            fixes.update(g.fixes)
            messages.append({"role": "assistant", "content": g.text})   # the call continues with what she really said
            results.append({"call": name, "caller": said, "caller_plain": understand(said, card.country)["plain"],
                            "brain": brain, "spoken": g.text, "fixes": g.fixes, "seconds": round(secs, 2), "first_sentence_seconds": round(first, 2)})
            lines += [f"caller: {said}", f" brain: {brain}"] + ([f"spoken: {g.text}   {g.fixes}"] if g.fixes else []) + [f"        ({secs:.1f}s, first sentence {first:.1f}s)"]
        lines.append("")

    n = len(results)
    touched = sum(1 for r in results if r["fixes"])
    times = sorted(r["seconds"] for r in results)
    firsts = sorted(r["first_sentence_seconds"] for r in results)
    summary = {"replies": n, "left_alone": n - touched, "fixed_by_guard": touched, "fixes_by_rule": dict(fixes),
               "card_kept_ready": cache_note, "median_first_sentence_seconds": firsts[n // 2],
               "slowest_first_sentence_seconds": firsts[-1], "median_seconds": times[n // 2], "slowest_seconds": times[-1], "load_seconds": round(load_s, 1)}
    lines += ["=== summary ===", json.dumps(summary, indent=2)]
    (out / "live-calls.txt").write_text("\n".join(lines) + "\n")
    (out / "live-calls.json").write_text(json.dumps({"summary": summary, "system": system, "results": results}, indent=2, ensure_ascii=False) + "\n")
    print("\n".join(lines[-12:]))
    print(f"\nFull transcript: {out / 'live-calls.txt'}")


if __name__ == "__main__":
    main()
