#!/usr/bin/env python3
"""guard: the safety net between Mila's brain and her voice.

The brain usually gets the manners right. This makes sure of the few
things that must be right every time, by checking each reply before it
is spoken and fixing it if needed:

  1. a phone number the caller just gave is read back
  2. no price is spoken unless it's on the shop's card
  3. no day or time is offered unless it's a free spot in the diary
     (and never on a day the shop doesn't work)
  4. a call back is never promised without a number to call
  5. no made-up deadlines ("within ten minutes") unless the card says so
  6. it sounds like speech: no lists or symbols, and not too long

    from guard import guard
    out = guard("I'll pass your call to Dave.", caller="It's Bec, 0412 345 678", card=card)
    out.text   -> "I'll pass your call to Dave. Just to check, that's 0412 345 678?"
    out.fixes  -> ["read_back"]
"""
import re
from dataclasses import dataclass, field

PHONE = re.compile(r"(?<!\d)(?:\(?0[2-478]\)?[ -]?\d{4}[ -]?\d{4}|04\d{2}[ -]?\d{3}[ -]?\d{3}|1[38]00[ -]?\d{3}[ -]?\d{3}|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})(?!\d)")
MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?|\b\d+ (?:dollars|bucks)\b", re.I)
DAY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
SLOT = re.compile(DAY + r"(?:,? (?:at|around|from))? (\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)", re.I)
DEADLINE = re.compile(r"\b(?:within|in) (?:the next )?(?:\d+|a|an|five|ten|fifteen|twenty|thirty|half an?) ?(?:minutes?|mins?|hours?|hour)\b", re.I)
CALLBACK = re.compile(r"\b(?:call|ring|phone|get back to) you\b|\bcall(?:s)? you back\b|\bcall back\b", re.I)
MAX_SENTENCES = 3


@dataclass
class Guarded:
    text: str
    fixes: list = field(default_factory=list)   # which rules had to step in


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _norm_time(t: str) -> str:
    t = t.lower().replace(".", "").replace(" ", "")
    return t if ":" in t else t[:-2] + ":00" + t[-2:]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text) if s.strip()]


def guard(reply: str, caller: str = "", card=None, diary: list[tuple[str, str]] | None = None,
          have_number: bool = False) -> Guarded:
    """diary = free spots as (day, time) pairs, or None if she can't see it.
    have_number = True once the caller's number is known from earlier in the call."""
    fixes, text = [], reply.strip()
    a = card.a if card else {}
    owner = a.get("owner_name", "the owner")

    # 6a. Speech only: no list marks or symbols.
    clean = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", text)
    clean = re.sub(r"[*_#`]+", "", clean).replace("\n", " ")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if clean != text:
        fixes.append("speech_only")
        text = clean

    # 2. Prices: only the ones on the card.
    allowed = {_digits(str(v)) for v in (a.get("prices") or {}).values()}
    if any(_digits(m) not in allowed for m in MONEY.findall(text)):
        fixes.append("price")
        text = (f"I don't want to guess a price and get it wrong. I can have {owner} call you back with a proper one. "
                "Would that help?")

    # 3. Days and times: only real free spots, only on working days.
    open_days = {d.lower() for d in a.get("open_days", [])}
    offered = [(d.lower(), _norm_time(t)) for d, t in SLOT.findall(text)]
    free = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}
    bad_slot = any((free is not None and s not in free) or (open_days and s[0] not in open_days) for s in offered)
    if offered and free is None:
        bad_slot = True          # she can't see the diary, so she can't offer a time
    if bad_slot:
        fixes.append("time")
        if diary:
            d, t = diary[0]
            text = f"The next free spot is {d} at {t}. Would that suit?"
        else:
            text = (f"I can't see the diary just now, so I won't guess a time. What day suits you best, "
                    f"and I'll have {owner} confirm it?")

    # 5. Deadlines: only if the card's urgent-call rule promises one.
    promised = {m.group(0).lower() for m in DEADLINE.finditer(a.get("emergencies", ""))}
    if any(m.group(0).lower() not in promised for m in DEADLINE.finditer(text)):
        fixes.append("deadline")
        text = DEADLINE.sub(lambda m: m.group(0) if m.group(0).lower() in promised else "as soon as possible", text)

    # 6b. Not too long for a phone call.
    parts = _sentences(text)
    if len(parts) > MAX_SENTENCES:
        fixes.append("too_long")
        keep = parts[:MAX_SENTENCES - 1]
        last_question = next((s for s in reversed(parts) if s.endswith("?")), parts[MAX_SENTENCES - 1])
        text = " ".join(keep + ([last_question] if last_question not in keep else []))

    # 1. Read back a number the caller just gave.
    said = [m.group(0) for m in PHONE.finditer(caller)]
    if said:
        have_number = True
        if not any(_digits(n) in _digits(text) for n in said):
            fixes.append("read_back")
            text = text.rstrip() + f" Just to check, that's {said[-1]}?"

    # 4. No call back promised without a number.
    # (Skipped when she is already asking something: one question at a time.)
    if CALLBACK.search(text) and not have_number and not text.rstrip().endswith("?") and not re.search(r"number", text, re.I):
        fixes.append("need_number")
        text = text.rstrip() + f" What's the best number for {owner} to call?"

    return Guarded(text, fixes)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from shop_card import ShopCard
    card = ShopCard.load(Path(__file__).resolve().parent.parent / "shop" / "examples" / "birch-and-co.json")
    diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]
    for caller, reply in [
        ("Can you get Dave to call me back? It's Bec, 0412 345 678.", "I'll pass your call to Dave."),
        ("There's water pouring through my ceiling!", "That's an emergency. I'll get Dave to call you back now."),
        ("How much for a leaking tap?", "It's usually about $150 for a tap."),
        ("Can someone come this week?", "Sure, I can do Wednesday at 10am."),
        ("What's the call-out fee?", "The call-out fee is $90."),
    ]:
        out = guard(reply, caller, card, diary)
        print(f"caller: {caller}\n brain: {reply}\n spoken: {out.text}   {out.fixes or ''}\n")
