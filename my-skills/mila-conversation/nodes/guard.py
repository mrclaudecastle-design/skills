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
DOING = re.compile(r"\b(?:will|'ll|can|going to|gonna)\b[^.!?]*\b(?:call|ring|phone|come|be there|be with you|be out|see you|fit you in|pass|let \w+ know|"
                   r"head over|get back|get out|pop (?:over|round)|sort)\b", re.I)
HEDGED = re.compile(r"\b(?:can't|cannot|can not|won't|not able|unable|no free|isn't|not sure|don't)\b", re.I)
ASK_WHEN = re.compile(r"\bwhat (?:day|time)\b[^.!?]*\?|\bwhen (?:would|works|suits|is good|are you)\b[^.!?]*\?|\bwhich day\b[^.!?]*\?", re.I)
FILLER = re.compile(r"^(?:have a (?:great|good|lovely|nice|wonderful) (?:day|one|arvo|afternoon|evening|night|weekend)[.!]|"
                    r"thanks for (?:confirming|the details|that|calling)[.!]|let me know if you need (?:help with )?anything else[.!]|"
                    r"thanks for your patience[.!]|sound good\?|feel free to (?:call|reach out)[^.!?]*[.!]|"
                    r"let (?:me|us) know (?:how|if) (?:we|i) can (?:help|assist)[^.!?]*[.!])$", re.I)
NAME = re.compile(r"\b(?i:it's|its|it is|this is|my name is|my name's|name's|i'm|i am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")
NOT_NAMES = {"Just", "Not", "After", "Looking", "Calling", "Flat", "Sorry", "At", "On", "About", "Good", "Fine", "Here", "Still", "Also",
             "Unit", "Number", "Apartment", "Level", "Lot", "Shop", "Suite"}
URGENT = re.compile(r"\b(?:urgent|emergency|flood(?:ing|ed)?|burst|pouring|gushing|no (?:water|power|heat(?:ing)?)|smell(?:s)? (?:of |like )?(?:gas|burning)|"
                    r"sparks?|sparking|on fire|smoke|sewage|overflow(?:ing)?|can't wait|asap)\b", re.I)
ACK = re.compile(r"^(?:thanks|thank you|got it|great|sure(?: thing)?|okay|ok|no problem|perfect|lovely|i've noted|i have noted|noted)\b", re.I)
ADDRESS = re.compile(r"\b(?:(?:unit|flat|apartment) \d+[a-z]?,? ?)?\d{1,4}[a-z]?(?:/\d{1,4})? (?:[A-Z][\w']+ ){1,3}"
                     r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Highway|Hwy|Parade|Pde|Terrace|Tce|Lane|Ln|Boulevard|Blvd|Close|Way)\b")
ANYTHING_ELSE = re.compile(r"^is there anything else (?:i can (?:assist|help)(?: you)?(?: with)?|you need|you'd like to add|you want to add)[^?]*\?$", re.I)
FLUFF = re.compile(r"^(?:that(?:'s| is| slot's| slot is) (?:a |still )?free(?: spot)?(?: in the diary)?[.!]|that's available[.!])$", re.I)
NOTED = re.compile(r"^i(?:'ve| have) (?:noted|got|taken|recorded)\b[^?]*$", re.I)
VAGUE_SOON = re.compile(r"\b(?:shortly|in no time|(?<!as )soon(?! as))\b", re.I)
OFFICE = re.compile(r"\b(?:as soon as|once|when) (?:he|she|they)(?:'s|'re| is| are| gets?) back (?:in|at|to) the office\b", re.I)
MATE = re.compile(r",? mate\b", re.I)
CLOCK = re.compile(r"\b\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?(?![a-z])", re.I)
SLOT_OR_TIME = re.compile(DAY + r"|(\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)(?![a-z])", re.I)
STREET_TYPES = (r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Highway|Hwy|Parade|Pde|"
                r"Terrace|Tce|Lane|Ln|Boulevard|Blvd|Close|Way)")
STREET = re.compile(r"\b((?:[A-Z][\w']+ ){1,3}" + STREET_TYPES + r")\b")
HOUSE_NUMBER = re.compile(r"(?<![\d:/])\d{1,4}[a-z]?(?![\d:])", re.I)
REFUSE_BEFORE = re.compile(r"\b(?:not(?!\s+(?:bad|till|until))|no(?=\s+(?:on\s+)?" + DAY + r")|"
                           r"(?:can't|cannot|can not|couldn't|won't)(?!\s+you\b))\b"
                           r"(?:\s+(?!till\b|until\b|before\b|after\b|by\b|from\b)[\w']+){0,3}?\s+(?:on\s+)?" + DAY, re.I)
REFUSE_BUSY = re.compile(r"\b(?:flat out|busy|away|tied up|booked up|out of town|anything but|except|other than|apart from)\s+(?:on\s+)?" + DAY, re.I)
REFUSE_AFTER = re.compile(DAY + r"(?:'s|\s+is)?\s+(?:no good|not good|out|no go|a no|not great|bad|no use)\b|"
                          + DAY + r"\s+(?:doesn't|does not|won't|wouldn't|isn't)\b(?!\s+(?:too\s+)?bad)", re.I)
BOOKED = re.compile(r"\b(?:i've|i have|we've|we have)\s+(?:booked|got you (?:down|in|booked)|locked (?:you|that|it) in|pencilled)|"
                    r"\byou're (?:all )?(?:booked|set|locked in)\b|\bbooked (?:you|that|it) in\b|\bthat's (?:booked|locked in)\b|"
                    r"\bi'll (?:book|lock|pop) (?:you|that|it) in\b|\b(?:your )?booking(?:'s| is) (?:confirmed|locked in|all set)\b|"
                    r"\b(?:locked|booked) (?:it|that|you) in\b|\ball booked\b|\bconfirmed your booking\b", re.I)
YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|correct|that's right|that's it|spot on|perfect|sounds good|sure|ok|okay|all good|"
                 r"too easy|lovely|right|bang on|that's correct|that's all correct|all correct|all right|thanks|thank you|cheers|ta|great|"
                 r"good)\b(?!\W*(?:but|no|not|wait|actually|hang on))", re.I)   # the ears often lose the "yes" before "thanks"
ADDRESS_SAID = re.compile(r"(?:\b(?:unit|flat)\s*\d{1,4}[a-z]?,?\s*)?(?:\bnumber\s*)?(?<![\d/])\d{1,4}[a-z]?(?:/\d{1,4})?,?\s+"
                          r"(?:[a-z']+\s+){0,3}[a-z']*" + r"(?:street|road|avenue|drive|court|place|crescent|highway|parade|terrace|lane|boulevard|close|way|st|rd|ave|dr|ct|pl|cres)\b", re.I)
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
        elif lw == "a" and re.match(r"\s+(?:hundred|thousand)\b", "".join(words[i + 1:i + 3]).lower()):
            run.append("1"); unit[0] = False                   # "a hundred and six"
        elif lw in ("hundred", "thousand") and run and not run[-1].startswith("0"):
            scale = 100 if lw == "hundred" else 1000
            base = int(run.pop()) * scale
            k = i + 1                                  # "nine hundred (and) ninety nine"
            rest = re.match(r"((?:\s+and)?\s+)([a-z]+)(?:[\s-]+([a-z]+))?", "".join(words[k:k + 6]).lower())
            if rest and re.match(r"[\s-]*(?:[a-z]+[\s-]+)?(?:hundred|thousand)\b", "".join(words[k:k + 6]).lower()[len(rest.group(1)):]):
                rest = None                            # "three thousand four hundred": let "four hundred" come next
            add, used = 0, ""
            if rest and (rest.group(2) in _TEENS or rest.group(2) in _TENS or rest.group(2) in _UNITS) and rest.group(2) not in ("oh", "o"):
                w2 = rest.group(2)
                add = _TEENS.get(w2) or _TENS.get(w2) or _UNITS.get(w2, 0)
                used = rest.group(1) + w2
                if w2 in _TENS and rest.group(3) in _UNITS and rest.group(3) not in ("oh", "o", "zero"):
                    add += _UNITS[rest.group(3)]
                    used = rest.group(0)
            if used:
                consumed, j = 0, k
                while consumed < len(used) and j < len(words):
                    consumed += len(words[j]); j += 1
                i = j - 1
            if run and int(run[-1]) >= 1000 and int(run[-1]) % 1000 == 0 and base + add < 1000:
                run[-1] = str(int(run[-1]) + base + add)
            else:
                run.append(str(base + add))
            unit[0] = False
        elif lw in _UNITS and not (lw == "o" and run == []):
            run.append(str(_UNITS[lw]) * repeat); repeat = 1; unit[0] = True
        elif w.isdigit():                 # written digits stay exactly as written
            flush(); out.append(w)
        elif (w.isspace() or w in (",", "-")) and run:
            k = i + 1
            while k < len(words) and (words[k].isspace() or words[k] in (",", "-")):
                k += 1
            nxt = words[k].lower() if k < len(words) else ""
            # "oh four one two, three four five" and "oh four twelve, ..." are one phone number;
            # "unit two, three Smith Street" and "unit three, forty seven" are two numbers.
            so_far = "".join(run)
            phone_like = (so_far.startswith("0") or len(so_far) >= 4) and len(so_far) < 10   # a full phone number ends at 10
            digit_word = nxt in _UNITS or nxt in ("double", "triple")
            join = (phone_like and (digit_word or nxt in _TEENS or nxt in _TENS)) or nxt in ("hundred", "thousand")   # "unit two three" stays "2 3": ask, don't guess
            if not join:
                flush(); out.extend(words[i:k])       # keep the gap exactly as said
            i = k - 1
        else:
            flush(); out.append(w)
        i += 1
    flush()
    return re.sub(r"\b(\d{1,4})\s+(?:slash|over|stroke)\s+(\d{1,4})\b", r"\1/\2", "".join(out), flags=re.I)   # "3 slash 47" -> 3/47


HOURS_TALK = re.compile(r"\b(?:open|opening hours|hours|closed?|closes|shut)\b", re.I)
_T = r"\d{1,2}(?::\d{2})?(?:\s?[ap]\.?m\.?)?"
TIME_RANGE = re.compile(_T + r"\s*(?:to|till|until|-|–)\s*" + _T + r"(?![\w:])", re.I)
HOURS_PHRASE = re.compile(r"\b(?:open(?:s)?|close[sd]?|shut|until|till|from|start(?:s)?|finish(?:es)?)\s+(?:at\s+|around\s+)?" + _T + r"(?![\w:])", re.I)
RELATIVE = re.compile(r"\b(today|tonight|this (?:arvo|afternoon|morning|evening)|tomorrow)\b", re.I)
WEEK = "monday tuesday wednesday thursday friday saturday sunday".split()


def _hours_or_offer(m) -> str:
    """'open 7am to 4pm' is hours talk and is dropped; 'Wednesday 10am to 11am' or
    'Wednesday from 10am' is an offer, so its first time is kept."""
    before = m.string[:m.start()]
    next_to_day = re.search(DAY + r"\s*,?\s*(?:at\s+|from\s+)?$", before, re.I)
    day_span = re.search(DAY + r"\s+(?:to|till|through|-|–)\s+" + DAY + r"\s*,?\s*$", before, re.I)
    day_after = re.match(r"\s*,?\s*(?:on\s+|this\s+|next\s+)?" + DAY, m.string[m.end():], re.I)
    if (next_to_day and not day_span or day_after) and not HOURS_TALK.search(before):
        times = re.findall(_T, m.group(0))
        first = times[0]
        if not re.search(r"[ap]\.?m", first, re.I):          # "10 to 11 am": the first time borrows "am"
            first += re.search(r"\s?[ap]\.?m\.?$", times[-1], re.I).group(0) if re.search(r"[ap]\.?m", times[-1], re.I) else ""
        return " at " + first + " "
    return " "


def _mask(text: str) -> str:
    """Blank out phone numbers, clock times and prices (same length), so only house numbers are left."""
    for rx in (PHONE, CLOCK, MONEY):
        text = rx.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _numbers_near(text: str, start: int, end: int, before: int, after: int, cut_before: bool) -> list[str]:
    head = text[max(0, start - before):start]
    if cut_before:
        head = re.split(r"[.!?]\s", head)[-1]
    tail = re.split(r"[.!?]", text[end:end + after])[0]
    return [n.lower() for n in HOUSE_NUMBER.findall(head + " " + tail)]


_FULL_TYPE = {"st": "street", "rd": "road", "ave": "avenue", "dr": "drive", "ct": "court", "pl": "place", "cres": "crescent",
              "hwy": "highway", "pde": "parade", "tce": "terrace", "ln": "lane", "blvd": "boulevard"}


def _compact(name: str) -> str:
    """'Harbour View St' -> 'harborviewstreet': no spaces, full street type, harbour/harbor alike."""
    words = re.findall(r"[a-z']+", name.lower())
    words = [_FULL_TYPE.get(w, w) for w in words]
    return re.sub(r"[^a-z]", "", "".join(words)).replace("our", "or")


def _street_heard(street: str, heard: str) -> bool:
    """Was this street said anywhere in the call, allowing run-together words ('Wattlestreet')
    and small spelling differences ('Harborview' / 'Harbour View')?"""
    from difflib import SequenceMatcher
    core = _compact(re.sub(r"\s+" + STREET_TYPES + r"$", "", street))
    hay = _compact(heard)
    if not core:
        return False
    if core in hay:
        return True
    n = len(core)
    if n < 5:
        return False
    return any(SequenceMatcher(None, core, hay[i:i + n]).ratio() >= 0.85 for i in range(0, max(1, len(hay) - n + 1)))


_TYPE_WORDS = r"(?:street|st|road|rd|avenue|ave|drive|dr|court|ct|place|pl|crescent|cres|highway|hwy|parade|pde|terrace|tce|lane|ln|boulevard|blvd|close|way)"
_UNIT_RX = re.compile(r"\b(?:unit|flat|apartment|apt)\s*(?:number\s*|no\.?\s*)?(\d{1,4}[a-z]?)\b", re.I)
_SLASH_RX = re.compile(r"(?<![\d/])(\d{1,4}[a-z]?)\s*/\s*(\d{1,4}[a-z]?)(?![\d/])", re.I)
_HOUSE_WORD_RX = re.compile(r"\b(?:street number|house number|number|no\.)\s*(?:is\s+|was\s+|'s\s+)?(\d{1,4}[a-z]?)\b", re.I)
_HOUSE_BEFORE_RX = re.compile(r"(?<![\d/])((?:\d\s){1,3}\d|\d{1,4}[a-z]?),?\s+(?:[a-z']+\s+){0,3}[a-z']*" + _TYPE_WORDS + r"\b", re.I)


def address_numbers(text: str) -> tuple[set, set, list]:
    """(unit numbers, house numbers, other numbers) in what was said.
    'unit 3, 47 Ocean Street', '3/47 Ocean St', 'the street number is 47', 'three two one Ocean Road' (321)."""
    units, houses = set(), set()
    for m in _SLASH_RX.finditer(text):
        units.add(m.group(1).lower()); houses.add(m.group(2).lower())
    for m in _UNIT_RX.finditer(text):
        units.add(m.group(1).lower())
    for m in _HOUSE_WORD_RX.finditer(text):
        houses.add(m.group(1).lower())
    for m in _HOUSE_BEFORE_RX.finditer(text):
        n = m.group(1).lower()
        if re.search(r"\b(?:unit|flat|apartment|apt)\s*(?:number\s*)?$", text[:m.start(1)], re.I) or "/" in text[max(0, m.start(1) - 2):m.start(1)]:
            continue                                    # that's the unit, said right before the street
        houses.add(n.replace(" ", ""))
        houses.update(n.split())                        # "three two one" may be 321 or not: allow either reading
    tagged = units | houses
    others = [n.lower() for n in HOUSE_NUMBER.findall(text) if n.lower() not in tagged]
    return units, houses, others


def _street_heard(street: str, heard: str) -> bool:
    """Was this street said anywhere in the call, allowing run-together words ('Wattlestreet')
    and small spelling differences ('Harborview' / 'Harbour View')? Street type must match if said."""
    from difflib import SequenceMatcher
    type_m = re.search(r"\s+(" + STREET_TYPES + r")$", street)
    core = _compact(street[:type_m.start()] if type_m else street)
    want_type = _compact(type_m.group(1)) if type_m else ""
    hay = _compact(heard)
    if not core:
        return False
    if len(core) < 6:                                   # short names must be whole words: "Park" is not "parking"
        words = re.sub(r"\s+" + STREET_TYPES + r"$", "", street).split()
        if not re.search(r"\b" + r"\s*".join(map(re.escape, (w.lower() for w in words))) + r"\b", heard.lower()):
            return False
    spots = [i for i in range(len(hay)) if hay.startswith(core, i)]
    n = len(core)
    if not spots and n >= 5:
        spots = [i for i in range(0, max(1, len(hay) - n + 1)) if SequenceMatcher(None, core, hay[i:i + n]).ratio() >= 0.85]
    if not spots:
        return False
    full_types = {_compact(t) for t in STREET_TYPES.strip("(?:)").split("|")}
    for i in spots:                                     # the type said after it, if any, must be the same
        after = hay[i + n:i + n + 12]
        said_type = next((t for t in sorted(full_types, key=len, reverse=True) if after.startswith(t)), "")
        if not said_type or not want_type or said_type == want_type:
            return True
    return False


def made_up_streets(reply: str, heard: str) -> list[str]:
    """Street names in the reply that the caller never said, or said with other numbers.
    Units must be numbers the caller gave as a unit and house numbers ones given as a house number:
    'Unit 47, number 3' for 'unit 3, 47', 'Unit 3' after '3 taps leaking', or 'Unit 22, number 22'
    for '22 Ocean Street' are caught. Street and numbers may come in different turns."""
    said = re.sub(r"\b(the|that|this|which|any|every|no|some) one\b", r"\1 _", reply, flags=re.I)
    said = spoken_numbers(said)
    r, h = _mask(said), _mask(spoken_numbers(heard))
    h_units, h_houses, h_other = address_numbers(h)
    bad = []
    for m in STREET.finditer(said):
        name = m.group(1)
        if not _street_heard(name, heard):
            bad.append(name)
            continue
        # the numbers that go with this street: the same sentence, up to 40 characters before and 25 after
        lo = max(0, m.start() - 40)
        cut = list(re.finditer(r"[.!?]\s", r[lo:m.start()]))
        lo = lo + cut[-1].end() if cut else lo
        window = re.split(r"[.!?]", r[lo:m.end() + 25])[0]
        units, houses, other = address_numbers(window)
        ok = units <= h_units and all(x in h_houses or (not h_houses and x in h_other) for x in houses) \
            and all(x in h_units | h_houses | set(h_other) for x in other)
        if not ok:
            bad.append(name)
    return bad


def refused_days(text: str) -> set:
    """Days the caller has said no to: 'not Thursday', 'Thursday's no good', 'I can't come Thursday',
    'I'm flat out Thursday', 'anything but Thursday'. Questions like 'Can't Dave do Thursday?' are not refusals."""
    days = set()
    for sentence in _sentences(text):
        question = sentence.rstrip().endswith("?")
        for m in REFUSE_BEFORE.finditer(sentence):
            if question and re.match(r"(?:can't|cannot|can not|couldn't|won't)", m.group(0), re.I):
                continue
            days.add(m.groups()[-1].lower())
        for m in REFUSE_BUSY.finditer(sentence):
            days.add(m.group(1).lower())
        for m in REFUSE_AFTER.finditer(sentence):
            days.add((m.group(1) or m.group(2) or "").lower())
    return days - {""}


def offered_slots(text: str, context_day: str = "", today: str | None = None) -> list[tuple[str, str]]:
    """Every (day, time) offered, in either order: 'Tuesday at 9:30am', '10am on Tuesday',
    'Tuesday at 9 or 11am', 'tomorrow at 2pm' (needs `today`, a weekday name).
    A time with no day comes back with context_day (a day said earlier), or '' if none.
    'today'/'tomorrow' with no `today` given comes back as '?', which can't be checked.
    Talk about opening hours ('open 7am to 5pm') is not an offer."""
    found = []
    text = spoken_numbers(text)
    def _ampm(n):                                    # "ten on Tuesday" -> 10am, "Tuesday at 2" -> 2pm
        n = int(n)
        return f"{n}{'am' if 7 <= n <= 11 else 'pm'}"
    # "ten o'clock", "half past nine", "quarter past two", "quarter to ten"
    text = re.sub(r"\b(\d{1,2})\s+o'clock(?:\s+(in the morning|in the afternoon|at night|in the evening))?",
                  lambda m: (f"{m.group(1)}{'am' if 'morning' in (m.group(2) or '') else 'pm'}" if m.group(2) else _ampm(m.group(1))), text, flags=re.I)
    def _past(m):
        h = int(m.group(3)); mins = {"half past": 30, "quarter past": 15, "quarter to": 45}[m.group(1).lower()]
        if m.group(1).lower() == "quarter to":
            h = 12 if h == 1 else h - 1
        return f"{h}:{mins:02d}" + _ampm(h)[len(str(h)):]
    text = re.sub(r"\b((half|quarter) (?:past|to))\s+(\d{1,2})(?![\d:])", _past, text, flags=re.I)
    text = re.sub(DAY + r"(,? at )(\d{1,2})(?![\d:]|\s?[ap]\.?m|\s*(?:/|unit|street))", lambda m: m.group(1) + m.group(2) + _ampm(m.group(3)) if 1 <= int(m.group(3)) <= 12 else m.group(0), text, flags=re.I)
    text = re.sub(r"(?<!have )(?<!has )(?<!got )(?<!there's )(?<!there are )(?<!is )(?<!are )\b(\d{1,2})(?![\d:]|\s?[ap]\.?m|\s+o'clock)(\s+on\s+" + DAY + r")",
                  lambda m: _ampm(m.group(1)) + m.group(2) if 1 <= int(m.group(1)) <= 12 else m.group(0), text, flags=re.I)
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
        last_day, day_seen = context_day, False
        for n, m in enumerate(hits):
            if m.group(1):
                last_day = context_day = m.group(1)
                day_seen = True
                continue
            nxt = hits[n + 1] if n + 1 < len(hits) else None
            gap = sentence[m.end():nxt.start()] if nxt else ""
            joiner = r"\s*(?:on|this|next)?\s*(?:this |next )?" if day_seen else r"\s*(?:on|this|next|,)?\s*(?:this |next )?"
            if nxt and nxt.group(1) and re.fullmatch(joiner, gap, re.I):   # "Tuesday at 9:30am, Thursday at 2pm" is a list
                found.append((nxt.group(1), m.group(2)))
            else:
                found.append((last_day, m.group(2)))
    return found


def is_urgent(text: str) -> bool:
    """Does what the caller said sound like an emergency?"""
    return bool(URGENT.search(text))


NAME_LOWER = re.compile(r"\b(?:it's|its|it is|this is|my name is|my name's|name's)\s+([a-z]{2,})(?=\s*(?:[,.!?]|$|\s+(?:here|calling|speaking)\b))", re.I)
NOT_NAME_WORDS = {"unit", "flat", "number", "apartment", "level", "lot", "shop", "suite", "me", "just", "the", "about", "urgent", "leaking", "broken", "fine", "good", "okay", "ok", "here", "now", "today",
                  "tomorrow", "true", "right", "correct", "wrong", "busy", "yes", "no", "not", "really", "that", "this", "it"}


def caller_name(text: str) -> str | None:
    for m in NAME.finditer(text):              # "It's Unit twelve. I'm Joe Brown." -> Joe Brown
        if m.group(1).split()[0] not in NOT_NAMES:
            return m.group(1)
    for m in NAME_LOWER.finditer(text):        # speech-to-text often comes in lower case: "its shane, ..."
        if m.group(1).lower() not in NOT_NAME_WORDS and m.group(1).capitalize() not in NOT_NAMES:
            return m.group(1).capitalize()
    return None


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
    reply_caps = {w.lower() for w in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z']{2,}", text)}
    caller_words = {w.lower() for w in re.findall(r"[A-Za-z']{3,}", caller)}
    is_read_back = bool(set(re.findall(r"\d+", text)) & set(re.findall(r"\d+", caller))) or bool(reply_caps & caller_words)
    gave_detail = bool(re.search(r"\d", caller))
    if last_reply and not is_read_back and not gave_detail and not text.rstrip().endswith("?") and re.sub(r"\W+", " ", text).strip().lower() == re.sub(r"\W+", " ", last_reply).strip().lower():
        fixes.append("repeat")
        text = "Thanks, I've got that."

    # 7. Never read out a blank template: "Monday 8 am | [Name]".
    if re.search(r"\[[^\]]{1,30}\]|\{[^}]{1,30}\}|\s\|\s|<[a-z_ ]{1,30}>", text, re.I):
        fixes.append("template")
        kept = [x for x in _sentences(text) if not re.search(r"\[|\]|\{|\}|\||<[a-z_ ]+>", x, re.I)]
        text = " ".join(kept) or "Sorry, could you say that again?"

    # 7b. Wording the card asks for: no "pass your message on" (there may be none), no booking a call back.
    worded = re.sub(r"\bpass (?:on )?(?:your|the) message(?: on)?(?: to (\w+))?", lambda m: f"let {m.group(1) or owner} know you called", text, flags=re.I)
    worded = re.sub(r"\bpass your message (?:on )?to (\w+)", r"let \1 know you called", worded, flags=re.I)
    worded = re.sub(r"\bbook (?:a time|a call(?: ?back)?|in a time) for (\w+) to (?:call|ring)(?: you)?(?: back)?", r"have \1 call you back", worded, flags=re.I)
    if worded != text:
        fixes.append("wording")
        text = worded

    # 7a. Speech only: no list marks or symbols.
    clean = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", text)
    clean = re.sub(r"[*_#`]+", "", clean).replace("\n", " ").replace(" — ", ", ").replace("—", ", ")
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    if clean != text:
        fixes.append("speech_only")
        text = clean

    # 9. Never read back a detail the caller hasn't given. An address she made up becomes a question.
    made_up = made_up_streets(text, heard_so_far + " " + caller)
    if made_up:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(a_ in x for a_ in made_up) and not x.endswith("?")]
        text = " ".join(kept + ["What's the address for the job?"])

    # 9b. Never read back a phone number the caller hasn't given (or the shop's own).
    heard_digits = _digits(spoken_numbers(heard_so_far + " " + caller)) + "|" + _digits(str(a.get("phone", "")))
    call_has_phone = bool(PHONE.search(spoken_numbers(heard_so_far + " " + caller)))
    fake = [] if (have_number and not call_has_phone) else \
        [m.group(0) for m in PHONE.finditer(text) if _digits(m.group(0)) not in heard_digits]
    if fake:
        fixes.append("made_up_detail")
        kept = [x for x in _sentences(text) if not any(f in x for f in fake) and not x.endswith("?")]
        text = " ".join(kept + ["What's the best number to reach you on?"])

    # 2. Prices: only the ones on the card.
    allowed = {_digits(str(v)) for v in (a.get("prices") or {}).values()}
    if any(_digits(m) not in allowed for m in MONEY.findall(text)):
        fixes.append("price")
        text = (f"I don't want to guess a price and get it wrong. I can have {owner} call you back with a proper one. "
                "Would that help?")

    # 2b. Asked about cost: say the card's prices plainly instead of only "can't say".
    asked_price = re.search(r"\b(?:how much|price|cost|ballpark|quote|charge|fee|rough idea|some idea|any idea|roughly)\b", caller, re.I)
    card_prices = a.get("prices") or {}
    if asked_price and card_prices and not MONEY.search(text) and "price" not in fixes:
        listed = "; ".join(f"the {k} is {v}" for k, v in card_prices.items())
        fixes.append("price_said")
        kept = [x for x in _sentences(text) if not x.endswith("?")][:1]
        text = " ".join(kept + [f"{listed[0].upper() + listed[1:]}, and the rest depends on the job. "
                                f"Would you like {owner} to call you with a proper price?"])

    # 3. Days and times: only real free spots, only on working days.
    open_days = {d.lower() for d in a.get("open_days", [])}
    # A time with no day takes its day from the call: what the caller just said, then her last reply, then earlier.
    refused_now = refused_days(caller)
    caller_days = [m.group(1).lower() for m in re.finditer(DAY, caller, re.I) if m.group(1).lower() not in refused_now]
    refused = (refused_days(heard_so_far) | refused_now) - set(caller_days)     # "Thursday then" later takes it back
    recent_days = caller_days[-1:] if caller_days else [   # the day the caller last named wins outright
        m.group(1).lower() for src in (last_reply, heard_so_far) for m in reversed(list(re.finditer(DAY, src, re.I)))
        if m.group(1).lower() not in refused]
    free_now = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}

    def which_day(t):
        for d in recent_days:                      # prefer a recent day where that time is actually free
            if free_now is None or (d, t) in free_now:
                return d
        return recent_days[0] if recent_days else ""
    offered = [(d.lower() or which_day(_norm_time(t)), _norm_time(t)) for d, t in offered_slots(text, "", today)]
    free = None if diary is None else {(d.lower(), _norm_time(t)) for d, t in diary}
    if free is not None and last_reply and BOOKED.search(last_reply):        # already booked: that spot has left the diary
        free |= {(d.lower(), _norm_time(t)) for d, t in offered_slots(last_reply, "", today) if d}
    def slot_ok(s):
        day, t = s
        if not day or day == "?":       # no day she or the caller named, or "tomorrow" without a date: can't check it
            return free is None and not open_days
        return (free is None or s in free) and (not open_days or day in open_days) and day not in refused
    bad_slot = any(not slot_ok(s) for s in offered)
    if offered and free is None:
        bad_slot = True          # she can't see the diary, so she can't offer a time
    if bad_slot:
        fixes.append("time")
        if diary:
            d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
            asked = SLOT.search(caller)     # tell the caller why, if they asked for a spot that isn't free
            why = f"Sorry, {asked.group(1).capitalize()} at {asked.group(2)} isn't free. " if asked else ""
            text = f"{why}The next free spot is {d} at {t}. Would that suit?"
        else:
            text = (f"I can't see the diary just now, so I won't guess a time. What day suits you best, "
                    f"and I'll have {owner} confirm it?")

    # 3b. Opening hours: only the card's.
    card_hours = TIME_RANGE.search(a.get("open_hours", "") or "")
    if card_hours:
        def _nt(t, ref):
            if not re.search(r"[ap]\.?m", t, re.I):
                suffix = re.search(r"([ap])\.?m", ref, re.I)
                t += (suffix.group(1) + "m") if suffix else ""
            return _norm_time(t) if re.search(r"[ap]m", t.replace(".", ""), re.I) else t
        ct = re.findall(_T, card_hours.group(0))
        c_open, c_close = _nt(ct[0], ct[-1]), _nt(ct[-1], ct[-1])

        def wrong_hours(sentence):
            if not HOURS_TALK.search(sentence) and not re.search(r"\bwe work\b", sentence, re.I):
                return False
            for rng in TIME_RANGE.finditer(sentence):
                ts = re.findall(_T, rng.group(0))
                if not re.search(r"[ap]\.?m", rng.group(0), re.I):       # "7 to 4": compare the hours only
                    hour = lambda t: int(re.match(r"\d+", t).group(0)) % 12
                    if (hour(ts[0]), hour(ts[-1])) != (hour(ct[0]), hour(ct[-1])):
                        return True
                elif (_nt(ts[0], ts[-1]), _nt(ts[-1], ts[-1])) != (c_open, c_close):
                    return True
            for m in re.finditer(r"\b(open(?:s)?|close[sd]?|closes|shut|finish(?:es)?)\s+(?:at\s+)?(" + _T + r")(?![\w:])", sentence, re.I):
                want = c_open if m.group(1).lower().startswith("open") else c_close
                if _nt(m.group(2), m.group(2)) != want:
                    return True
            return False
        hours_parts = _sentences(text)
        if any(wrong_hours(x) for x in hours_parts):
            fixes.append("hours")
            asked = any(wrong_hours(x) and x.endswith("?") for x in hours_parts)
            kept = [x if not wrong_hours(x) else f"We work {a['open_hours']}." for x in hours_parts]
            if asked and diary:
                d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
                kept.append(f"The next free spot is {d} at {t}. Would that suit?")
            text = " ".join(dict.fromkeys(kept))

    # 3c. Booking: only after the caller says yes to a full read-back (day and time, name, number, address),
    # with a free spot in the diary. Otherwise she reads back, or asks for what is still missing.
    if BOOKED.search(text) and not (last_reply and BOOKED.search(last_reply)):
        call = spoken_numbers(heard_so_far + " " + caller)
        name = caller_name(heard_so_far + " " + caller) or caller_name(call)
        phones = [m.group(0) for m in PHONE.finditer(call)]
        addresses = [m.group(0) for m in ADDRESS_SAID.finditer(_mask(call))]
        lr = last_reply or ""
        lr_slots = [(d.lower(), _norm_time(t)) for d, t in offered_slots(lr, "", today)]
        slot = next((s_ for s_ in lr_slots + offered if free is not None and s_ in free and s_[0] not in refused), None)
        lr_phones = [_digits(m.group(0)) for m in PHONE.finditer(lr)]
        phone_ok = (phones and lr_phones and lr_phones[-1] == _digits(phones[-1])) or (have_number and not phones and not lr_phones)
        confirmed = (YES.search(caller) and lr.rstrip().endswith("?") and slot is not None and slot in lr_slots and phone_ok
                     and ADDRESS_SAID.search(lr) and not made_up_streets(lr, heard_so_far))
        if a.get("bookings", "book") != "book":
            ask = f"I'll pass this to {owner} so he can lock in a time with you."
        elif confirmed:
            ask = None
        elif diary is None:
            ask = f"I can't see the diary just now, so I won't book it in yet. I'll have {owner} call you to lock in a time."
        elif not name:
            ask = "Can I grab your name?"
        elif not phones and not have_number:
            ask = "What's the best number to reach you on?"
        elif not addresses:
            ask = "What's the address for the job?"
        elif slot is None:
            d, t = next(((d, t) for d, t in diary if d.lower() not in refused), diary[0])
            ask = f"The next free spot is {d} at {t}. Would that suit?"
        else:
            day = next(d for d, _ in diary if d.lower() == slot[0])
            tm = next(t for d, t in diary if d.lower() == slot[0] and _norm_time(t) == slot[1])
            ph = _digits(phones[-1]) if phones else ""
            ph = f"{ph[:4]} {ph[4:7]} {ph[7:]}" if len(ph) == 10 and ph.startswith("04") else (phones[-1] if phones else "")
            number = f" on {ph}" if ph else ""
            ask = f"Just to check: {day} at {tm}, {name}{number}, at {addresses[-1].strip(' ,').title()}. Is that right?"
        if ask:
            fixes.append("booking")
            kept = [x for x in _sentences(text) if not BOOKED.search(x) and not x.endswith("?") and not offered_slots(x)
                    and not ((VAGUE_SOON.search(x) or SOON.search(x)) and DOING.search(x))]
            text = " ".join(kept[:1] + [ask])

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
        chosen = {i for i, x in enumerate(parts)
                  if re.search(r"\d|\b(?:unit|flat|apartment)\b", x, re.I) or STREET.search(x) or offered_slots(x)}
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

    # 11. One thing at a time: name, then number, then address. A call back never needs an address.
    call_so_far = heard_so_far + " " + caller
    wants_call_back = bool(re.search(r"\b(?:call|ring|phone) me\b|\bcall(?:s)? (?:me )?back\b|\bget (?:him|her|them|\w+) to (?:call|ring)\b",
                                     call_so_far, re.I)) or a.get("bookings", "book") != "book"
    have_name = bool(caller_name(call_so_far))
    have_phone = have_number or bool(PHONE.search(spoken_numbers(call_so_far)))
    have_address = bool(ADDRESS_SAID.search(_mask(spoken_numbers(call_so_far))))
    parts_q = _sentences(text)
    for i, q in enumerate(parts_q):
        if not q.endswith("?"):
            continue
        asks = [k for k, rx in (("name", r"\bname\b"), ("number", r"\b(?:phone )?number\b|\bphone\b|\bmobile\b"),
                                 ("address", r"\baddress\b|\bwhere (?:are you|is the job)\b")) if re.search(rx, q, re.I)]
        if wants_call_back and "address" in asks:
            asks.remove("address")
            if not asks:
                asks = ["none"]
        if len(asks) > 1 or asks == ["none"]:
            missing = [k for k, have in (("name", have_name), ("number", have_phone), ("address", have_address or wants_call_back)) if not have]
            nxt = missing[0] if missing else None
            fixes.append("one_ask")
            parts_q[i] = {"name": "Can I grab your name?", "number": "What's the best number to reach you on?",
                          "address": "What's the address for the job?", None: ""}[nxt]
    if "one_ask" in fixes:
        text = " ".join(x for x in parts_q if x) or "Thanks, I've got that."

    # 4. No call back promised without a number.
    # (Skipped when she is already asking something: one question at a time.)
    owner_calls = re.search(r"\b(?:call|ring|phone|get back to) you\b|\b(?:he|she|they|we|" + re.escape(owner) + r")(?:'ll| will| can)?\s+(?:give you a )?(?:call|ring)", text, re.I)
    goodbye = re.search(r"\b(?:bye|goodbye|see ya|hooroo|catch ya)\b", caller, re.I)
    if CALLBACK.search(text) and owner_calls and not goodbye and not have_number and not text.rstrip().endswith("?") \
            and not re.search(r"number", text, re.I):
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
