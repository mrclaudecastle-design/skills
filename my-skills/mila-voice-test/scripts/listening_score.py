#!/usr/bin/env python3
"""Score how well each set of ears heard the same recordings.

You give it what was really said and what each model heard. It reports,
per model: words wrong per 100, how often the important details (names,
numbers, street names) came through intact, and the average delay.

Input is a JSON Lines file, one recording per line:
  {"clip": "call-01", "said": "It's Bec at 22 Old Coach Road, 0412 345 678",
   "details": ["Bec", "22 Old Coach Road", "0412 345 678"],
   "heard": {"moonshine": {"text": "it's beck at 22 old coach road ...", "delay_ms": 180},
             "nemotron":  {"text": "...", "delay_ms": 140}}}

    python3 listening_score.py results.jsonl
"""
import json
import re
import sys
from collections import defaultdict

NUMBER_WORDS = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                "six": "6", "seven": "7", "eight": "8", "nine": "9"}


def words(text: str) -> list[str]:
    """Lower-case words, with numbers split into single digits so
    '0412' and 'oh four one two' count as the same thing."""
    out = []
    for w in re.findall(r"[a-z']+|\d+", text.lower().replace("’", "'")):
        if w.isdigit():
            out.extend(w)
        else:
            out.append(NUMBER_WORDS.get(w, w.replace("'", "")))
    return [w for w in out if w]


def errors(said: list[str], heard: list[str]) -> int:
    """Fewest word changes to turn what was heard into what was said."""
    prev = list(range(len(heard) + 1))
    for i, s in enumerate(said, 1):
        row = [i]
        for j, h in enumerate(heard, 1):
            row.append(min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (s != h)))
        prev = row
    return prev[-1]


def detail_kept(detail: str, heard: list[str]) -> bool:
    d = words(detail)
    return any(heard[i:i + len(d)] == d for i in range(len(heard) - len(d) + 1)) if d else True


def score(rows: list[dict]) -> dict:
    t = defaultdict(lambda: {"words": 0, "errors": 0, "details": 0, "kept": 0, "delays": [], "clips": 0})
    for row in rows:
        said = words(row["said"])
        for model, result in row["heard"].items():
            heard = words(result.get("text", ""))
            m = t[model]
            m["clips"] += 1
            m["words"] += len(said)
            m["errors"] += errors(said, heard)
            for d in row.get("details", []):
                m["details"] += 1
                m["kept"] += detail_kept(d, heard)
            if result.get("delay_ms") is not None:
                m["delays"].append(result["delay_ms"])
    return {model: {"clips": m["clips"],
                    "wrong_per_100": round(100 * m["errors"] / m["words"], 1) if m["words"] else None,
                    "details_kept_pct": round(100 * m["kept"] / m["details"]) if m["details"] else None,
                    "avg_delay_ms": round(sum(m["delays"]) / len(m["delays"])) if m["delays"] else None}
            for model, m in t.items()}


def table(scores: dict) -> str:
    lines = [f"{'ears':16}{'clips':>6}{'words wrong /100':>18}{'details kept':>14}{'delay':>9}"]
    best = sorted(scores, key=lambda k: (-(scores[k]["details_kept_pct"] or 0), scores[k]["wrong_per_100"] or 999))
    for model in best:
        s = scores[model]
        kept = "-" if s["details_kept_pct"] is None else f"{s['details_kept_pct']}%"
        delay = "-" if s["avg_delay_ms"] is None else f"{s['avg_delay_ms']} ms"
        lines.append(f"{model:16}{s['clips']:>6}{s['wrong_per_100']:>18}{kept:>14}{delay:>9}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
    print(table(score(rows)))
