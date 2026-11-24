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
  8. she never says the same thing twice in a row
  9. she never reads back a detail the caller hasn't given (such as a made-up address)

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
FILLER = re.compile(r"^(?:have a (?:great|good|lovely|nice|wonderful) (?:day|one|arvo|afternoon|evening|night|weekend)[.!]|"
                    r"thanks for (?:confirming|the details|that|calling)[.!]|let me know if you need (?:help with )?anything else[.!]|"
                    r"thanks for your patience[.!]|sound good\?|feel free to (?:call|reach out)[^.!?]*[.!])$", re.I)
NAME = re.compile(r"\b(?i:it's|its|it is|this is|my name is|my name's|name's|i'm|i am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
NOT_NAMES = {"Just", "Not", "After", "Looking", "Calling", "Flat", "Sorry", "At", "On", "About", "Good", "Fine", "Here", "Still", "Also"}
URGENT = re.compile(r"\b(?:urgent|emergency|flood(?:ing|ed)?|burst|pouring|gushing|no (?:water|power|heat(?:ing)?)|smell(?:s)? (?:of |like )?(?:gas|burning)|"
                    r"sparks?|sparking|on fire|smoke|sewage|overflow(?:ing)?|can't wait|asap)\b", re.I)
ACK = re.compile(r"^(?:thanks|thank you|got it|great|sure(?: thing)?|okay|ok|no problem|perfect|lovely|i've noted|i have noted|noted)\b", re.I)
ADDRESS = re.compile(r"\b(?:(?:unit|flat|apartment) \d+[a-z]?,? ?)?\d{1,4}[a-z]?(?:/\d{1,4})? (?:[A-Z][\w']+ ){1,3}"
                     r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Highway|Hwy|Parade|Pde|Terrace|Tce|Lane|Ln|Boulevard|Blvd|Close|Way)\b")
ANYTHING_ELSE = re.compile(r"^is there anything else (?:i can (?:assist|help)(?: you)?(?: with)?|you need)[^?]*\?$", re.I)
FLUFF = re.compile(r"^(?:that(?:'s| is| slot's| slot is) (?:a |still )?free(?: spot)?(?: in the diary)?[.!]|that's available[.!])$", re.I)
NOTED = re.compile(r"^i(?:'ve| have) (?:noted|got|taken|recorded)\b[^?]*$", re.I)
VAGUE_SOON = re.compile(r"\b(?:shortly|in no time|(?<!as )soon(?! as))\b", re.I)
OFFICE = re.compile(r"\b(?:as soon as|once|when) (?:he|she|they)(?:'s|'re| is| are| gets?) back (?:in|at|to) the office\b", re.I)
MATE = re.compile(r",? mate\b", re.I)
CLOCK = re.compile(r"\b\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?(?![a-z])", re.I)
SLOT_OR_TIME = re.compile(DAY + r"|(\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)(?![a-z])", re.I)
MAX_SENTENCES = 3

_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine".split())}
_UNITS.update({"oh": 0, "o": 0, "nought": 0})
_TEENS = {w: 10 + i for i, w in enumerate("ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}


def spoken_numbers(text: str) -> str:
    """Turn numbers said in words into digits, so 'forty seven Ocean Street' and
    'oh four one two, three four five...' can be checked like written ones."""
    words = re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]+|\s+", text)
    out, run, repeat, i = [], [], 1, 0
    unit = [False]          # was the last piece a single digit word (digit-by-digit reading)?

    def flush():
        if run:
            out.append("".join(run))
            run.clear()
    while i < len(words):
        w, lw = words[i], words[i].lower()
        if lw in ("double", "triple"):
            repeat = 2 if lw == "double" else 3
        elif lw in _TENS:
            n = _TENS[lw]
            j = i + 1
            if j + 1 < len(words) and words[j].isspace() or (j < len(words) and words[j] == "-"):
                k = j + 1
                if k < len(words) and words[k].lower() in _UNITS and words[k].lower() not in ("oh", "o", "zero", "nought"):
                    n += _UNITS[words[k].lower()]
                    i = k
            run.append(str(n) * repeat); repeat = 1; unit[0] = False
        elif lw in _TEENS:
            run.append(str(_TEENS[lw]) * repeat); repeat = 1; unit[0] = False
        elif lw in _UNITS and not (lw == "o" and run == []):
            run.append(str(_UNITS[lw]) * repeat); repeat = 1; unit[0] = True
        elif w.isdigit():                 # written digits stay exactly as written
            flush(); out.append(w)
        elif (w.isspace() or w in (",", "-")) and run:
            k = i + 1
            while k < len(words) and (words[k].isspace() or words[k] in (",", "-")):
                k += 1
            nxt = words[k].lower() if k < len(words) else ""
            # "oh four one two, three four five" is one number; "unit three, forty seven" is two.
            if not (unit[0] and (nxt in _UNITS or nxt in ("double", "triple"))):
                flush(); out.extend(words[i:k])       # keep the gap exactly as said
            i = k - 1
        else:
            flush(); out.append(w)
        i += 1
    flush()
    return "".join(out)


HOURS_TALK = re.compile(r"\b(?:open|opening|hours|closed?|closes|shut)\b", re.I)
_T = r"\d{1,2}(?::\d{2})?(?:\s?[ap]\.?m\.?)?"
TIME_RANGE = re.compile(_T + r"\s*(?:to|till|until|-|–)\s*" + _T + r"(?![\w:])", re.I)
HOURS_PHRASE = re.compile(r"\b(?:open(?:s|ing)?|close[sd]?|shut|until|till|from|start(?:s)?|finish(?:es)?)\s+(?:at\s+|around\s+)?" + _T + r"(?![\w:])", re.I)
RELATIVE = re.compile(r"\b(today|tonight|this (?:arvo|afternoon|morning|evening)|tomorrow)\b", re.I)
WEEK = "monday tuesday wednesday thursday friday saturday sunday".split()


def _hours_or_offer(m) -> str:
    """'open 7am to 4pm' is hours talk and is dropped; 'Wednesday 10am to 11am' or
    'Wednesday from 10am' is an offer, so its first time is kept."""
    before = m.string[:m.start()]
    next_to_day = re.search(DAY + r"\s*,?\s*(?:at\s+)?$", before, re.I)
    day_span = re.search(DAY + r"\s+(?:to|till|through|-|–)\s+" + DAY + r"\s*,?\s*$", before, re.I)
    if next_to_day and not day_span:
        return " at " + re.search(_T, m.group(0)).group(0)
    return " "


def offered_slots(text: str, context_day: str = "", today: str | None = None) -> list[tuple[str, str]]:
    """Every (day, time) offered, in either order: 'Tuesday at 9:30am', '10am on Tuesday',
    'Tuesday at 9 or 11am', 'tomorrow at 2pm' (needs `today`, a weekday name).
    A time with no day comes back with context_day (a day said earlier), or '' if none.
    'today'/'tomorrow' with no `today` given comes back as '?', which can't be checked.
    Talk about opening hours ('open 7am to 5pm') is not an offer."""
    found = []
    for sentence in _sentences(text):
        sentence = HOURS_PHRASE.sub(_hours_or_offer, TIME_RANGE.sub(_hours_or_offer, sentence))
        hits = list(SLOT_OR_TIME.finditer(sentence))
        rel = RELATIVE.search(sentence)
        if rel and not any(h.group(1) for h in hits):
            word = rel.group(1).lower()
            if today and today.lower() in WEEK:
                n = WEEK.index(today.lower()) + (1 if word == "tomorrow" else 0)
                context_day = WEEK[n % 7]
            else:
                context_day = "?"
        last_day = context_day
        for n, m in enumerate(hits):
            if m.group(1):
                last_day = context_day = m.group(1)
                continue
            nxt = hits[n + 1] if n + 1 < len(hits) else None
            gap = sentence[m.end():nxt.start()] if nxt else ""
            if nxt and nxt.group(1) and re.fullmatch(r"\s*(?:on|this|next|,)?\s*(?:this |next )?", gap, re.I):
                found.append((nxt.group(1), m.group(2)))
            else:
                found.append((last_day, m.group(2)))
    return found


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
          have_number: bool = False, urgent: bool | None = None, heard_so_far: str = "", last_reply: str = "",
          today: str | None = None) -> Guarded:
    """diary = free spots as (day, time) pairs, or None if she can't see it.
    have_number = True once the caller's number is known from earlier in the call.
    urgent = True if this call is an emergency (worked out from `caller` if left as None).
    heard_so_far = everything the caller has said earlier in this call.
    last_reply = what Mila said on her previous turn.
    today = today's weekday name, so "tomorrow at 2pm" can be checked against the diary."""
    fixes, text = [], reply.strip()
    a = card.a if card else {}
    owner = a.get("owner_name", "the owner")
    if urgent is None:
        urgent = is_urgent(caller)

    text = text.replace("\u2019", "'").replace("\u2018", "'")
    caller = spoken_numbers(caller.replace("\u2019", "'").replace("\u2018", "'"))
    heard_so_far = spoken_numbers(heard_so_far.replace("\u2019", "'"))
    everything_heard = (heard_so_far + " " + caller).lower()

    # 8. Never the same sentence twice in a row.
    # Reading back a detail the caller has just said again (a correction) is not a repeat.
    is_read_back = bool(set(re.findall(r"\d+", text)) & set(re.findall(r"\d+", caller)))
    if last_reply and not is_read_back and re.sub(r"\W+", " ", text).strip().lower() == re.sub(r"\W+", " ", last_reply).strip().lower():
        fixes.append("repeat")
        text = "Thanks, I've got that."

    # 7a. Speech only: no list marks or symbols.
    clean = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", text)
    clean = re.sub(r"[*_#`]+", "", clean).replace("\n", " ").replace(" — ", ", ").replace("—", ", ")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if clean != text:
        fixes.append("speech_only")
        text = clean

    # 9. Never read back a detail the caller hasn't given. An address she made up becomes a question.
    made_up = [m.group(0) for m in ADDRESS.finditer(text)
               if not re.search(r"(?<![\w/])" + re.escape(m.group(0).lower()), everything_heard)]
    if made_up:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(a_ in x for a_ in made_up) and not x.endswith("?")]
        text = " ".join(kept + ["What's the address for the job?"])

    # 2. Prices: only the ones on the card.
    allowed = {_digits(str(v)) for v in (a.get("prices") or {}).values()}
    if any(_digits(m) not in allowed for m in MONEY.findall(text)):
        fixes.append("price")
        text = (f"I don't want to guess a price and get it wrong. I can have {owner} call you back with a proper one. "
                "Would that help?")

    # 3. Days and times: only real free spots, only on working days.
    open_days = {d.lower() for d in a.get("open_days", [])}
    # A time with no day takes its day from the call: what the caller just said, then her last reply, then earlier.
    caller_days = [m.group(1).lower() for m in re.finditer(DAY, caller, re.I)]
    recent_days = caller_days[-1:] if caller_days else [   # the day the caller last named wins outright
        m.group(1).lower() for src in (last_reply, heard_so_far) for m in reversed(list(re.finditer(DAY, src, re.I)))]
    free_now = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}

    def which_day(t):
        for d in recent_days:                      # prefer a recent day where that time is actually free
            if free_now is None or (d, t) in free_now:
                return d
        return recent_days[0] if recent_days else ""
    offered = [(d.lower() or which_day(_norm_time(t)), _norm_time(t)) for d, t in offered_slots(text, "", today)]
    free = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}
    def slot_ok(s):
        day, t = s
        if not day or day == "?":       # no day she or the caller named, or "tomorrow" without a date: can't check it
            return free is None and not open_days
        return (free is None or s in free) and (not open_days or day in open_days)
    bad_slot = any(not slot_ok(s) for s in offered)
    if offered and free is None:
        bad_slot = True          # she can't see the diary, so she can't offer a time
    if bad_slot:
        fixes.append("time")
        if diary:
            d, t = diary[0]
            asked = SLOT.search(caller)     # tell the caller why, if they asked for a spot that isn't free
            why = f"Sorry, {asked.group(1).capitalize()} at {asked.group(2)} isn't free. " if asked else ""
            text = f"{why}The next free spot is {d} at {t}. Would that suit?"
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
        if SOON.search(sentence) and DOING.search(sentence) and not HEDGED.search(sentence) and not SLOT.search(sentence) and not CLOCK.search(sentence):
            return re.sub(r"\s{2,}", " ", SOON.sub("as soon as possible", sentence))
        return sentence
    softened = " ".join(soften(x) for x in _sentences(text))
    if not urgent and softened != " ".join(_sentences(text)):
        fixes.append("promise")
        text = softened

    # 5c. "He'll be with you shortly" is a promise too, and there is no office to be back in.
    if not urgent:
        kept = _sentences(text)
        if SLOT.search(text):     # a visit is booked for a set time, so "shortly" contradicts it
            kept = [x for x in kept if SLOT.search(x) or not (VAGUE_SOON.search(x) and DOING.search(x) and not HEDGED.search(x))]
        fixed = OFFICE.sub("as soon as possible", " ".join(kept))
        if fixed != " ".join(_sentences(text)):
            if "promise" not in fixes:
                fixes.append("promise")
            text = fixed

    # 10. She goes along with slang, she doesn't start it.
    if MATE.search(text) and "mate" not in everything_heard:
        fixes.append("slang")
        text = MATE.sub("", text)

    # 7b. No chatbot sign-offs, and not too long for a phone call.
    parts = _sentences(text)
    real = [x for x in parts if not FILLER.match(x) and not (ANYTHING_ELSE.match(x) and not (have_number or PHONE.search(caller)))]
    if real and len(real) < len(parts):
        fixes.append("sign_off")
        parts = real
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        fixes.append("too_long")
        # Drop padding first ("That's a free spot in the diary."), then empty acknowledgements, later ones before the opener.
        parts = [x for x in parts if not FLUFF.match(x)] or parts
        for i in sorted((i for i, x in enumerate(parts) if ACK.match(x) and len(x.split()) <= 5), key=lambda i: (i == 0, -i)):
            if len(parts) - 1 >= MAX_SENTENCES or len(parts) > MAX_SENTENCES:
                parts = parts[:i] + parts[i + 1:]
            if len(parts) <= MAX_SENTENCES:
                break
        text = " ".join(parts)
    if len(parts) > MAX_SENTENCES:
        # Keep any sentence carrying a number, address or time (a read-back), and her last question.
        chosen = {i for i, x in enumerate(parts) if re.search(r"\d|\b(?:unit|flat|apartment)\b", x, re.I) or offered_slots(x)}
        last_q = next((i for i in range(len(parts) - 1, -1, -1) if parts[i].endswith("?")), None)
        chosen.add(last_q if last_q is not None else MAX_SENTENCES - 1)
        for i in range(len(parts)):
            if len(chosen) >= MAX_SENTENCES:
                break
            chosen.add(i)
        text = " ".join(parts[i] for i in sorted(chosen))

    # 1. Read back a number the caller just gave, first, as a statement, so her own question still comes last.
    said = [m.group(0) for m in PHONE.finditer(caller)]
    if said:
        have_number = True
        if not any(_digits(n) in _digits(text) for n in said):
            fixes.append("read_back")
            name = caller_name(caller)
            # The read-back already thanks them by name, so drop the brain's own "Sure thing, Tom." / "I've noted..." lines.
            rest = [x for x in _sentences(text) if not ((ACK.match(x) and len(x.split()) <= 4) or NOTED.match(x))]
            text = (f"So that's {name} on {said[-1]}. " if name else f"So that's {said[-1]}. ") + " ".join(rest)
            text = text.strip()

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
