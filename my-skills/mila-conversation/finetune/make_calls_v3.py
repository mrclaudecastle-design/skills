#!/usr/bin/env python3
"""Make varied training calls (version 3) for teaching Qwen to talk like Mila.

Why a new version: the first training run copied the wording of the old
templates (it kept asking "Can I get your name?") instead of learning the
manners. Here every line Mila says has many wordings, the order she
gathers details changes from call to call, and three habits are in every
call where they apply:
  1. a phone number is always read back
  2. when she doesn't know, she says so and offers a call back
  3. she never asks for something the caller already gave

Every call is made up. No real customer data.

    python3 make_calls_v3.py --out data-v3 --count 1200
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
           ("Coastline Carpentry", "carpenter", "Mick"), ("Bright Spark Air Con", "air conditioning technician", "Priya"),
           ("Tidy Paws Dog Grooming", "dog groomer", "Kylie"), ("Summit Cleaning", "cleaner", "Rosa"),
           ("Ironbark Fencing", "fencer", "Baz"), ("Clearview Windows", "window cleaner", "Nat")],
    "ca": [("Maple Ridge Plumbing", "plumber", "Dan"), ("Northern Lights Electric", "electrician", "Sara"),
           ("Prairie Heating", "heating technician", "Marc"), ("Lakeside Auto", "mechanic", "Jo"),
           ("Cedar Home Cleaning", "cleaner", "Anne")],
}
JOBS = {   # (what the caller says is wrong, the service name on the card)
    "plumber": [("hot water system", "hot water systems"), ("kitchen tap", "leaking taps"), ("toilet", "toilets"), ("shower drain", "blocked drains")],
    "electrician": [("power point in the kitchen", "power points"), ("lights in the lounge", "lighting"), ("switchboard", "switchboards"), ("oven", "oven and cooktop wiring")],
    "gardener": [("back lawn", "lawn mowing"), ("hedges out the front", "hedge trimming"), ("garden beds", "garden tidy-ups")],
    "mechanic": [("ute", "servicing"), ("car", "servicing"), ("brakes", "brakes"), ("battery", "batteries")],
    "carpenter": [("back deck", "decks"), ("front door", "doors"), ("side gate", "gates")],
    "air conditioning technician": [("air con in the lounge", "air conditioner repairs"), ("split system", "split system servicing")],
    "dog groomer": [("dog", "full grooms"), ("puppy", "puppy grooms")],
    "cleaner": [("house", "regular house cleans"), ("rental", "end of lease cleans"), ("office", "office cleans")],
    "fencer": [("side fence", "timber fences"), ("back fence", "fence repairs"), ("pool fence", "pool fencing")],
    "window cleaner": [("windows", "window cleaning"), ("shopfront", "shopfront glass")],
    "heating technician": [("furnace", "furnace repairs"), ("thermostat", "thermostats")],
}
REPAIR_TRADES = {"plumber", "electrician", "mechanic", "carpenter", "air conditioning technician", "fencer", "heating technician"}
NAMES = ["Sarah", "Michael", "Bec", "Jason", "Linda", "Tom", "Aisha", "Greg", "Mei", "Shane", "Karen", "Luca", "Priyanka",
         "Daniel", "Chloe", "Hamish", "Fatima", "Ollie", "Nikki", "Raj", "Tracey", "Ben", "Zoe", "Wayne"]
STREETS = ["Smith Street", "Station Road", "Victoria Avenue", "Church Street", "George Street", "Old Coach Road",
           "Banksia Crescent", "Wattle Court", "High Street", "Ocean Parade", "Maple Drive", "King Street"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIMES = ["8:00am", "9:30am", "11:00am", "1:00pm", "2:00pm", "3:30pm"]
WEEKDAYS = [d.lower() for d in DAYS]


def p(r, *options):
    return r.choice(options)


def phone(r, c):
    if c == "au":
        return f"04{r.randint(10, 99)} {r.randint(100, 999)} {r.randint(100, 999)}"
    return f"{r.choice(['604', '416', '403', '780'])}-555-01{r.randint(10, 99)}"


class Ctx:
    """One made-up call: who is ringing, about what, and how they talk."""

    def __init__(self, r, c):
        self.r, self.c = r, c
        self.shop, self.trade, self.owner = r.choice(SHOPS[c])
        self.thing, self.service = r.choice(JOBS[self.trade])
        self.name, self.num = r.choice(NAMES), phone(r, c)
        self.addr = f"{r.randint(2, 140)} {r.choice(STREETS)}"
        self.casual = r.random() < 0.55
        self.repair = self.trade in REPAIR_TRADES
        days = r.sample(DAYS, 3)
        self.slots = [(d, r.choice(TIMES)) for d in sorted(days, key=DAYS.index)]
        self.card = {"shop_name": self.shop, "trade": self.trade, "owner_name": self.owner, "country": c,
                     "open_days": WEEKDAYS + (["saturday"] if r.random() < 0.25 else []),
                     "open_hours": r.choice(["7am to 4pm", "8am to 5pm", "7:30am to 4:30pm", "8am to 4pm"]),
                     "services": sorted({s for _, s in JOBS[self.trade]}), "bookings": "book"}
        self.diary = True

    # ---- the caller ----
    def problem(self):
        r, c, t = self.r, self.c, self.thing
        if not self.repair:
            return p(r, f"I'm after someone for my {t}", f"I need a {self.trade} for my {t}", f"I'd like to get my {t} done")
        if self.casual and c == "au":
            return p(r, f"my {t} has carked it", f"my {t}'s cactus", f"my {t} is playing up", f"my {t}'s on the blink", f"my {t} is stuffed")
        if self.casual:
            return p(r, f"my {t} is on the fritz", f"my {t}'s kaput", f"my {t} has quit on me")
        return p(r, f"my {t} has stopped working", f"there's a problem with my {t}", f"my {t} needs looking at")

    def when(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "this arvo", "tomorrow arvo", "first thing tomorrow", "sometime this week", "before the weekend")
        return p(r, "this afternoon", "tomorrow", "first thing tomorrow", "sometime this week", "as soon as you can")

    def hello(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "G'day, ", "Hey, how ya going, ", "Hi there, ", "Yeah g'day, ")
        if self.casual:
            return p(r, "Hey there, ", "Hi, how's it going, ", "Hey, ")
        return p(r, "Hello, ", "Hi, ", "Good morning, ", "Hi there, ")

    def yes(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "Yeah nah yeah, that works.", "Nah yeah, that's fine.", "Too easy, yep.", "Yeah, righto.", "Yep, sweet as.")
        if self.casual:
            return p(r, "For sure, that works.", "You bet.", "Yeah, that's great.")
        return p(r, "Yes, that works.", "That's fine, thank you.", "Yes please.", "Perfect.")

    def no(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "Yeah, nah, I'm flat out then.", "Nah, that's no good for me.", "Yeah nah, can't do that one.")
        if self.casual:
            return p(r, "Ah, no, I'm swamped then.", "No, that one's no good.")
        return p(r, "No, I can't do that time, sorry.", "That doesn't suit me, I'm afraid.")

    def thanks(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "Cheers mate.", "Too easy, ta.", "Thanks heaps.", "Legend, cheers.")
        if self.casual:
            return p(r, "Thanks a bunch.", "Awesome, thanks.", "Perfect, thanks, eh.")
        return p(r, "Thank you.", "Great, thanks.", "Thanks very much.", "That's perfect, thank you.")

    # ---- Mila ----
    def sorry(self):
        if not self.repair:
            return p(self.r, "Sure, I can help with that. ", "Of course. ", "Happy to help. ", "")
        return p(self.r, "Oh no, sorry to hear that. ", "That's no good, sorry. ", "Sorry about that. ", "Oh, that's a pain. ", "")

    def ok(self):
        r = self.r
        if self.casual and self.c == "au":
            return p(r, "No worries.", "Too easy.", "Easy done.", "Lovely.", "Great.")
        if self.casual:
            return p(r, "For sure.", "No problem at all.", "Great.", "Perfect.")
        return p(r, "Of course.", "Lovely.", "Great.", "Perfect.", "Thanks.")

    def ask_name(self):
        return p(self.r, "Can I grab your name?", "Who am I speaking with?", "What's your name, please?", "Can I take a name for the booking?", "And your name is?")

    def ask_num(self):
        o = self.owner
        return p(self.r, "What's the best number to reach you on?", f"What number should {o} call?", "And a contact number?",
                 "Can I get a phone number for you?", "What's the best number for you?")

    def ask_addr(self):
        return p(self.r, "What's the address?", "Where are you located?", "And the address for the job?", "Whereabouts are you?")

    def read_num(self):
        n = self.num
        return p(self.r, f"So that's {n}.", f"Let me read that back: {n}.", f"Got it, {n}.", f"That's {n}, is that right?", f"{n}, thanks.")

    def close(self, what):
        o, n = self.owner, self.name
        welcome = ("No worries at all" if self.casual and self.c == "au" else "No problem at all" if self.casual else "You're welcome")
        return p(self.r, f"{welcome}, {n}. {what}", f"{welcome}. {what} Thanks for calling, {n}.", f"Thanks {n}. {what}")

    def system(self):
        text = ShopCard(self.card).instructions()
        if self.card.get("bookings") == "book":
            if self.diary:
                text += "\n- Free spots in the diary: " + "; ".join(f"{d} {t}" for d, t in self.slots) + ". Offer only these."
            else:
                text += f"\n- You can't see the diary right now. Ask what day suits and say {self.owner} will confirm the time."
        return text


def gather(x, have: set, want: list) -> list:
    """Collect the details still missing, in a random order, reading the number back."""
    r, turns, lead = x.r, [], x.ok()
    todo = [w for w in want if w not in have]
    r.shuffle(todo)
    for item in todo:
        if item == "name":
            turns += [("assistant", f"{lead} {x.ask_name()}"), ("user", p(r, f"It's {x.name}.", f"{x.name}.", f"Yeah, {x.name}.", f"My name's {x.name}."))]
            lead = f"Thanks {x.name}."
        elif item == "addr":
            turns += [("assistant", f"{lead} {x.ask_addr()}"), ("user", p(r, f"{x.addr}.", f"It's {x.addr}.", f"I'm at {x.addr}."))]
            lead = p(r, f"{x.addr}, got it.", "Got it.", "Thanks.")
        else:
            turns += [("assistant", f"{lead} {x.ask_num()}"), ("user", p(r, f"{x.num}.", f"It's {x.num}.", f"Best one is {x.num}."))]
            lead = x.read_num()
    return turns, lead


def opener_extras(x):
    """Sometimes the caller gives their name or number straight away."""
    r, have, said = x.r, set(), ""
    if r.random() < 0.35:
        have.add("name")
        said = p(r, f"it's {x.name} here, ", f"{x.name} speaking, ", f"my name's {x.name}, ")
    return have, said


def flow_booking(x):
    r = x.r
    have, said = opener_extras(x)
    (d1, t1), (d2, t2) = x.slots[0], x.slots[1]
    turns = [("user", f"{x.hello()}{said}{x.problem()}, " + p(r, f"reckon someone could come {x.when()}?" if x.casual and x.c == "au" else f"could someone come {x.when()}?",
                                                               f"any chance of getting {x.owner} out {x.when()}?", f"can I book someone in for {x.when()}?")),
             ("assistant", x.sorry() + p(r, f"The next spot {x.owner} has is {d1} at {t1}. Would that suit?", f"I can get {x.owner} to you {d1} at {t1}. Does that work?",
                                         f"{x.owner}'s next free time is {d1} at {t1}. How does that sound?"))]
    day, time = d1, t1
    if r.random() < 0.3:
        day, time = d2, t2
        turns += [("user", x.no()), ("assistant", p(r, f"No problem. How about {d2} at {t2} instead?", f"That's okay. There's also {d2} at {t2}. Would that be better?")),
                  ("user", x.yes())]
    else:
        turns.append(("user", x.yes()))
    want = ["name", "num"] + (["addr"] if x.trade not in ("dog groomer", "mechanic") else [])
    more, lead = gather(x, have, want)
    turns += more
    turns += [("assistant", f"{lead} " + p(r, f"So that's {x.owner} coming {day} at {time}. Anything else I can help with?",
                                           f"You're booked in for {day} at {time}. Is there anything else?", f"I've got you down for {day} at {time}. Anything else you need?")),
              ("user", p(r, "No, that's all. ", "Nah, all good. " if x.c == "au" else "No, that's it. ", "That's everything. ") + x.thanks()),
              ("assistant", x.close(f"{x.owner} will see you {day}."))]
    return turns


def flow_no_diary(x):
    x.diary = False
    r = x.r
    have, said = opener_extras(x)
    turns = [("user", f"{x.hello()}{said}{x.problem()}, can someone come {x.when()}?"),
             ("assistant", x.sorry() + p(r, f"I can't see the diary just now, so I can't promise a time. What day would suit you best, and I'll have {x.owner} confirm it?",
                                         f"I don't have the diary in front of me, so I won't guess a time. Which day works for you? {x.owner} will confirm it with you.")),
             ("user", p(r, "Thursday would be good.", "Any morning this week.", "Friday if you can.", "Tomorrow if possible."))]
    more, lead = gather(x, have, ["name", "num"])
    turns += more + [("assistant", f"{lead} " + p(r, f"I'll pass that to {x.owner}, and they'll call to confirm the time.", f"{x.owner} will ring you to lock in a time."))]
    return turns


def flow_message_only(x):
    x.card["bookings"] = "message"
    r = x.r
    turns = [("user", f"{x.hello()}can I book someone in? {x.problem().capitalize()}."),
             ("assistant", x.sorry() + p(r, f"I can't book it in myself, but I'll get {x.owner} to call you back and sort out a time.",
                                         f"{x.owner} does the bookings personally, so I'll have them ring you back.") + " " + x.ask_name()),
             ("user", f"{x.name}.")]
    more, lead = gather(x, {"name"}, ["num"])
    more[0] = ("assistant", f"Thanks {x.name}. {x.ask_num()}")
    turns += more + [("assistant", f"{lead} " + p(r, f"I'll let {x.owner} know it's about your {x.thing}. They'll call you back today.",
                                                  f"I'll pass on that it's your {x.thing}, and {x.owner} will be in touch soon."))]
    return turns


def flow_callback_one_line(x):
    """Caller gives name and number in one breath: read the number back, don't ask again."""
    r, o = x.r, x.owner
    turns = [("user", p(r, f"Can you get {o} to call me back? It's {x.name}, {x.num}.", f"Just get {o} to ring me, {x.name} on {x.num}.",
                        f"{x.hello()}it's {x.name}. Can {o} call me on {x.num}?")),
             ("assistant", p(r, f"Of course, {x.name}. {x.read_num()} Is there a message you'd like me to pass on?",
                             f"Sure, {x.name}. {x.read_num()} What should I tell {o} it's about?",
                             f"No problem, {x.name}. {x.read_num()} Anything you'd like {o} to know before calling?")),
             ("user", p(r, f"Just that it's about my {x.thing}.", "Nah, all good." if x.c == "au" else "No, that's all.", f"Tell them it's about the quote."))]
    turns.append(("assistant", p(r, f"Will do. {o} will call you back as soon as they're free.", f"I'll pass that on now. {o} will be in touch soon.")))
    return turns


def flow_price_unknown(x):
    r, o = x.r, x.owner
    ask = p(r, f"How much do you reckon it'd be to fix my {x.thing}?" if x.c == "au" else f"What would it run me to sort out my {x.thing}?",
            f"What do you charge for {x.service}?", f"Can you give me a rough price for my {x.thing}?", "What's your hourly rate?")
    turns = [("user", ask),
             ("assistant", p(r, f"I don't have prices here, and I don't want to guess and get it wrong. I can have {o} call you back with a proper price. Would that help?",
                             f"I can't give you a figure, sorry, I'd only be guessing. {o} can call you back with a real price. Shall I arrange that?",
                             f"That's one for {o}, since it depends on the job. Can I get them to call you back with a price?")),
             ("user", x.yes())]
    more, lead = gather(x, set(), ["name", "num"])
    turns += more + [("assistant", f"{lead} I'll get {o} to ring you with a price today.")]
    return turns


def flow_price_allowed(x):
    r, o = x.r, x.owner
    fee = p(r, "$80", "$90", "$110", "$120")
    x.card["prices"] = {"call-out fee": fee}
    return [("user", p(r, f"What do you charge to come and look at my {x.thing}?", "Is there a call-out fee?", "What's it cost just to come out?")),
            ("assistant", p(r, f"The call-out fee is {fee}. Anything beyond that depends on what {o} finds, and they'd tell you before starting.",
                            f"It's {fee} for the call-out. {o} would give you a price for the rest once they've had a look.")),
            ("user", p(r, "And roughly how much to fix it?", "What about the repair itself?", "Any idea what the whole job would be?")),
            ("assistant", p(r, f"I can't give you a figure for that, sorry, I'd only be guessing. Would you like {o} to call you back, or shall I book a time?",
                            f"That part I don't know, and I won't guess. {o} can tell you once they've seen it. Would you like to book a time?"))]


def flow_not_offered(x):
    r, o = x.r, x.owner
    thing = p(r, "roofing", "tiling", "painting", "asbestos removal", "pest control")
    x.card["not_offered"] = [thing, p(r, "insurance work", "commercial jobs")]
    return [("user", p(r, f"Do you guys do {thing} as well?", f"Can {o} do {thing}?", f"I'm also after someone for {thing}, do you do that?")),
            ("assistant", p(r, f"Sorry, {thing} isn't something {o} does. Is there anything else I can help with?",
                            f"No, sorry, {o} doesn't do {thing}. Can I help with anything else?")),
            ("user", p(r, "Nah, that was it, cheers." if x.c == "au" else "No, that was it, thanks.", "No, that's all.")),
            ("assistant", p(r, "No worries, thanks for calling." if x.casual and x.c == "au" else "No problem, thanks for calling.", "Thanks for calling. Have a good day."))]


def flow_unknown_service(x):
    r, o = x.r, x.owner
    thing = p(r, "paving", "gutter cleaning", "rubbish removal", "after-hours work", "jobs out past the airport")
    turns = [("user", p(r, f"Do you do {thing}?", f"Would {o} be able to help with {thing}?")),
             ("assistant", p(r, f"I'm not sure, to be honest, and I'd hate to tell you wrong. I can ask {o} and have them call you back. Would that help?",
                             f"I don't know that one, sorry. Let me get {o} to call you back with a proper answer. Is that okay?")),
             ("user", x.yes())]
    more, lead = gather(x, set(), ["name", "num"])
    return turns + more + [("assistant", f"{lead} {o} will call you back about the {thing}.")]


def flow_closed_day(x):
    r, o = x.r, x.owner
    x.card["open_days"] = WEEKDAYS
    d, t = x.slots[0]
    return [("user", p(r, "Any chance someone could come out Sunday?", "Can you do Saturday arvo?" if x.c == "au" else "Can you do Saturday afternoon?", "Are you open on the weekend?")),
            ("assistant", p(r, f"Sorry, {o} doesn't work weekends. The next spot is {d} at {t}. Would that suit?",
                            f"{o} only works Monday to Friday, sorry. I do have {d} at {t}. Would that work?")),
            ("user", x.yes()),
            ("assistant", f"{x.ok()} I'll put you down for {d} at {t}. {x.ask_name()}")]


def flow_misheard(x):
    r = x.r
    return [("user", f"Yeah it's {x.name}, I'm at... [unclear] ...{x.addr.split()[-1]}, can you send someone?"),
            ("assistant", p(r, f"Sorry {x.name}, the line dropped out for a second. Could you give me the address once more?",
                            f"Sorry {x.name}, I missed part of that. What was the street name again?")),
            ("user", f"{x.addr}."),
            ("assistant", p(r, f"Got it, {x.addr}. And what do you need a hand with?", f"{x.addr}, thanks. What's the job?"))]


def flow_urgent(x):
    r, o = x.r, x.owner
    x.card["emergencies"] = f"If it's urgent, take the address and number and say {o} will ring within fifteen minutes."
    urgent = {"plumber": "there's water pouring through my ceiling", "electrician": "the power's out and something smells like burning",
              "heating technician": "the furnace is out and it's freezing"}.get(x.trade, f"it's urgent, my {x.thing} can't wait")
    turns = [("user", f"{x.hello()}{urgent}!"),
             ("assistant", p(r, "That sounds urgent, let's get this sorted. What's the address?", "Okay, I'll get onto this straight away. Where are you?")),
             ("user", f"{x.addr}.")]
    more, lead = gather(x, {"addr", "name"}, ["num"])
    more[0] = ("assistant", f"{x.addr}, got it. {x.ask_num()}")
    return turns + more + [("assistant", f"{lead} {o} will ring you within fifteen minutes.")]


FLOWS = [(flow_booking, 6), (flow_no_diary, 2), (flow_message_only, 2), (flow_callback_one_line, 3), (flow_price_unknown, 3),
         (flow_price_allowed, 2), (flow_not_offered, 2), (flow_unknown_service, 2), (flow_closed_day, 2), (flow_misheard, 1), (flow_urgent, 2)]


def make(count: int, seed: int = 11, au_share: float = 0.75) -> list[dict]:
    r = random.Random(seed)
    flows = [f for f, w in FLOWS for _ in range(w)]
    rows, seen = [], set()
    while len(rows) < count:
        x = Ctx(r, "au" if r.random() < au_share else "ca")
        turns = r.choice(flows)(x)
        key = json.dumps(turns)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"messages": [{"role": "system", "content": x.system()}] + [{"role": a, "content": b} for a, b in turns]})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data-v3")
    ap.add_argument("--count", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = make(args.count, args.seed)
    cut = max(1, len(rows) // 10)
    for name, part in (("valid.jsonl", rows[:cut]), ("train.jsonl", rows[cut:])):
        path = out / name
        if path.exists():
            raise SystemExit(f"{path} already exists. Pick a new --out folder so nothing is overwritten.")
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in part))
        print(f"wrote {len(part):5} calls -> {path}")


if __name__ == "__main__":
    main()
