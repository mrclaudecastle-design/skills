#!/usr/bin/env python3
"""turn: joins the small nodes into one step of a call.

Text in, text out, so the whole conversation logic can be tried and tested
without any voice models. In the live call, the ears feed `heard`, the
brain supplies `brain_reading` and the reply text, and the voice reads `say`.

    from turn import Call
    call = Call(country="au")
    out = call.hear([("thursday at two", 0.6), ("tuesday at two", 0.3)], brain_reading="thursday at two")
    out.action -> "act" | "confirm" | "ask_again" | "read_back" | "keypad" | "take_message"
    out.say    -> what Mila says next, already in spoken form
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import PHONE, guard, is_urgent, spoken_numbers     # noqa: E402
from lingo import mirror, understand          # noqa: E402
from plausibility import Vote, decide         # noqa: E402
from repair import handle_key, next_step      # noqa: E402
from say_it import say_it                     # noqa: E402


@dataclass
class Out:
    action: str
    say: str | None = None          # None on "act": the brain writes the reply
    meaning: str | None = None      # what Mila believes the caller meant, in plain words
    confidence: float = 0.0
    signals: set = field(default_factory=set)
    keys: dict = field(default_factory=dict)


class Call:
    def __init__(self, country: str = "au", checks=(), card=None, today: str | None = None):
        # Pass a ShopCard and the country and sanity checks come from the shop's own answers.
        self.country = card.country if card else country
        self.checks = list(checks) + (card.checks() if card else [])
        self.card = card
        self.today = today          # today's weekday name, so "tomorrow at 2pm" can be checked against the diary
        self.misses = 0             # misunderstandings in a row on the current detail
        self.caller_casual = False  # has the caller used everyday local talk yet?
        self.pending = None         # a reading waiting for a yes or no
        self.keys = {}              # live keypad choices, if any
        self.guesses = []           # readings still in the running for this detail
        self.have_number = False    # has the caller given a phone number yet?
        self.last_heard = ""        # the caller's latest line, as best heard
        self.urgent = False         # has the caller described an emergency?
        self.all_heard = ""         # everything the caller has said so far
        self.last_spoken = ""       # Mila's previous reply

    def hear(self, heard: list[tuple[str, float]], brain_reading: str | None = None,
             brain_weight: float = 0.8, topic: str = "that") -> Out:
        """heard = the ears' guesses, best first, each with a 0 to 1 trust score."""
        heard = _clean_guesses(heard)
        self.last_heard = heard[0][0] if heard else ""
        self.urgent = self.urgent or is_urgent(self.last_heard)
        votes, signals = [], set()
        for i, (text, weight) in enumerate(heard):
            u = understand(text, self.country)
            if i == 0:
                signals = u["signals"]
            self.caller_casual = self.caller_casual or u["casual"]
            votes.append(Vote(u["plain"], weight, f"ears-{i + 1}"))
        if brain_reading:
            votes.append(Vote(understand(brain_reading, self.country)["plain"], brain_weight, "brain"))

        # A plain yes or no settles a reading Mila just read back.
        if self.pending and signals & {"yes", "no"} or self.pending and _yes_no(heard):
            answer = "yes" if "yes" in signals or _yes_no(heard) == "yes" else "no"
            return self._settle(answer, topic, signals)

        r = decide(votes, self.checks)
        self.guesses = [g for g in [r.value, *r.runners_up] if g]
        if r.action == "act":
            self.misses, self.pending = 0, None
            return Out("act", None, r.value, r.confidence, signals)
        if r.action == "confirm":
            self.pending = r.value
            return Out("confirm", say_it(f"Just checking I've got it right. Was that {r.value}?"),
                       r.value, r.confidence, signals)
        return self._repair(self.guesses, topic, r.confidence, signals)

    def press(self, digit: str) -> Out:
        """The caller pressed a key after a keypad question."""
        if not self.keys:                       # no keypad question is open: treat it as a missed line
            return self._repair([], "that", 0.0, set())
        choice = handle_key(str(digit if digit is not None else ""), self.keys)
        if choice == "invalid":
            return Out("keypad", "Sorry, I didn't catch that key. " + self._keypad_line(), keys=self.keys)
        self.keys = {}
        if choice is None:
            self.misses += 1
            return self._repair([], "that", 0.0, set())
        self.misses, self.pending = 0, None
        return Out("act", None, choice, 1.0)

    def speak(self, brain_reply: str, diary=None, today: str | None = None) -> Out:
        """Run the brain's reply through the safety net, then into spoken form."""
        g = guard(str(brain_reply or ""), self.last_heard, self.card, diary, self.have_number, self.urgent, self.all_heard, self.last_spoken,
                  today or self.today)
        self.all_heard += " " + self.last_heard
        self.last_spoken = g.text
        # A number said in words ("oh four one two...") counts as given, the same as one in digits.
        self.have_number = self.have_number or bool(PHONE.search(spoken_numbers(self.last_heard)))
        self.last_heard = ""        # this line has been answered; don't read its number back twice
        return Out("say", say_it(g.text), signals=set(g.fixes))

    def ok(self) -> str:
        """A short acknowledgement. Local only if the caller was casual first."""
        return mirror("ok", self.country, self.caller_casual) or "Of course."

    def _settle(self, answer, topic, signals):
        value, self.pending = self.pending, None
        if answer == "yes":
            self.misses = 0
            return Out("act", None, value, 1.0, signals)
        # She got it wrong: drop that reading and try what's left, one rung up the ladder.
        self.misses = max(self.misses, 1)
        self.guesses = [g for g in self.guesses if g != value]
        return self._repair(self.guesses, topic, 0.0, signals)

    def _repair(self, guesses, topic, confidence, signals):
        step = next_step(self.misses, guesses, topic)
        self.misses += 1
        self.keys = step.keys
        self.pending = guesses[0] if step.action == "read_back" else None
        return Out(step.action, say_it(step.say), guesses[0] if guesses else None, confidence, signals, step.keys)

    def _keypad_line(self):
        parts = [f"press {k} for {v}" if v else f"press {k} if it's something else" for k, v in self.keys.items()]
        return say_it(", ".join(parts).capitalize() + ".")


def _clean_guesses(heard) -> list[tuple[str, float]]:
    """The ears' guesses with anything unusable dropped: no text, or a trust score that isn't a number."""
    out = []
    for item in heard or []:
        try:
            text, weight = item[0], float(item[1])
        except (TypeError, ValueError, IndexError):
            continue
        if isinstance(text, str) and text.strip() and weight == weight:
            out.append((text, max(0.0, min(1.0, weight))))
    return out


def _yes_no(heard):
    first = heard[0][0].lower().strip(" .!,") if heard else ""
    if first in {"yes", "yep", "yeah", "yup", "that's right", "correct", "that's it", "yes please"}:
        return "yes"
    if first in {"no", "nope", "nah", "that's wrong", "not quite"}:
        return "no"
    return None


if __name__ == "__main__":
    call = Call("au")
    script = [
        ("Clear line", [("can you come thursday at two", 0.9), ("can you come thursday at two", 0.5)], "can you come thursday at two"),
        ("Noisy line", [("thursday arvo at two", 0.5), ("tuesday arvo at two", 0.45)], None),
        ("Caller", [("nah yeah thursday", 0.9)], None),
        ("Very bad line", [("...day at ...", 0.2), ("someday at who", 0.15)], None),
        ("Still bad", [("thursday at ten", 0.3), ("tuesday at two", 0.28), ("thursday at two", 0.2)], None),
        ("Caller", [("no", 0.9)], None),
    ]
    for label, heard, brain in script:
        out = call.hear(heard, brain, topic="the day")
        print(f"{label}: caller ~ {heard[0][0]!r}\n   [{out.action}, sure {out.confidence}] {out.say or '(carry on: ' + str(out.meaning) + ')'}")
    out = call.press("1")
    print(f"Caller presses 1\n   [{out.action}] (carry on: {out.meaning})   Mila: {call.ok()}")
