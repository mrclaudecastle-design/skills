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
  5. no made-up promises: a deadline ("within fifteen minutes") only on an
     urgent call and only if the card says so, and no "today" or "this arvo"
     for when the owner will call or come
  6. when she needs a day or time and can see the diary, she offers a free
     spot instead of asking "what time suits?"
  7. it sounds like speech: no lists, symbols or chatbot sign-offs, not too long

    from guard import guard
    out = guard("I'll pass your call to Dave.", caller="It's Bec, 0412 345 678", card=card)
    out.text   -> "So that's Bec on 0412 345 678. I'll pass your call to Dave."
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
SOON = re.compile(r"\b(?:later )?(?:today|tonight|tomorrow(?: (?:morning|arvo|afternoon))?|this (?:arvo|afternoon|morning|evening)|"
                  r"right now|right away|straight away|immediately)\b|\bnow(?=[.!?,]|$)", re.I)
DOING = re.compile(r"\b(?:will|'ll|can|going to|gonna)\b[^.!?]*\b(?:call|ring|phone|come|be there|be with you|be out|see you|fit you in|"
                   r"head over|get back|get out|pop (?:over|round)|sort)\b", re.I)
HEDGED = re.compile(r"\b(?:can't|cannot|can not|won't|not able|unable|no free|isn't|not sure|don't)\b", re.I)
ASK_WHEN = re.compile(r"\bwhat (?:day|time)\b[^.!?]*\?|\bwhen (?:would|works|suits|is good|are you)\b[^.!?]*\?|\bwhich day\b[^.!?]*\?", re.I)
FILLER = re.compile(r"^(?:let me know if you need (?:help with )?anything else[.!]|"
                    r"thanks for your patience[.!]|sound good\?|feel free to (?:call|reach out)[^.!?]*[.!])$", re.I)
NAME = re.compile(r"\b(?i:it's|its|it is|this is|my name is|my name's|name's|i'm|i am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
NOT_NAMES = {"Just", "Not", "After", "Looking", "Calling", "Flat", "Sorry", "At", "On", "About", "Good", "Fine", "Here", "Still", "Also"}
URGENT = re.compile(r"\b(?:urgent|emergency|flood(?:ing|ed)?|burst|pouring|gushing|no (?:water|power|heat(?:ing)?)|smell(?:s)? (?:of |like )?(?:gas|burning)|"
                    r"sparks?|sparking|on fire|smoke|sewage|overflow(?:ing)?|can't wait|asap)\b", re.I)
ACK = re.compile(r"^(?:thanks|thank you|got it|great|sure(?: thing)?|okay|ok|no problem|perfect|lovely|i've noted|i have noted|noted)\b", re.I)
MAX_SENTENCES = 3


def is_urgent(text: str) -> bool:
    """Does what the caller said sound like an emergency?"""
    return bool(URGENT.search(text))


def caller_name(text: str) -> str | None:
    m = NAME.search(text)
    return m.group(1) if m and m.group(1).split()[0] not in NOT_NAMES else None


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
          have_number: bool = False, urgent: bool | None = None) -> Guarded:
    """diary = free spots as (day, time) pairs, or None if she can't see it.
    have_number = True once the caller's number is known from earlier in the call.
    urgent = True if this call is an emergency (worked out from `caller` if left as None)."""
    fixes, text = [], reply.strip()
    a = card.a if card else {}
    owner = a.get("owner_name", "the owner")
    if urgent is None:
        urgent = is_urgent(caller)

    # 7a. Speech only: no list marks or symbols.
    clean = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", text)
    clean = re.sub(r"[*_#`]+", "", clean).replace("\n", " ").replace(" — ", ", ").replace("—", ", ")
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

    # 6. If she asks "what time suits?" while free spots are in front of her, offer one instead.
    if diary and not offered and ASK_WHEN.search(text):
        fixes.append("offer_spot")
        said_days = [d for d, _ in diary if d.lower() in caller.lower()]
        picks = [s for s in diary if s[0] in said_days][:1] or list(diary[:2])
        offer = (f"I have {picks[0][0]} at {picks[0][1]}. Would that suit?" if len(picks) == 1 else
                 f"The next free spots are {picks[0][0]} at {picks[0][1]} or {picks[1][0]} at {picks[1][1]}. Would either suit?")
        kept = [s for s in _sentences(text) if not s.endswith("?")][:1]
        text = " ".join(kept + [offer])

    # 5a. Deadlines: only on an urgent call, and only the one the card's urgent rule promises.
    promised = {m.group(0).lower() for m in DEADLINE.finditer(a.get("emergencies", ""))} if urgent else set()
    if any(m.group(0).lower() not in promised for m in DEADLINE.finditer(text)):
        fixes.append("deadline")
        text = DEADLINE.sub(lambda m: m.group(0) if m.group(0).lower() in promised else "as soon as possible", text)

    # 5b. No "today" or "this arvo" for when the owner will call or come: she can't know that.
    def soften(sentence: str) -> str:
        if SOON.search(sentence) and DOING.search(sentence) and not HEDGED.search(sentence) and not SLOT.search(sentence):
            return re.sub(r"\s{2,}", " ", SOON.sub("as soon as possible", sentence))
        return sentence
    softened = " ".join(soften(x) for x in _sentences(text))
    if not urgent and softened != " ".join(_sentences(text)):
        fixes.append("promise")
        text = softened

    # 7b. No chatbot sign-offs, and not too long for a phone call.
    parts = _sentences(text)
    real = [x for x in parts if not FILLER.match(x)]
    if real and len(real) < len(parts):
        fixes.append("sign_off")
        parts = real
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        fixes.append("too_long")
        # Drop empty acknowledgements first ("I've noted your details."), later ones before the opener.
        for i in sorted((i for i, x in enumerate(parts) if ACK.match(x) and len(x.split()) <= 5), key=lambda i: (i == 0, -i)):
            if len(parts) - 1 >= MAX_SENTENCES or len(parts) > MAX_SENTENCES:
                parts = parts[:i] + parts[i + 1:]
            if len(parts) <= MAX_SENTENCES:
                break
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        keep = parts[:MAX_SENTENCES - 1]
        last_question = next((x for x in reversed(parts) if x.endswith("?")), parts[MAX_SENTENCES - 1])
        text = " ".join(keep + ([last_question] if last_question not in keep else []))

    # 1. Read back a number the caller just gave, first, as a statement, so her own question still comes last.
    said = [m.group(0) for m in PHONE.finditer(caller)]
    if said:
        have_number = True
        if not any(_digits(n) in _digits(text) for n in said):
            fixes.append("read_back")
            name = caller_name(caller)
            text = (f"So that's {name} on {said[-1]}. " if name else f"So that's {said[-1]}. ") + text

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
