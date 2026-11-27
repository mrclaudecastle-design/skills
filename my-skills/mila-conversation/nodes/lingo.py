#!/usr/bin/env python3
"""lingo: understand local everyday talk, and go along with it politely.

Mila never starts slang. She understands it, and if the caller is casual
she may answer with one light local phrase. Countries live in ../lingo/*.json
(Australia first, then Canada), so adding one is just adding a file.

    from lingo import understand, mirror
    u = understand("yeah nah the hot water's carked it, can ya come this arvo", "au")
    u["plain"]    -> "no the hot water's stopped working, can ya come this afternoon"
    u["signals"]  -> {"no", "broken", "time"}
"""
import json
import random
import re
from functools import lru_cache
from pathlib import Path

LINGO_DIR = Path(__file__).resolve().parent.parent / "lingo"


def _code(country) -> str:
    """A country code is two or three letters and nothing else, so it can never point at another file."""
    code = str(country or "au").strip().lower()
    return code if re.fullmatch(r"[a-z]{2,3}", code) else "au"


def load(country: str) -> dict:
    return _load(_code(country))


@lru_cache
def _load(country: str) -> dict:
    path = LINGO_DIR / f"{country}.json"
    try:
        data = json.loads(path.read_text())
        data["phrases"]
    except (OSError, ValueError, KeyError, TypeError):
        # No word list for this country yet: she understands plain English and mirrors nothing.
        return {"phrases": {}, "pattern": re.compile(r"(?!x)x"), "mirrors": {}}
    # Longest phrases first so "yeah nah yeah" wins over "yeah nah".
    phrases = sorted(data["phrases"].items(), key=lambda kv: -len(kv[0]))
    pattern = re.compile(r"(?<![\w'-])(" + "|".join(re.escape(p) for p, _ in phrases) + r")(?![\w'-])", re.I)
    return {"phrases": dict(phrases), "pattern": pattern, "mirrors": data.get("mirrors", {})}


def understand(text: str, country: str = "au") -> dict:
    """Return the caller's words in plain English, plus what they signalled."""
    lang = load(country)
    text = str(text or "")
    signals, matched = set(), []

    def swap(m):
        before = m.string[:m.start()].rstrip()
        if m.group(1)[:1].isupper() and before and before[-1] not in ".!?" and before.split()[-1][:1].isupper():
            return m.group(1)                      # a surname, not slang: "John Keen"
        entry = lang["phrases"][m.group(1).lower()]
        matched.append(m.group(1).lower())
        if entry.get("signal"):
            signals.add(entry["signal"])
        return entry["means"]

    plain = lang["pattern"].sub(swap, text)
    plain = re.sub(r"\s+([,.?!])", r"\1", re.sub(r"\s{2,}", " ", plain))
    plain = re.sub(r",+\s*([.?!])", r"\1", plain).strip(" ,")
    return {"plain": plain, "signals": signals, "matched": matched, "casual": bool(matched)}


def mirror(kind: str, country: str = "au", caller_was_casual: bool = False, rng=random) -> str | None:
    """A light local phrase Mila may say back. None unless the caller was casual first."""
    if not caller_was_casual:
        return None
    options = [v for v in load(country)["mirrors"].get(kind, []) if isinstance(v, str)]
    return rng.choice(options) if options else None


if __name__ == "__main__":
    for country, line in [("au", "Yeah nah the hot water's carked it, reckon you could come this arvo?"),
                          ("au", "Too easy, cheers mate."),
                          ("ca", "For sure, the furnace is on the fritz and the hydro's out, eh.")]:
        u = understand(line, country)
        print(f"[{country}] {line}\n   plain:   {u['plain']}\n   signals: {sorted(u['signals'])}")
