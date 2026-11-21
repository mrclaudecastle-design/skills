#!/usr/bin/env python3
"""Checks for every node. Run: python3 tests/test_nodes.py"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nodes"))
from fillers import Fillers                                   # noqa: E402
from lingo import mirror, understand                          # noqa: E402
from plausibility import Vote, decide, phone_has_enough_digits, within_opening_days  # noqa: E402
from repair import handle_key, next_step                      # noqa: E402
from say_it import number_words, say_it                       # noqa: E402
from stopwatch import Stopwatch                               # noqa: E402


class SayIt(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(number_words(0), "zero")
        self.assertEqual(number_words(85), "eighty-five")
        self.assertEqual(number_words(105), "one hundred and five")
        self.assertEqual(number_words(1250), "one thousand two hundred and fifty")
        self.assertEqual(number_words(2005), "two thousand and five")

    def test_phones(self):
        self.assertEqual(say_it("0412 345 678"), "oh four one two, three four five, six seven eight")
        self.assertEqual(say_it("0412345678"), "oh four one two, three four five, six seven eight")
        self.assertEqual(say_it("(02) 9876 5432"), "oh two, nine eight seven six, five four three two")
        self.assertEqual(say_it("1300 123 456"), "thirteen hundred, one two three, four five six")
        self.assertEqual(say_it("604-555-0199"), "six oh four, five five five, oh one nine nine")

    def test_money(self):
        self.assertEqual(say_it("$85"), "eighty-five dollars")
        self.assertEqual(say_it("$1"), "one dollar")
        self.assertEqual(say_it("$85.50"), "eighty-five dollars fifty")
        self.assertEqual(say_it("$1,250.00"), "one thousand two hundred and fifty dollars")

    def test_times(self):
        self.assertEqual(say_it("2:30pm"), "half past two in the afternoon")
        self.assertEqual(say_it("9am"), "nine o'clock in the morning")
        self.assertEqual(say_it("7:45 am"), "quarter to eight in the morning")
        self.assertEqual(say_it("10:05am"), "ten oh five in the morning")
        self.assertEqual(say_it("14:15"), "quarter past two in the afternoon")
        self.assertEqual(say_it("6:30pm"), "half past six in the evening")

    def test_addresses_and_punctuation(self):
        self.assertEqual(say_it("3/14 Smith St."), "unit three, fourteen Smith Street.")
        self.assertEqual(say_it("22 Old Coach Rd"), "twenty-two Old Coach Road")
        self.assertEqual(say_it("Open till 5pm."), "Open till five o'clock in the afternoon.")
        self.assertIn("St Kilda", say_it("We're in St Kilda"))

    def test_plain_text_untouched(self):
        line = "No worries, I'll let them know."
        self.assertEqual(say_it(line), line)


class Lingo(unittest.TestCase):
    def test_yeah_nah(self):
        self.assertIn("no", understand("yeah nah", "au")["signals"])
        self.assertIn("yes", understand("nah yeah", "au")["signals"])
        u = understand("Yeah nah yeah that works", "au")
        self.assertEqual(u["signals"], {"yes"})

    def test_plain_meaning(self):
        u = understand("the hot water's carked it, can you come this arvo", "au")
        self.assertEqual(u["plain"], "the hot water's stopped working, can you come this afternoon")
        self.assertEqual(u["signals"], {"broken", "time"})

    def test_no_false_hits_inside_words(self):
        u = understand("I need the tap fixed at the beauty salon in Taree", "au")
        self.assertEqual(u["matched"], [])
        self.assertFalse(u["casual"])

    def test_canada(self):
        u = understand("For sure, the furnace is on the fritz, eh.", "ca")
        self.assertEqual(u["plain"], "yes, the home heater is not working properly.")
        self.assertTrue({"yes", "broken", "casual"} <= u["signals"])

    def test_never_starts_slang(self):
        self.assertIsNone(mirror("ok", "au", caller_was_casual=False))
        self.assertIn(mirror("ok", "au", caller_was_casual=True, rng=random.Random(1)),
                      ["No worries.", "Too easy.", "Easy done."])


class Plausibility(unittest.TestCase):
    def test_agreement_wins(self):
        r = decide([Vote("Thursday 2pm", 0.7, "ears-1"), Vote("thursday  2pm", 0.9, "brain"), Vote("Tuesday 2pm", 0.2, "ears-2")])
        self.assertEqual((r.value, r.action), ("Thursday 2pm", "act"))
        self.assertEqual(r.runners_up, ["Tuesday 2pm"])

    def test_split_vote_confirms(self):
        r = decide([Vote("Thursday 2pm", 0.6), Vote("Tuesday 2pm", 0.4), Vote("Thursday 2pm", 0.3)])
        self.assertEqual(r.action, "confirm")

    def test_lone_voter_capped(self):
        self.assertEqual(decide([Vote("Thursday 2pm", 0.4)]).action, "repair")

    def test_checks_knock_out_nonsense(self):
        open_days = within_opening_days({"monday", "tuesday", "wednesday", "thursday", "friday"})
        r = decide([Vote("Sunday 2pm", 0.7), Vote("Monday 2pm", 0.5), Vote("Monday 2pm", 0.6)], checks=[open_days])
        self.assertEqual(r.value, "Monday 2pm")
        r = decide([Vote("0412 345 67", 0.9), Vote("0412 345 678", 0.5), Vote("0412 345 678", 0.5)], checks=[phone_has_enough_digits])
        self.assertEqual(r.value, "0412 345 678")

    def test_nothing_heard(self):
        r = decide([Vote("", 0.9), Vote(None, 0.5)])
        self.assertEqual((r.value, r.action), (None, "repair"))


class Repair(unittest.TestCase):
    def test_ladder(self):
        g = ["Thursday at two", "Tuesday at two"]
        self.assertEqual([next_step(i, g).action for i in range(4)], ["ask_again", "read_back", "keypad", "take_message"])

    def test_keypad(self):
        s = next_step(2, ["Thursday at two", "Tuesday at two"])
        self.assertIn("press 1 for Thursday at two", s.say)
        self.assertEqual(handle_key("1", s.keys), "Thursday at two")
        self.assertEqual(handle_key("2", s.keys), "Tuesday at two")
        self.assertIsNone(handle_key("3", s.keys))
        self.assertEqual(handle_key("9", s.keys), "invalid")

    def test_no_guesses(self):
        self.assertEqual(next_step(1, []).action, "ask_again")
        self.assertEqual(next_step(2, []).action, "take_message")


class StopwatchAndFillers(unittest.TestCase):
    def test_stopwatch_flags_slow_step(self):
        ticks = iter([0.0, 0.1, 0.1, 0.9, 0.9, 1.0])
        sw = Stopwatch(clock=lambda: next(ticks))
        for name in ("hear", "think", "speak"):
            with sw.step(name):
                pass
        self.assertEqual(sw.slow_steps(), ["think"])
        self.assertAlmostEqual(sw.total_ms, 1000, places=3)
        self.assertIn("SLOW", sw.report())

    def test_fillers_never_repeat(self):
        f = Fillers(random.Random(3))
        said = [f.listening() for _ in range(30)]
        self.assertTrue(all(a != b for a, b in zip(said, said[1:])))
        self.assertIsNone(f.holding("diary", expected_wait_ms=200))
        self.assertIsNotNone(f.holding("diary", expected_wait_ms=1500))


if __name__ == "__main__":
    unittest.main(verbosity=1)
