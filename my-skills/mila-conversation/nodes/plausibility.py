#!/usr/bin/env python3
"""plausibility: several small voters decide what the caller most likely meant.

Each voter gives one reading and how much it trusts it. Voters can be the
ears' top guesses, the brain's reading, or a plain rule. Sanity checks then
knock down readings that make no sense for this shop (closed that day, time
already gone, phone number too short). The result is the winning reading,
how sure Mila is (0 to 1), and what she should do next.

    from plausibility import Vote, decide
    result = decide([Vote("thursday 2pm", 0.6, "ears-1"),
                     Vote("tuesday 2pm", 0.3, "ears-2"),
                     Vote("thursday 2pm", 0.8, "brain")])
    result.action  -> "act" | "confirm" | "repair"
"""
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

ACT_AT = 0.80      # sure enough to carry on without asking
CONFIRM_AT = 0.50  # fairly sure: read it back to the caller first


@dataclass
class Vote:
    value: str            # the reading, e.g. "thursday 2pm"
    weight: float = 1.0   # how much this voter trusts it, 0 to 1
    source: str = ""      # who voted: "ears-1", "brain", "rule"


@dataclass
class Result:
    value: str | None
    confidence: float
    action: str                       # "act", "confirm" or "repair"
    runners_up: list = field(default_factory=list)   # other readings, best first
    tally: dict = field(default_factory=dict)


def _key(value: str) -> str:
    return " ".join(str(value).lower().split())


def _trust(weight, default: float = 0.0) -> float:
    """A weight or a check's answer as a number from 0 to 1. Anything unreadable counts as `default`."""
    try:
        w = float(weight)
    except (TypeError, ValueError):
        return default
    if math.isnan(w):
        return default
    return max(0.0, min(1.0, w))


def decide(votes: list[Vote], checks: list[Callable[[str], float]] = (),
           act_at: float = ACT_AT, confirm_at: float = CONFIRM_AT) -> Result:
    """Tally the votes, apply sanity checks, and say what to do next."""
    tally, shown = defaultdict(float), {}
    for v in votes:
        if v.value is None or not str(v.value).strip():
            continue
        k = _key(v.value)
        tally[k] += _trust(v.weight)
        shown.setdefault(k, v.value)
    # Each check returns 0 (impossible) to 1 (fine) and scales that reading.
    for k in list(tally):
        for check in checks:
            try:                                   # a broken check has no say; it must never end the call
                tally[k] *= _trust(check(str(shown[k])), 1.0)
            except Exception:
                pass
    total = sum(tally.values())
    if total <= 0:
        return Result(None, 0.0, "repair", [], dict(tally))
    ranked = sorted(tally.items(), key=lambda kv: -kv[1])
    best, score = ranked[0]
    confidence = round(score / total, 3)
    # One voter alone can't be fully sure, however confident it sounds.
    backing = [_trust(v.weight) for v in votes if v.value is not None and str(v.value).strip() and _key(v.value) == best]
    if len(backing) == 1:
        confidence = min(confidence, backing[0])
    action = "act" if confidence >= act_at else "confirm" if confidence >= confirm_at else "repair"
    return Result(shown[best], round(confidence, 3), action,
                  [shown[k] for k, s in ranked[1:] if s > 0], {shown[k]: round(s, 3) for k, s in ranked})


# A few ready-made sanity checks. Add shop-specific ones the same way.
def phone_has_enough_digits(value: str) -> float:
    d = "".join(c for c in str(value) if c.isdigit())
    n = len(d)
    ok = n in (8, 10) or (n == 11 and d.startswith(("61", "1"))) or (n == 12 and d.startswith("610"))   # +61 4.., +1 604.., +61 (0)4..
    return 1.0 if ok else 0.2


def within_opening_days(open_days: set[str]) -> Callable[[str], float]:
    days = "monday tuesday wednesday thursday friday saturday sunday".split()
    short = {"mon": "monday", "tue": "tuesday", "tues": "tuesday", "wed": "wednesday", "thu": "thursday", "thur": "thursday",
             "thurs": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}
    open_days = {str(d).lower() for d in open_days}

    def check(value: str) -> float:
        words = re.findall(r"[a-z]+", str(value).lower())
        named = [short.get(w, w) for w in words if short.get(w, w) in days]
        return 1.0 if not named or any(d in open_days for d in named) else 0.1
    return check


if __name__ == "__main__":
    votes = [Vote("Thursday 2pm", 0.6, "ears-1"), Vote("Tuesday 2pm", 0.35, "ears-2"), Vote("thursday 2pm", 0.8, "brain")]
    print(decide(votes))
    print(decide([Vote("Sunday 2pm", 0.7, "ears-1"), Vote("Monday 2pm", 0.4, "ears-2")],
                 checks=[within_opening_days({"monday", "tuesday", "wednesday", "thursday", "friday"})]))
