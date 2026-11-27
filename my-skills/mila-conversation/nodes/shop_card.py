#!/usr/bin/env python3
"""shop_card: turn a new shop's answered questionnaire into a ready Mila.

One Mila, trained once as a receptionist. Each shop is a small card of
answers, not a new training run. This node reads the answers, fills the
gaps with safe defaults, and produces what the rest of the kit needs:
her instructions for this shop, the greeting, the country for lingo, and
the sanity checks for the voting node (such as the days the shop works).

    from shop_card import ShopCard
    card = ShopCard.load("shop/examples/birch-and-co.json")
    card.missing()        -> []            (anything she can't start without)
    card.instructions()   -> the text given to the brain for every call
    card.checks()         -> [checks for plausibility.decide]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plausibility import within_opening_days   # noqa: E402
from guard import HUMAN_CLAIM, day_list, price_table   # noqa: E402

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "shop" / "questionnaire.json").read_text())["questions"]
COUNTRIES = {"au": "Australia", "ca": "Canada"}

# The receptionist manners every shop gets. This is the part she is trained on.
MANNERS = ("You are on a live phone call, so speak the way people talk: one or two short sentences, "
           "one question at a time, no lists. Understand everyday local expressions and go along with them warmly, "
           "but don't start using slang yourself. Read names, numbers, days and times back to confirm them. "
           "When you read back an address, say every number the caller gave (unit and street number) and the street, exactly as they said them. "
           "Never invent a price, a time or a promise. When a day or time is needed, offer a free spot from the diary rather than asking "
           "what time suits. Once the caller picks a spot, read back the day, time, their name, address and number in one go, and "
           "book it only when they say yes to that. Don't say anyone will confirm it later. Don't say when someone will call or arrive unless these notes say so. Don't say goodbye until you have "
           "the caller's name and number. Only say you'll pass on a message if the caller gave you one. "
           "End naturally, the way a person would on the phone, without sign-offs like 'let me know if you need anything else'.")


def _listed(items) -> str:
    items = [str(i) for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class ShopCard:
    def __init__(self, answers: dict):
        answers = answers if isinstance(answers, dict) else {}
        self.given = {k: v for k, v in answers.items() if v not in (None, "", [], {})}
        self.problems = []                      # answers she couldn't make sense of, in the owner's words
        self._tidy()
        self.a = {q["id"]: q["default"] for q in QUESTIONS if "default" in q}
        self.a.update(self.given)

    def _tidy(self):
        """Owners type answers every which way. Put each one into the shape the rest of the kit expects,
        and note the ones that can't be read rather than guessing."""
        g, asks = self.given, {q["id"]: q["ask"] for q in QUESTIONS}
        for key in ("shop_name", "trade", "owner_name", "area", "open_hours", "emergencies", "greeting", "extra"):
            if key in g and not isinstance(g[key], str):
                g[key] = ", ".join(str(x) for x in g[key]) if isinstance(g[key], (list, tuple)) else str(g[key])
            if key in g:
                g[key] = re.sub(r"[\x00-\x1f]+", " ", g[key]).strip()
                if not g[key]:
                    del g[key]
        for key in ("country", "bookings"):
            if key in g:
                g[key] = str(g[key]).strip().lower()
        if "country" in g:
            g["country"] = {"australia": "au", "aus": "au", "canada": "ca", "can": "ca"}.get(g["country"], g["country"])
        if "open_days" in g:
            days = day_list(g["open_days"])
            if days:
                g["open_days"] = days
            else:
                self.problems.append(f"{asks['open_days']} (I couldn't read the days, please list them, like Monday to Friday)")
                del g["open_days"]
        for key in ("services", "not_offered"):
            if key in g and isinstance(g[key], str):
                g[key] = [x.strip() for x in re.split(r",|;|\n|\band\b", g[key]) if x.strip()]
            elif key in g and isinstance(g[key], (list, tuple, set)):
                g[key] = [str(x).strip() for x in g[key] if str(x).strip()]
            elif key in g:
                del g[key]
        if "prices" in g:
            table = price_table({"prices": g["prices"]})
            if isinstance(g["prices"], dict) and all(table.get(str(k)) for k in g["prices"]):
                g["prices"] = {str(k): str(v) for k, v in g["prices"].items()}
            elif table and all(table.values()) and not isinstance(g["prices"], dict):
                raw = g["prices"] if isinstance(g["prices"], (list, tuple, set)) else [x for x in re.split(r"[;\n]|,(?!\d{3})", str(g["prices"])) if x.strip()]
                g["prices"] = dict(zip(table, (re.search(r"(?:AU|CA|US|NZ|A|C)?\$?\s?\d[\d,]*(?:\.\d{1,2})?", str(x)).group(0).strip() for x in raw)))
                g["prices"] = {k: (v if v.startswith(("$", "A", "C", "U", "N")) else "$" + v) for k, v in g["prices"].items()}
            else:                               # a price she can't read is a price she must never say
                self.problems.append(f"{asks['prices']} (I couldn't read these, so I won't say any price until they're fixed. Write each as: what it's for, then the amount)")
                del g["prices"]

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def missing(self) -> list[str]:
        """Questions that must be answered before Mila can take calls, in the owner's words."""
        problems = [q["ask"] for q in QUESTIONS if q.get("need") and q["id"] not in self.given]
        for q in QUESTIONS:
            value = self.given.get(q["id"])
            if value is not None and "choices" in q and value not in q["choices"]:
                problems.append(f"{q['ask']} (pick one of: {', '.join(q['choices'])})")
        return problems

    def warnings(self) -> list[str]:
        """Answers she couldn't read, for the owner to fix. They don't stop her taking calls:
        she falls back to the safe choice (no prices said, the usual working days)."""
        return list(self.problems)

    @property
    def country(self) -> str:
        return self.a.get("country", "au")

    def greeting(self) -> str:
        name = str(self.a.get("shop_name", ""))
        default = next(q["default"] for q in QUESTIONS if q["id"] == "greeting")
        template = str(self.a.get("greeting") or default)
        if HUMAN_CLAIM.search(template) or re.search(r"\b(?:not|isn't|no) (?:an? )?(?:AI|robot|bot|machine|computer)\b", template, re.I) \
                or re.search(r"[{}]", template.replace("{shop_name}", "")):
            template = default                 # a greeting may never say she's a person, and odd blanks aren't read out
        mark = "\x00"
        rest = template.replace("{shop_name}", mark)           # only that one blank is filled; nothing else is run
        rest = re.sub(r"\{[^{}]*\}", "", rest).replace("{", "").replace("}", "")
        rest = re.sub(r"\s{2,}", " ", rest).strip()
        # Callers are always told she's an AI, whatever the shop wrote. "AI" in the shop's own name doesn't count.
        if not re.search(r"\bAI\b|\bartificial intelligence\b", rest):
            rest = re.sub(r"\bMila\b", "Mila, the AI receptionist", rest, count=1) if re.search(r"\bMila\b", rest) \
                else rest.rstrip() + " This is Mila, the AI receptionist."
        return re.sub(r"^[\s,.]+", "", rest.replace(mark, name)).strip()

    def checks(self) -> list:
        """Sanity checks for the voting node, built from this shop's answers."""
        days = {d.lower() for d in self.a.get("open_days", [])}
        return [within_opening_days(days)] if days else []

    def instructions(self) -> str:
        if self.missing():
            raise ValueError("Not ready: " + "; ".join(self.missing()))
        a, owner = self.a, self.a["owner_name"]
        lines = [f"You are Mila, the receptionist for {a['shop_name']}, a {a['trade']} in {COUNTRIES.get(self.country, self.country)}. "
                 f"{owner} is on a job and can't answer.", MANNERS,
                 f"If you don't know, say so and offer to have {owner} call back.", "", "About this business:"]
        if a.get("area"):
            lines.append(f"- Covers: {a['area']}.")
        lines.append(f"- Works {_listed([d.capitalize() for d in a['open_days']])}, {a['open_hours']}. Never offer a time outside these.")
        if a.get("services"):
            lines.append(f"- Main jobs: {_listed(a['services'])}.")
        if a.get("not_offered"):
            lines.append(f"- Does not do: {_listed(a['not_offered'])}. Say so kindly.")
        if a.get("prices"):
            lines.append("- Prices you may say, and no others: " + "; ".join(f"{k} {v}" for k, v in a["prices"].items())
                         + f". For the cost of a job itself, say it depends on the job and offer a call back from {owner}.")
        else:
            lines.append(f"- You have no prices. For any price question, offer a call back from {owner}.")
        lines.append(f"- For a call back you only need the caller's name, number and what it's about. Don't ask for an address "
                     f"and don't book the call back into the diary; {owner} rings back as soon as possible.")
        lines.append(f"- Don't talk about who else works here. If asked to recommend another business, say kindly you can't, "
                     f"and don't offer a call back for it.")
        lines.append("- You can book jobs into the diary." if a["bookings"] == "book"
                     else f"- You don't book jobs. Take the caller's name, number and what they need, and say {owner} will call back.")
        lines.append(f"- Urgent calls: {a['emergencies']}")
        if a.get("extra"):
            lines.append(f"- Also: {a['extra']}")
        return "\n".join(lines)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    card = ShopCard.load(sys.argv[1] if len(sys.argv) > 1 else here / "shop" / "examples" / "birch-and-co.json")
    print("Still needed:", card.missing() or "nothing, ready to take calls")
    print("Greeting:", card.greeting(), "\n")
    print(card.instructions())
