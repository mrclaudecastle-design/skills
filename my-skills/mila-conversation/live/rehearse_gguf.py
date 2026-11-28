#!/usr/bin/env python3
"""Rehearsal: the same 12 scripted calls as live_call_test.py, on a GGUF copy of the brain.

Use it to try a fix on any computer without Apple's MLX (a cloud box, a rented
GPU, a Linux PC) before the real round on the Mac. Same calls, same diary,
same card, same safety net, greedy decoding. Timings here do NOT count toward
the pass mark: only the Mac round does. Writes into a new --out folder only.

    pip install llama-cpp-python
    python rehearse_gguf.py --model Qwen3-8B-Q4_K_M.gguf --out runs/rehearsal-01
"""
import os
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "nodes"))
sys.path.insert(0, str(HERE))
from guard import PHONE, guard, is_urgent   # noqa: E402
from lingo import understand                # noqa: E402
from shop_card import ShopCard              # noqa: E402
from live_call_test import CALLS, DIARY     # noqa: E402  (one list of calls for both)
from more_calls import MORE_CALLS           # noqa: E402


def chatml(messages) -> str:
    """Qwen3's own chat layout with thinking switched off, as apply_chat_template(enable_thinking=False) gives."""
    text = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
    return text + "<|im_start|>assistant\n<think>\n\n</think>\n\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--card", default=str(ROOT / "shop" / "examples" / "birch-and-co.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--threads", type=int, default=os.cpu_count())
    ap.add_argument("--only", default="", help="comma-separated call names to play (default: all 12)")
    ap.add_argument("--set", choices=["main", "more"], default="main", help="main = the 12 scored calls; more = 12 unseen ones")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already has files. Pick a new --out folder so nothing is overwritten.")
    out.mkdir(parents=True, exist_ok=True)

    from llama_cpp import Llama
    card = ShopCard.load(args.card)
    system = card.instructions() + "\n- Free spots in the diary: " + "; ".join(f"{d} {t}" for d, t in DIARY) + ". Offer only these."
    t0 = time.perf_counter()
    llm = Llama(model_path=args.model, n_ctx=4096, n_threads=args.threads, verbose=False, seed=0)
    load_s = time.perf_counter() - t0
    calls = {k: v for k, v in (CALLS if args.set == "main" else MORE_CALLS).items() if not args.only or k in args.only.split(",")}

    results, fixes, lines = [], Counter(), [f"Model: {args.model}  load: {load_s:.1f}s  (rehearsal, timings don't count)", "", system, ""]
    for name, caller_lines in calls.items():
        messages, have_number, urgent = [{"role": "system", "content": system}], False, False
        heard_so_far, last_reply = "", ""
        lines.append(f"=== {name} ===")
        for said in caller_lines:
            messages.append({"role": "user", "content": said})
            t = time.perf_counter()
            brain = ""
            for part in llm(chatml(messages), max_tokens=args.max_tokens, temperature=0.0, top_k=1, stream=True,
                            stop=["<|im_end|>", "<|im_start|>"]):
                brain += part["choices"][0]["text"]
            secs = time.perf_counter() - t
            brain = brain.strip()
            if "</think>" in brain:
                brain = brain.split("</think>")[-1].strip()
            urgent = urgent or is_urgent(said)
            g = guard(brain, said, card, DIARY, have_number, urgent, heard_so_far, last_reply)
            heard_so_far, last_reply = heard_so_far + " " + said, g.text
            have_number = have_number or bool(PHONE.search(said))
            fixes.update(g.fixes)
            messages.append({"role": "assistant", "content": g.text})
            results.append({"call": name, "caller": said, "caller_plain": understand(said, card.country)["plain"],
                            "brain": brain, "spoken": g.text, "fixes": g.fixes, "seconds": round(secs, 2)})
            lines += [f"caller: {said}", f" brain: {brain}"] + ([f"spoken: {g.text}   {g.fixes}"] if g.fixes else []) + [f"        ({secs:.1f}s)"]
            print(lines[-3:], flush=True)
        lines.append("")

    n = len(results)
    touched = sum(1 for r in results if r["fixes"])
    summary = {"replies": n, "left_alone": n - touched, "fixed_by_guard": touched, "fixes_by_rule": dict(fixes),
               "note": "rehearsal on GGUF; timings don't count", "load_seconds": round(load_s, 1)}
    lines += ["=== summary ===", json.dumps(summary, indent=2)]
    (out / "live-calls.txt").write_text("\n".join(lines) + "\n")
    (out / "live-calls.json").write_text(json.dumps({"summary": summary, "system": system, "results": results}, indent=2, ensure_ascii=False) + "\n")
    print(f"\nFull transcript: {out / 'live-calls.txt'}")


if __name__ == "__main__":
    main()
