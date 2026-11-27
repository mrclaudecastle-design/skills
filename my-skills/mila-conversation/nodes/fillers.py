#!/usr/bin/env python3
"""fillers: the small sounds that make a call feel like a person is there.

Listening sounds while the caller talks at length, and a holding line when
a lookup takes a moment. Never the same one twice in a row.

    from fillers import Fillers
    f = Fillers()
    f.listening()          -> "Mm-hm."
    f.holding("diary")     -> "Let me check the diary for you."
"""
import random

LISTENING = ["Mm-hm.", "Yep.", "Right.", "Okay.", "Got it."]
HOLDING = {
    "diary": ["Let me check the diary for you.", "One sec, I'll have a look at the diary.", "Bear with me, just checking what's free."],
    "price": ["Let me check that for you.", "One moment, I'll look that up."],
    "any": ["One moment.", "Bear with me a sec.", "Let me check that for you."],
}
# Only worth saying a holding line if the wait will be felt.
HOLD_AFTER_MS = 700


class Fillers:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.last = {}

    def _pick(self, key, options):
        choices = [o for o in options if o != self.last.get(key)] or options
        self.last[key] = self.rng.choice(choices)
        return self.last[key]

    def listening(self) -> str:
        return self._pick("listening", LISTENING)

    def holding(self, what: str = "any", expected_wait_ms: float = HOLD_AFTER_MS) -> str | None:
        if expected_wait_ms is not None and expected_wait_ms < HOLD_AFTER_MS:
            return None
        return self._pick("holding", HOLDING.get(what, HOLDING["any"]))


if __name__ == "__main__":
    f = Fillers()
    print([f.listening() for _ in range(4)])
    print(f.holding("diary"), "|", f.holding("price", 200))
