#!/usr/bin/env python3
"""Make starter training calls for teaching Qwen to talk like Mila.

Every call is made up (no real customer data). They teach the habits:
short spoken replies, one question at a time, understanding local talk
and going along with it without starting it, reading details back, and
never inventing prices or promises, and following each shop's own
answers (its questionnaire card) for days, prices and what it does.

These are seeds. A few hundred templated calls teach the style; widen them
with a stronger model before a serious training run.

    python3 make_seed_data.py --out data --count 300
    -> data/train.jsonl, data/valid.jsonl  (chat format, one call per line)
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nodes"))
from shop_card import ShopCard   # noqa: E402

SHOPS = {
    "au": [("Birch and Co Plumbing", "plumber", "Dave"), ("Kingsley Electrical", "electrician", "Sam"),
           ("Northside Mowing", "gardener", "Jess"), ("Harbour Mobile Mechanics", "mechanic", "Tony"),
           ("Coastline Carpentry", "carpenter", "Mick"), ("Bright Spark Air Con", "air conditioning technician", "Priya")],
    "ca": [("Maple Ridge Plumbing", "plumber", "Dan"), ("Northern Lights Electric", "electrician", "Sara"),
           ("Prairie Heating", "heating technician", "Marc"), ("Lakeside Auto", "mechanic", "Jo")],
}
NAMES = ["Sarah", "Michael", "Bec", "Jason", "Linda", "Tom", "Aisha", "Greg", "Mei", "Shane", "Karen", "Luca"]
SLOTS = [("Thursday", "2:00pm"), ("tomorrow", "9:30am"), ("Friday", "11:00am"), ("Monday", "3:30pm"), ("Wednesday", "8:00am")]
PROBLEMS = {
    "plumber": ["hot water system", "kitchen tap", "toilet", "shower drain"],
    "electrician": ["power point in the kitchen", "lights in the lounge", "switchboard", "oven"],
    "gardener": ["back lawn", "hedges out the front", "garden beds"],
    "mechanic": ["ute", "car", "van"],
    "carpenter": ["back deck", "front door", "side gate"],
    "air conditioning technician": ["air con in the lounge", "split system"],
    "heating technician": ["furnace", "thermostat"],
}
BROKEN = {"au": ["has carked it", "is cactus", "is playing up", "is on the blink", "is stuffed"],
          "ca": ["is on the fritz", "is kaput", "has quit on me"]}
WHEN = {"au": ["this arvo", "tomorrow arvo", "first thing tomorrow", "sometime this week"],
        "ca": ["this afternoon", "first thing tomorrow", "sometime this week"]}
CASUAL_OK = {"au": ["Too easy.", "No worries.", "Easy done."], "ca": ["For sure.", "No problem at all.", "You bet."]}
PLAIN_OK = ["Of course.", "Sure thing.", "Certainly."]
THANKS = {"au": ["Cheers mate.", "Too easy, ta.", "Beauty, thanks heaps."], "ca": ["Thanks a bunch.", "Perfect, thanks, eh."]}
PLAIN_THANKS = ["Thank you.", "Great, thanks.", "That's perfect, thank you."]


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
FEES = {"au": "$90", "ca": "$110"}


def make_card(r, c, shop, trade, owner, **overrides) -> ShopCard:
    """A made-up shop's questionnaire answers. Calls must agree with the card."""
    answers = {"shop_name": shop, "trade": trade, "owner_name": owner, "country": c,
               "open_days": WEEKDAYS + (["saturday"] if r.random() < 0.25 else []),
               "open_hours": r.choice(["7am to 4pm", "8am to 5pm", "7:30am to 3:30pm"]),
               "services": PROBLEMS[trade], "bookings": "book"}
    answers.update(overrides)
    return ShopCard(answers)


def call_booking(r, c, shop, trade, owner):
    name, (day, time), casual = r.choice(NAMES), r.choice(SLOTS), r.random() < 0.6
    thing, broke, when = r.choice(PROBLEMS[trade]), r.choice(BROKEN[c]), r.choice(WHEN[c])
    opener = (f"G'day, my {thing} {broke}, reckon someone could come {when}?" if c == "au" and casual else
              f"Hey there, my {thing} {broke}, any chance someone could come {when}?" if casual else
              f"Hello, my {thing} has stopped working. Could someone come out {when}?")
    ok = r.choice(CASUAL_OK[c]) if casual else r.choice(PLAIN_OK)
    bye = r.choice(THANKS[c]) if casual else r.choice(PLAIN_THANKS)
    return [("user", opener),
            ("assistant", f"Oh no, sorry to hear that. The next spot {owner} has is {day} at {time}. Would that suit?"),
            ("user", "Yeah nah yeah, that works." if c == "au" and casual else "For sure, that works." if casual else "Yes, that works."),
            ("assistant", f"{ok} Can I grab your name and the address?"),
            ("user", f"It's {name}, {r.randint(2, 98)} {r.choice(['Smith', 'Station', 'Victoria', 'Church', 'George'])} Street."),
            ("assistant", f"Thanks {name}. So that's {owner} coming {day} at {time}. Is this the best number to reach you on?"),
            ("user", f"Yep. {bye}"),
            ("assistant", ("No worries at all, " if casual and c == "au" else "You're welcome, ") + f"{name}. {owner} will see you {day}.")]


def call_no_means_no(r, c, shop, trade, owner):
    day, time = r.choice(SLOTS)
    other_day, other_time = r.choice([s for s in SLOTS if s[0] != day])
    refuse = "Yeah, nah, I'm flat out then." if c == "au" else "Ah, no, I'm swamped then."
    return [("user", f"Hi, I need a {trade} to come and have a look at something."),
            ("assistant", f"Happy to help. {owner} has {day} at {time} free. Would that work for you?"),
            ("user", refuse),
            ("assistant", f"No problem. How about {other_day} at {other_time} instead?"),
            ("user", "Nah yeah, that's better." if c == "au" else "For sure, that's better."),
            ("assistant", f"Great, I'll put you down for {other_day} at {other_time}. Can I get your name?")]


def call_price_unknown(r, c, shop, trade, owner):
    thing = r.choice(PROBLEMS[trade])
    return [("user", f"How much do you reckon it'd be to fix my {thing}?" if c == "au" else f"What would it run me to fix my {thing}?"),
            ("assistant", f"I don't want to guess and get it wrong, because it depends on what {owner} finds. "
                          f"I can have {owner} call you back with a proper price. What's the best number?"),
            ("user", "Yeah righto, it's 0412 345 678." if c == "au" else "Sure, it's 604-555-0199."),
            ("assistant", ("So that's 0412 345 678. " if c == "au" else "So that's 604-555-0199. ") + f"I'll get {owner} to ring you today.")]


def call_misheard(r, c, shop, trade, owner):
    name = r.choice(NAMES)
    return [("user", f"Yeah it's {name}, I'm at... [unclear] ...Road, can you send someone?"),
            ("assistant", f"Sorry {name}, the line dropped out for a second. Could you give me the street name once more?"),
            ("user", "Old Coach Road. Number 22."),
            ("assistant", "Got it, 22 Old Coach Road. And what do you need a hand with?")]


def call_readback(r, c, shop, trade, owner):
    name = r.choice(NAMES)
    number = f"04{r.randint(10, 99)} {r.randint(100, 999)} {r.randint(100, 999)}" if c == "au" else f"{r.choice(['604', '416', '403'])}-555-01{r.randint(10, 99)}"
    return [("user", f"Can you just get {owner} to call me back? It's {name}."),
            ("assistant", f"Of course, {name}. What's the best number for {owner} to call?"),
            ("user", number + "."),
            ("assistant", f"That's {number}. I'll pass that on to {owner} now. Is there anything you'd like me to tell them?"),
            ("user", "Nah, all good." if c == "au" else "No, that's all."),
            ("assistant", f"Lovely. {owner} will be in touch soon.")]


def call_out_of_scope(r, c, shop, trade, owner):
    """Something the card doesn't mention: she doesn't guess."""
    return [("user", "Do you guys do paving as well?"),
            ("assistant", f"I'm not sure, to be honest, and I'd hate to tell you wrong. I can ask {owner} and have them call you back. Would that help?"),
            ("user", "Yeah, that'd be good." if c == "au" else "Yeah, that'd be great."),
            ("assistant", "No problem. What's your name and the best number?")]


def call_not_offered(r, c, shop, trade, owner):
    """Something the card says they don't do: she says so kindly."""
    thing = "tiling" if trade == "carpenter" else "roofing"
    return ({"not_offered": [thing, "asbestos removal"]},
            [("user", f"Do you guys do {thing} as well?"),
             ("assistant", f"Sorry, {thing} isn't something {owner} does. Is there anything else I can help with?"),
             ("user", "Nah, that was it, cheers." if c == "au" else "No, that was it, thanks."),
             ("assistant", "No worries, thanks for calling." if c == "au" else "No problem, thanks for calling.")])


def call_price_allowed(r, c, shop, trade, owner):
    """The card lists one price: she says that one and no others."""
    fee, thing = FEES[c], r.choice(PROBLEMS[trade])
    return ({"prices": {"call-out fee": fee}},
            [("user", f"What do you charge to come and look at my {thing}?"),
             ("assistant", f"The call-out fee is {fee}. Anything beyond that depends on what {owner} finds, so they'd tell you before starting."),
             ("user", "And how much to fix it, roughly?"),
             ("assistant", f"I can't give you a figure for that, sorry, I'd only be guessing. {owner} can give you a proper price once they've seen it. Would you like to book a time?")])


def call_closed_day(r, c, shop, trade, owner):
    """Asked for a day the card says they don't work."""
    day, time = r.choice([s for s in SLOTS if s[0] in ("Monday", "Wednesday", "Friday")])
    return ({"open_days": WEEKDAYS},
            [("user", "Any chance someone could come out Sunday?"),
             ("assistant", f"Sorry, {owner} doesn't work Sundays. The next spot is {day} at {time}. Would that suit?"),
             ("user", "Yeah, righto, that'll do." if c == "au" else "Sure, that works."),
             ("assistant", f"Great, I'll put you down for {day} at {time}. Can I get your name?")])


def call_message_only(r, c, shop, trade, owner):
    """The card says take messages, don't book."""
    name, thing = r.choice(NAMES), r.choice(PROBLEMS[trade])
    return ({"bookings": "message"},
            [("user", f"Hi, can I book someone in to look at my {thing}?"),
             ("assistant", f"I can't book it in myself, but I'll get {owner} to call you back and sort out a time. Can I grab your name?"),
             ("user", f"It's {name}."),
             ("assistant", f"Thanks {name}. And what's the best number for {owner} to call?")])


CALLS = [(call_booking, 5), (call_no_means_no, 2), (call_price_unknown, 2), (call_misheard, 1), (call_readback, 2),
         (call_out_of_scope, 1), (call_not_offered, 2), (call_price_allowed, 2), (call_closed_day, 2), (call_message_only, 2)]


def make(count: int, seed: int = 7, au_share: float = 0.75):
    r = random.Random(seed)
    makers = [m for m, weight in CALLS for _ in range(weight)]
    rows, seen = [], set()
    while len(rows) < count:
        c = "au" if r.random() < au_share else "ca"
        shop, trade, owner = r.choice(SHOPS[c])
        made = r.choice(makers)(r, c, shop, trade, owner)
        overrides, turns = made if isinstance(made, tuple) else ({}, made)
        card = make_card(r, c, shop, trade, owner, **overrides)
        key = shop + json.dumps(turns)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"messages": [{"role": "system", "content": card.instructions()}]
                     + [{"role": role, "content": text} for role, text in turns]})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data")
    p.add_argument("--count", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = make(args.count, args.seed)
    cut = max(1, len(rows) // 10)
    for name, part in (("valid.jsonl", rows[:cut]), ("train.jsonl", rows[cut:])):
        path = out / name
        if path.exists():
            raise SystemExit(f"{path} already exists. Pick a new --out folder so nothing is overwritten.")
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in part))
        print(f"wrote {len(part):4} calls -> {path}")


if __name__ == "__main__":
    main()
