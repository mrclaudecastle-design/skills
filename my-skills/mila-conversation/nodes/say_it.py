#!/usr/bin/env python3
"""say_it: turn written details into words a person would say out loud.

Runs on Mila's reply just before the voice reads it, so "0412 345 678"
is not read as "four hundred and twelve". No dependencies.

    from say_it import say_it
    say_it("See you at 2:30pm at 3/14 Smith St, it's $85.")
"""
import re

ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
STREETS = {"St": "Street", "Rd": "Road", "Ave": "Avenue", "Dr": "Drive",
           "Ct": "Court", "Pl": "Place", "Cres": "Crescent", "Hwy": "Highway",
           "Pde": "Parade", "Tce": "Terrace", "Ln": "Lane", "Blvd": "Boulevard",
           "Cl": "Close"}


def number_words(n: int) -> str:
    """0 and up in words, the way people say them."""
    if n >= 1_000_000:
        m, r = divmod(n, 1_000_000)
        joiner = " and " if 0 < r < 100 else " "
        return number_words(m) + " million" + (joiner + number_words(r) if r else "")
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + ("-" + ONES[o] if o else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" and " + number_words(r) if r else "")
    th, r = divmod(n, 1000)
    joiner = " and " if 0 < r < 100 else " "
    return number_words(th) + " thousand" + (joiner + number_words(r) if r else "")


def digits(s: str, zero: str = "oh") -> str:
    """Read digits one by one: '0412' -> 'oh four one two'."""
    return " ".join(zero if c == "0" else ONES[int(c)] for c in s if c.isdigit())


def _phone(*groups):
    return ", ".join(digits(g) for g in groups)


def _money(m):
    dollars = int(m.group(1).replace(",", ""))
    cents = m.group(2)
    unit = "dollar" if dollars == 1 else "dollars"
    if cents and int(cents) and dollars == 0:
        return f"{number_words(int(cents))} cents"
    if cents and int(cents):
        return f"{number_words(dollars)} {unit} {number_words(int(cents))}"
    return f"{number_words(dollars)} {unit}"


def _time(m):
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower().replace(".", "")
    if hour > 24 or minute > 59:
        return m.group(0)                       # not a time: leave it as written
    if hour in (0, 24):
        hour, ampm = 12, "am"                   # 0:30 is half past twelve at night
    elif hour > 12:
        hour, ampm = hour - 12, "pm"
    if hour == 12 and ampm == "am":
        if minute == 0:
            return "midnight"
        part_12 = " at night"
    elif hour == 12 and minute == 0 and ampm == "pm":
        return "midday"
    else:
        part_12 = None
    part = {"am": " in the morning", "pm": " in the afternoon" if hour in (12, 1, 2, 3, 4, 5) else " at night"}.get(ampm, "")
    if ampm == "pm" and 6 <= hour <= 8:
        part = " in the evening"
    if part_12:
        part = part_12
    nxt = number_words(hour % 12 + 1)
    h = number_words(hour)
    if minute == 0:
        return f"{h} o'clock{part}"
    if minute == 15:
        return f"quarter past {h}{part}"
    if minute == 30:
        return f"half past {h}{part}"
    if minute == 45:
        return f"quarter to {nxt}{part}"
    mins = ("oh " if minute < 10 else "") + number_words(minute)
    return f"{h} {mins}{part}"


def say_it(text: str) -> str:
    t = text
    # Phone numbers first, before anything else touches the digits.
    def _local(m):                                   # +61 412 345 678 is read the local way: oh four one two...
        d = "0" + re.sub(r"\D", "", m.group(1)).lstrip("0")
        return f"{d[:4]} {d[4:7]} {d[7:]}" if d.startswith("04") else f"{d[:2]} {d[2:6]} {d[6:]}"
    t = re.sub(r"(?<![\d+])\+61[ -]?((?:\(0\)[ -]?)?[2-478](?:[ -]?\d){8})(?!\d)", _local, t)
    t = re.sub(r"(?<![\d+])\+1[ .-]?(?=\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d))", "", t)
    t = re.sub(r"(?<!\d)(04\d{2})[ -]?(\d{3})[ -]?(\d{3})(?!\d)", lambda m: _phone(*m.groups()), t)      # AU mobile
    t = re.sub(r"(?<!\d)\(?(0[2378])\)?[ -]?(\d{4})[ -]?(\d{4})(?!\d)", lambda m: _phone(*m.groups()), t)  # AU landline
    t = re.sub(r"(?<!\d)(1[38]00)[ -]?(\d{3})[ -]?(\d{3})(?!\d)",
               lambda m: f"{'thirteen' if m.group(1) == '1300' else 'one eight'} hundred, {_phone(m.group(2), m.group(3))}", t)
    t = re.sub(r"(?<!\d)\(?(\d{3})\)?[ .-](\d{3})[ .-](\d{4})(?!\d)", lambda m: _phone(*m.groups()), t)   # Canada / US
    t = re.sub(r"(?<![\d$])\b(0[2378])(\d{2})[ -](\d{3})[ -](\d{3})(?!\d)",                              # a landline written 0299 998 888
               lambda m: _phone(m.group(1), m.group(2) + m.group(3)[:2], m.group(3)[2:] + m.group(4)), t)
    # Emergency lines and everyday short forms.
    t = re.sub(r"(?<![\d$.,:/-])\b000\b(?![\d.,:/-]\d)", "triple zero", t)
    t = re.sub(r"(?<![\d$.,:/-])\b911\b(?![\d.,:/-]\d)", "nine one one", t)
    t = re.sub(r"\b24/7\b", "twenty-four seven", t)
    t = re.sub(r"(?<![\d.,])\b(\d{1,3})\s?%", lambda m: f"{number_words(int(m.group(1)))} percent", t)
    # Money.
    t = re.sub(r"\$(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))?", _money, t)
    # Times: 2:30pm, 2.30pm, 2pm, 14:30.
    t = re.sub(r"\b(\d{1,2})\.(\d{2})(?=\s*(?:[ap]\.m\.|[ap]m)(?!\w))", r"\1:\2", t, flags=re.I)
    t = re.sub(r"\b(\d{1,2}):(\d{2})\s*([ap]\.m\.|[ap]m)?(?![\w:])", _time, t, flags=re.I)
    t = re.sub(r"\b(\d{1,2})()\s*([ap]\.m\.|[ap]m)(?!\w)", _time, t, flags=re.I)
    # Unit and street number: 3/14 Smith St -> unit three, fourteen Smith St.
    t = re.sub(r"\b(\d{1,3})/(\d{1,4})(?= [A-Z])",
               lambda m: f"unit {number_words(int(m.group(1)))}, {number_words(int(m.group(2)))}", t)
    # Street number before a street name: 14 Smith St -> fourteen Smith St.
    street = "|".join(STREETS) + "|" + "|".join(STREETS.values())
    # A letter on the end: 12A Smith St -> twelve A Smith St, Unit 4B -> Unit four B.
    t = re.sub(rf"\b(\d{{1,4}})([A-Za-z])(?= (?:[A-Z][\w']+ ){{1,3}}(?:{street})\b)", lambda m: f"{number_words(int(m.group(1)))} {m.group(2).upper()}", t)
    t = re.sub(r"\b((?i:unit|flat|apartment|shop|suite|lot)) (\d{1,4})([A-Za-z])?\b(?![/:.]\d)",
               lambda m: f"{m.group(1)} {number_words(int(m.group(2)))}" + (f" {m.group(3).upper()}" if m.group(3) else ""), t)
    t = re.sub(rf"\b(\d{{1,4}})(?= (?:[A-Z][\w']+ ){{1,3}}(?:{street})\b)", lambda m: number_words(int(m.group(1))), t)
    # Street short forms, only after a capitalised name so "St Kilda" is left alone.
    t = re.sub(rf"\b([A-Z][\w']+) ({'|'.join(STREETS)})\b(?! [A-Z])", lambda m: f"{m.group(1)} {STREETS[m.group(2)]}", t)
    return t


if __name__ == "__main__":
    for line in ["Ring me back on 0412 345 678.", "That's $85, or $1,250.50 for the lot.",
                 "I can do 2:30pm Thursday at 3/14 Smith St.", "Office is (02) 9876 5432, open till 5pm."]:
        print(f"{line}\n  -> {say_it(line)}")
