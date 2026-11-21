#!/usr/bin/env python3
"""repair: what Mila does when she and the caller aren't understanding each other.

A short ladder, so nobody gets stuck repeating themselves:
  step 1  say her best guess back and ask if that's right
  step 2  second approach: "press 1 if you meant X, 2 if you meant Y"
  step 3  stop trying, take a message and promise a call back

    from repair import next_step, handle_key
    step = next_step(misses=2, guesses=["Thursday at 2", "Tuesday at 2"])
    step.say     -> "Sorry, let's make this easy. Press 1 for Thursday at 2, ..."
    handle_key("1", step.keys) -> "Thursday at 2"
"""
from dataclasses import dataclass, field

MAX_KEY_CHOICES = 3


@dataclass
class Step:
    action: str                 # "ask_again", "read_back", "keypad" or "take_message"
    say: str
    keys: dict = field(default_factory=dict)   # which key means which reading


def next_step(misses: int, guesses: list[str] = (), topic: str = "that") -> Step:
    """misses = how many times in a row this detail has gone wrong."""
    guesses = [g for g in guesses if g][:MAX_KEY_CHOICES]
    if misses <= 0 or not guesses:
        if misses >= 2:
            return _take_message()
        return Step("ask_again", f"Sorry, I missed {topic}. Could you say it once more for me?")
    if misses == 1:
        return Step("read_back", f"Just checking I've got it right. Was that {guesses[0]}?")
    if misses == 2:
        keys = {str(i + 1): g for i, g in enumerate(guesses)}
        parts = [f"press {k} for {g}" for k, g in keys.items()]
        other = str(len(keys) + 1)
        keys[other] = None
        choices = ", ".join(parts) + f", or press {other} if it's something else"
        return Step("keypad", f"Sorry about that, let's make it easy. On your keypad, {choices}.", keys)
    return _take_message()


def handle_key(digit: str, keys: dict):
    """Returns the chosen reading, None for 'something else', or 'invalid'."""
    return keys.get(digit.strip(), "invalid") if digit.strip() in keys else "invalid"


def _take_message() -> Step:
    return Step("take_message", "I'm sorry, I don't want to keep getting this wrong. "
                "I'll take a quick message and have them call you straight back. What's the best number for you?")


if __name__ == "__main__":
    for misses in range(4):
        s = next_step(misses, ["Thursday at two", "Tuesday at two"], "the day")
        print(f"miss {misses}: [{s.action}] {s.say}")
