#!/usr/bin/env python3
"""Checks for every node. Run: python3 tests/test_nodes.py"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nodes"))
from fillers import Fillers                                   # noqa: E402
from guard import guard                                       # noqa: E402
from lingo import mirror, understand                          # noqa: E402
from plausibility import Vote, decide, phone_has_enough_digits, within_opening_days  # noqa: E402
from repair import handle_key, next_step                      # noqa: E402
from say_it import number_words, say_it                       # noqa: E402
from stopwatch import Stopwatch                               # noqa: E402
from shop_card import ShopCard                                # noqa: E402
from turn import Call                                         # noqa: E402


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


class Turn(unittest.TestCase):
    def test_clear_line_carries_on(self):
        out = Call("au").hear([("thursday at two", 0.9)], brain_reading="thursday at two")
        self.assertEqual((out.action, out.say, out.meaning), ("act", None, "thursday at two"))

    def test_unsure_reads_back_then_yes(self):
        call = Call("au")
        out = call.hear([("thursday arvo at two", 0.5), ("tuesday arvo at two", 0.45)])
        self.assertEqual(out.action, "confirm")
        self.assertIn("thursday afternoon at two", out.say)
        out = call.hear([("nah yeah", 0.9)])
        self.assertEqual((out.action, out.meaning, call.misses), ("act", "thursday afternoon at two", 0))

    def test_full_ladder_to_keypad_and_message(self):
        call = Call("au")
        self.assertEqual(call.hear([("mumble", 0.2)]).action, "ask_again")
        self.assertEqual(call.hear([("thursday at ten", 0.3), ("tuesday at two", 0.28), ("thursday at two", 0.2)]).action, "read_back")
        out = call.hear([("no", 0.9)])
        self.assertEqual(out.action, "keypad")
        self.assertNotIn("thursday at ten", out.say)
        self.assertEqual(call.press("9").action, "keypad")
        self.assertEqual(call.press("3").action, "take_message")

    def test_keypad_choice(self):
        call = Call("au")
        call.hear([("mumble", 0.2)])
        call.hear([("thursday at ten", 0.3), ("tuesday at two", 0.28)])
        call.hear([("nope", 0.9)])
        out = call.press("1")
        self.assertEqual((out.action, out.meaning), ("act", "tuesday at two"))

    def test_only_casual_after_caller_is(self):
        call = Call("au")
        self.assertEqual(call.ok(), "Of course.")
        call.hear([("too easy, cheers", 0.9)])
        self.assertIn(call.ok(), ["No worries.", "Too easy.", "Easy done."])


class Shop(unittest.TestCase):
    ROOT = Path(__file__).resolve().parent.parent

    def card(self, **extra):
        return ShopCard({"shop_name": "Birch and Co", "trade": "plumber", "owner_name": "Dave", "country": "au", **extra})

    def test_example_is_ready(self):
        card = ShopCard.load(self.ROOT / "shop" / "examples" / "birch-and-co.json")
        self.assertEqual(card.missing(), [])
        text = card.instructions()
        for needle in ("Birch and Co Plumbing", "Dave", "call-out fee $90", "Does not do: roofing", "book jobs into the diary"):
            self.assertIn(needle, text)

    def test_four_answers_are_enough(self):
        card = self.card()
        self.assertEqual(card.missing(), [])
        text = card.instructions()
        self.assertIn("You have no prices", text)
        self.assertIn("You don't book jobs", text)
        self.assertEqual(card.greeting(), "Birch and Co, this is Mila, the AI receptionist. How can I help?")

    def test_missing_and_bad_answers_are_named_in_plain_words(self):
        card = ShopCard({"shop_name": "Birch and Co", "country": "nz"})
        missing = card.missing()
        self.assertIn("What do you do, in a few words?", missing)
        self.assertTrue(any("Which country" in m for m in missing))
        with self.assertRaises(ValueError):
            card.instructions()

    def test_card_drives_the_call(self):
        call = Call(card=self.card(open_days=["monday", "tuesday"]))
        out = call.hear([("sunday at two", 0.6), ("monday at two", 0.5), ("monday at two", 0.5)])
        self.assertEqual(out.meaning, "monday at two")

    def test_training_calls_use_the_card(self):
        sys.path.insert(0, str(self.ROOT / "finetune"))
        from make_seed_data import make
        rows = make(120, seed=3)
        self.assertEqual(len(rows), 120)
        for row in rows:
            system = row["messages"][0]["content"]
            self.assertIn("About this business:", system)
            self.assertEqual(row["messages"][-1]["role"], "assistant")
            said = " ".join(m["content"] for m in row["messages"][1:] if m["role"] == "assistant")
            if "$" in said and "0412" not in said:
                self.assertIn("Prices you may say", system)

    def test_v3_calls_keep_the_three_habits(self):
        import re
        sys.path.insert(0, str(self.ROOT / "finetune"))
        from make_calls_v3 import make
        rows = make(300, seed=5)
        lines = [m["content"] for row in rows for m in row["messages"] if m["role"] == "assistant"]
        self.assertGreater(len(set(lines)) / len(lines), 0.5)          # varied wording, not templates
        for row in rows:
            turns = row["messages"][1:]
            self.assertEqual(turns[-1]["role"], "assistant")
            for i, m in enumerate(turns[:-1]):
                if m["role"] == "user":
                    for number in re.findall(r"04\d\d \d{3} \d{3}|\d{3}-555-01\d\d", m["content"]):
                        self.assertIn(number, turns[i + 1]["content"])   # every number is read back
            if "Free spots in the diary" in row["messages"][0]["content"]:
                spots = row["messages"][0]["content"].split("Free spots in the diary: ")[1]
                for m in turns:
                    for day, time in re.findall(r"(Monday|Tuesday|Wednesday|Thursday|Friday) at (\d+:\d\d[ap]m)", m["content"]):
                        if m["role"] == "assistant":
                            self.assertIn(f"{day} {time}", spots)        # only offers real diary spots


class Guard(unittest.TestCase):
    ROOT = Path(__file__).resolve().parent.parent
    DIARY = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]

    def setUp(self):
        self.card = ShopCard.load(self.ROOT / "shop" / "examples" / "birch-and-co.json")

    def g(self, reply, caller="", diary="default", **kw):
        return guard(reply, caller, self.card, self.DIARY if diary == "default" else diary, **kw)

    def test_good_reply_is_left_alone(self):
        for reply in ["The call-out fee is $90.", "The next spot Dave has is Thursday at 2:00pm. Would that suit?",
                      "Sorry, roofing isn't something Dave does. Is there anything else I can help with?"]:
            out = self.g(reply, have_number=True)
            self.assertEqual((out.text, out.fixes), (reply, []))

    def test_run_02_misses_are_caught(self):
        out = self.g("I'll pass your call to Dave.", "Can you get Dave to call me back? It's Bec, 0412 345 678.")
        self.assertEqual(out.fixes, ["read_back"])
        self.assertEqual(out.text, "So that's Bec on 0412 345 678. I'll pass your call to Dave.")
        out = self.g("That's an emergency. I'll get Dave to call you back now.", "There's water pouring through my ceiling!")
        self.assertEqual(out.fixes, ["need_number"])
        self.assertIn("best number", out.text)

    def test_number_already_read_back_or_known(self):
        self.assertEqual(self.g("So that's 0412 345 678. Dave will call you back.", "It's 0412 345 678").fixes, [])
        self.assertEqual(self.g("So that's oh four one two... 0412345678.", "0412 345 678").fixes, [])
        self.assertEqual(self.g("Dave will call you back shortly.", "Thanks", have_number=True).fixes, [])

    def test_prices(self):
        out = self.g("It's usually about $150 for a tap.")
        self.assertIn("price", out.fixes)
        self.assertNotIn("150", out.text)
        self.assertEqual(out.text.count("?"), 1)                      # one question at a time
        self.assertIn("price", self.g("Probably eighty bucks or 80 dollars.").fixes)

    def test_times(self):
        out = self.g("Sure, I can do Wednesday at 10am.")
        self.assertEqual(out.fixes, ["time"])
        self.assertIn("Tuesday at 9:30am", out.text)
        self.assertEqual(self.g("How about Thursday at 2pm?").fixes, [])
        self.assertIn("time", self.g("I can do Thursday at 2pm.", diary=None).fixes)   # can't see the diary
        self.assertIn("time", self.g("I can do Sunday at 2pm.", diary=[("Sunday", "2pm")]).fixes)  # closed day

    def test_deadline_and_speech(self):
        out = self.g("Dave will be there within ten minutes.", have_number=True)
        self.assertEqual(out.fixes, ["deadline"])
        self.assertIn("as soon as possible", out.text)
        # The card promises fifteen minutes, but only for urgent calls.
        self.assertEqual(self.g("Dave will ring within fifteen minutes.", "There's water pouring through my ceiling!", have_number=True).fixes, [])
        self.assertEqual(self.g("Dave will ring within fifteen minutes.", "It's about a leaking tap.", have_number=True).fixes, ["deadline"])
        out = self.g("We do:\n- blocked drains\n- **hot water**\n- taps")
        self.assertIn("speech_only", out.fixes)
        self.assertNotRegex(out.text, r"[*\n-] ")
        out = self.g("One. Two. Three. Four. Would Tuesday suit?")
        self.assertIn("too_long", out.fixes)
        self.assertTrue(out.text.endswith("Would Tuesday suit?"))

    def test_live_01_slips_are_caught(self):
        """Real replies from the first live run on the Mac (untrained Qwen, 23 Nov 2026)."""
        out = self.g("Thanks, Linda. I've noted your details. Dave will call you to confirm the time. Is there anything else I can assist with?",
                     "My name is Linda Park and the number is 0498 111 222.")
        self.assertTrue(out.text.startswith("So that's Linda Park on 0498 111 222. "))
        self.assertIn("Dave will call you to confirm the time.", out.text)
        self.assertEqual(out.text.count("?"), 1)
        out = guard("Great, Friday works. What time this week?", "Yes, Friday is fine.", self.card,
                    [("Tuesday", "9:30am"), ("Thursday", "2:00pm"), ("Friday", "11:00am")])
        self.assertEqual((out.fixes, out.text), (["offer_spot"], "Great, Friday works. I have Friday at 11:00am. Would that suit?"))
        out = self.g("G'day! I'll check if Dave can fit you in this arvo. What day and time would work best for you?",
                     "G'day, my hot water's carked it, reckon someone could come this arvo?")
        self.assertIn("Tuesday at 9:30am or Thursday at 2:00pm", out.text)
        self.assertNotIn("this arvo", out.text)
        out = self.g("Got it, 0433 987 654. Dave will call you back within fifteen minutes. Is there anything else I can assist with?", "0433 987 654.")
        self.assertEqual(out.fixes, ["deadline"])
        self.assertIn("as soon as possible", out.text)
        out = self.g("Thanks Linda. I'll book you for Friday. Dave will see you today.", have_number=True)
        self.assertEqual(out.fixes, ["promise"])
        self.assertNotIn("today", out.text)
        out = self.g("No, we don't do roofing. We specialise in plumbing. Let me know if you need help with anything else!")
        self.assertEqual((out.fixes, out.text), (["sign_off"], "No, we don't do roofing. We specialise in plumbing."))
        self.assertEqual(self.g("Sorry, I can't do today. The next free spot is Tuesday at 9:30am.").fixes, [])
        self.assertEqual(self.g("Thanks, 0411 000 999. Dave will call you within fifteen minutes.", "0411 000 999.", urgent=True).fixes, [])

    def test_live_03_slips_are_caught(self):
        """Real replies from the second live run (untrained Qwen, v5 guard, 23 Nov 2026)."""
        out = self.g("Sure thing, Dave will ring you back soon. Have a great day!", "Yeah alright, get him to call me.")
        self.assertEqual(out.text, "Sure thing, Dave will ring you back soon. What's the best number for Dave to call?")
        out = self.g("Sure thing, Tom. I'll have Dave call you right away.", "Yeah, get Dave to ring me. It's Tom on 0455 222 333.")
        self.assertEqual(out.text, "So that's Tom on 0455 222 333. I'll have Dave call you as soon as possible.")
        out = self.g("Thanks, Linda. I've noted your name and number. Dave will call you back to confirm the details. Have a great day!",
                     "My name is Linda Park and the number is 0498 111 222.")
        self.assertEqual(out.text, "So that's Linda Park on 0498 111 222. Dave will call you back to confirm the details.")
        out = self.g("Sure, Wednesday at 10am. Is that correct?", "Can I book Wednesday at 10am?")
        self.assertEqual(out.text, "Sorry, Wednesday at 10am isn't free. The next free spot is Tuesday at 9:30am. Would that suit?")
        self.assertEqual(self.g("Thanks, have a great day!", "No worries. Bye.", have_number=True).fixes, [])   # a real goodbye stays

    def test_launch_thread_replay_faults(self):
        """Faults found when the launch thread replayed 206 real replies from 34 saved calls (24 Nov 2026)."""
        diary = [("Tuesday", "9:30am"), ("Wednesday", "9am"), ("Thursday", "2:00pm")]
        # 1. A real appointment time is not a vague promise.
        g = guard("Dave can come at 9am tomorrow.", caller="tomorrow works", have_number=True)
        self.assertNotIn("promise", g.fixes)
        # 2. Re-reading a corrected address is not a repeat.
        last = "So that's 47 Ocean Street. Is that right?"
        g = guard(last, caller="No, 47 Ocean Street, not 41.", last_reply=last, have_number=True)
        self.assertNotIn("repeat", g.fixes)
        # 3. An address or number said in words counts as given.
        g = guard("So that's 47 Ocean Street.", caller="it's forty seven Ocean Street", have_number=True)
        self.assertNotIn("made_up_detail", g.fixes)
        g = guard("Dave will call you back.", caller="it's oh four one two, three four five, six seven eight")
        self.assertNotIn("need_number", g.fixes)
        # 4. Too long never cuts the number out of a read-back.
        g = guard("Thanks Shane. That's a free spot in the diary. Lovely. Your number is 0412 345 678. Dave will see you Thursday at 2:00pm. "
                  "Anything else?", have_number=True, diary=diary)
        self.assertIn("0412 345 678", g.text)
        # 5. Time first, a wrong time in a list, a near-miss house number, curly apostrophes.
        self.assertIn("time", guard("I can do 10 am on Tuesday.", diary=diary).fixes)
        self.assertIn("time", guard("I have Tuesday at 9:30am or 11am.", diary=diary).fixes)
        self.assertNotIn("time", guard("I have Tuesday at 9:30am or Wednesday at 9am.", diary=diary).fixes)
        self.assertIn("made_up_detail", guard("So that's 7 Ocean Street.", caller="47 Ocean Street", have_number=True).fixes)
        self.assertIn("promise", guard("Dave\u2019ll ring you back today.", have_number=True).fixes)

    def test_spoken_numbers(self):
        from guard import spoken_numbers
        self.assertEqual(spoken_numbers("forty seven Ocean Street"), "47 Ocean Street")
        self.assertEqual(spoken_numbers("oh four one two, three four five, six seven eight"), "0412345678")
        self.assertEqual(spoken_numbers("ring 0412 345 678"), "ring 0412 345 678")

    def test_live_05_slips_are_caught(self):
        g = guard("I've booked Dave for Thursday 2:00pm. He'll be with you shortly.", caller="yeah Thursday's good",
                  diary=[("Thursday", "2:00pm")], have_number=True)
        self.assertEqual((g.fixes, g.text), (["promise"], "I've booked Dave for Thursday 2:00pm."))
        g = guard("Dave will call you as soon as he's back in the office.", have_number=True)
        self.assertEqual(g.text, "Dave will call you as soon as possible.")
        g = guard("We don't give prices over the phone, mate.", caller="just give me a number")
        self.assertEqual((g.fixes, g.text), (["slang"], "We don't give prices over the phone."))
        g = guard("No worries, mate.", caller="cheers mate")
        self.assertEqual(g.fixes, [])
        g = guard("Dave will be there within fifteen minutes, he'll be with you shortly.", caller="the pipe has burst", urgent=True, have_number=True)
        self.assertNotIn("promise", g.fixes)

    def test_live_04_slips_are_caught(self):
        """Real replies from the third live run (untrained Qwen, v6 guard, 23 Nov 2026)."""
        out = self.g("Thanks, Linda. I've booked you for Friday at 11:00am. The address is 123 Main Street, right?",
                     "My name is Linda Park and the number is 0498 111 222.", diary=[("Friday", "11:00am")],
                     heard_so_far="Hello, I have a blocked drain. Yes, Friday is fine.")
        self.assertIn("made_up_detail", out.fixes)
        self.assertNotIn("Main Street", out.text)
        self.assertEqual(out.text, "So that's Linda Park on 0498 111 222. I've booked you for Friday at 11:00am. What's the address for the job?")
        same = "Thanks, Shane, 14 Banksia Crescent. We'll have Dave out on Thursday 2:00pm. Is there anything else I can help with?"
        out = self.g(same, "0412 345 678.", heard_so_far="It's Shane, 14 Banksia Crescent.", last_reply=same)
        self.assertEqual((out.fixes, out.text), (["repeat", "read_back"], "So that's 0412 345 678."))
        self.assertEqual(self.g("Got it, Shane, 14 Banksia Crescent.", "It's Shane, 14 Banksia Crescent.", have_number=True).fixes, [])   # a real address stays
        out = self.g("Yes, there's a call-out fee of $90. Is there anything else I can help with?", "Is there a call-out fee?")
        self.assertEqual((out.fixes, out.text), (["sign_off"], "Yes, there's a call-out fee of $90."))
        out = self.g("Got it, Tuesday's not working. How about Thursday 2:00pm? That's a free spot in the diary. Sounds good?", "Yeah nah, Tuesday's no good.")
        self.assertEqual(out.text, "Got it, Tuesday's not working. How about Thursday 2:00pm? Sounds good?")

    def test_call_speaks_through_the_guard(self):
        call = Call(card=self.card)
        call.hear([("it's bec on 0412 345 678", 0.9)], brain_reading="it's bec on 0412 345 678")
        out = call.speak("Thanks Bec, I'll pass that on.", self.DIARY)
        self.assertIn("read_back", out.signals)
        self.assertIn("oh four one two", out.say)
        self.assertEqual(call.speak("Dave will call you back soon.", self.DIARY).signals, set())


if __name__ == "__main__":
    unittest.main(verbosity=1)
