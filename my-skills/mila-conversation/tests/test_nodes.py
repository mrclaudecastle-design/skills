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
        out = self.g("Thanks Linda. I'll book you for Tuesday. Dave will see you today.", have_number=True)
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

    def test_launch_thread_v10_faults(self):
        """Faults found when the launch thread ran v10 in its call loop (24 Nov 2026)."""
        from guard import spoken_numbers
        diary = [("Tuesday", "8am"), ("Thursday", "2pm")]
        # 1. Two numbers said with a comma stay two numbers.
        self.assertEqual(spoken_numbers("Unit three, forty seven Ocean Street"), "Unit 3, 47 Ocean Street")
        self.assertIn("made_up_detail", guard("So that's Unit 347 Ocean Street.", caller="Unit three, forty seven Ocean Street",
                                              have_number=True).fixes)
        self.assertNotIn("made_up_detail", guard("So that's Unit 3, 47 Ocean Street.", caller="Unit three, forty seven Ocean Street",
                                                 have_number=True).fixes)
        # 2. Opening hours are not an offered time.
        g = guard("We're only open Monday to Friday, 7am to 5pm.", diary=diary, have_number=True)
        self.assertNotIn("time", g.fixes)
        # 3. A time with no day, or "tomorrow", is only fine when the day is known and free.
        self.assertIn("time", guard("I can do 2pm.", diary=diary).fixes)
        self.assertNotIn("time", guard("I can do 2pm.", caller="Thursday's good", diary=diary).fixes)
        self.assertIn("time", guard("I can do tomorrow at 2pm.", diary=diary).fixes)
        self.assertNotIn("time", guard("I can do tomorrow at 2pm.", diary=diary, today="Wednesday").fixes)
        self.assertIn("time", guard("I can do tomorrow at 2pm.", diary=diary, today="Monday").fixes)
        # 4. A corrected address said in parts is a re-read, and her question stays.
        last = "So that's Unit 5, 21 Bay Street. Is that right?"
        g = guard(last, caller="Unit five. Twenty one Bay Street.", last_reply=last, have_number=True)
        self.assertNotIn("repeat", g.fixes)
        self.assertTrue(g.text.endswith("Is that right?"))
        # 5. An address already said counts as heard.
        g = guard("Is that 21 Bay Street, Unit 5?", caller="yes", heard_so_far="it's unit five, twenty one Bay Street", have_number=True)
        self.assertNotIn("made_up_detail", g.fixes)
        # 6. Too long keeps an address said in parts.
        g = guard("Lovely. That's Unit 5. At 21 Bay Street. Dave will see you Thursday at 2pm. Anything else?",
                  caller="Unit five, twenty one Bay Street", diary=diary, have_number=True)
        self.assertIn("Unit 5", g.text)
        self.assertIn("21 Bay Street", g.text)

    def test_mac_hand_check_v11(self):
        """Found by hand on v11 (24 Nov 2026)."""
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm"), ("Friday", "11:00am")]
        g = guard("Great, I've got you down for 2:00pm.", caller="Yes, that works.", diary=diary, have_number=True,
                  last_reply="I have Thursday at 2:00pm. Would that suit?")
        self.assertNotIn("time", g.fixes)
        self.assertIn("time", guard("We're open then, so how about Wednesday at 10am?", diary=diary).fixes)
        self.assertIn("time", guard("We work 7am to 4pm, I can do Monday at 10am.", diary=diary).fixes)
        self.assertNotIn("time", guard("We work 7am to 4pm, I can do Friday at 11:00am.", diary=diary).fixes)
        self.assertIn("time", guard("How about Wednesday from 10am?", diary=diary).fixes)
        self.assertIn("time", guard("I can do Wednesday 10am to 11am.", diary=diary).fixes)
        self.assertNotIn("time", guard("We're open Monday to Friday, 7am to 4pm.", diary=diary).fixes)
        g = guard("Sure, 2:00pm works, I've got you down.", caller="Not Thursday. Can you do Wednesday at 2pm?",
                  last_reply="How about Thursday at 2:00pm?", diary=diary, have_number=True)
        self.assertIn("time", g.fixes)
        self.assertNotIn("time", guard("We're open Wednesday 7am to 4pm.", caller="Are you open Wednesday?", diary=diary).fixes)
        self.assertIn("time", guard("Sure, 2:00pm works, I've got you down.", caller="Can you do Wednesday at 2pm, not Thursday?",
                                    last_reply="How about Thursday at 2:00pm?", diary=diary, have_number=True).fixes)
        self.assertIn("time", guard("I can do 10am to 11am on Wednesday.", diary=diary).fixes)
        g = guard("Great, 123 Main Street it is.", caller="yes", last_reply="So that's 123 Main Street.", have_number=True)
        self.assertIn("made_up_detail", g.fixes)

    def test_launch_thread_v14_faults(self):
        """Faults found when the launch thread replayed real replies through v14 (24 Nov 2026)."""
        from guard import spoken_numbers
        card = ShopCard.load(Path(__file__).resolve().parent.parent / "shop" / "examples" / "birch-and-co.json")
        diary = [("Tuesday", "9:30am"), ("Thursday", "4pm"), ("Friday", "11:00am")]
        # 1, 2. Spoken numbers.
        self.assertEqual(spoken_numbers("unit two, three Smith Street"), "unit 2, 3 Smith Street")
        self.assertEqual(spoken_numbers("oh four twelve, three four five, six seven eight"), "0412345678")
        self.assertIn("made_up_detail", guard("So that's Unit 23 Smith Street.", caller="unit two, three Smith Street", have_number=True).fixes)
        self.assertNotIn("need_number", guard("Dave will call you back.", caller="oh four twelve, three four five, six seven eight").fixes)
        # 3. Refusals in other words, and from earlier in the call.
        for no in ("Thursday's no good.", "I can't come Thursday."):
            g = guard("Sure, I've got you down for 4pm.", caller="What else have you got?", heard_so_far=no,
                      last_reply="How about Thursday at 4pm?", diary=diary, have_number=True)
            self.assertIn("time", g.fixes, no)
            self.assertNotIn("Thursday", g.text, no)
        self.assertNotIn("time", guard("Great, Thursday at 4pm it is.", caller="Actually, Thursday then.", heard_so_far="Thursday's no good.",
                                       diary=diary, have_number=True).fixes)
        # 4. "An opening" is an offer.
        self.assertIn("time", guard("We have an opening at 10 am.", diary=diary).fixes)
        # 5, 8. Opening hours must match the card (7am to 4pm).
        self.assertIn("hours", guard("We're open 7am to 9pm.", card=card, diary=diary).fixes)
        self.assertNotIn("hours", guard("We're open 7am to 4pm.", card=card, diary=diary).fixes)
        g = guard("We close at 3 pm, so how about then?", card=card, diary=diary)
        self.assertIn("hours", g.fixes)
        self.assertIn("4pm", g.text)
        self.assertIn("time", guard("You can come from 11 am, Tuesday suits.", diary=diary).fixes)
        self.assertIn("time", guard("Tuesday from 10 to 11 am works.", diary=diary).fixes)
        # 6, 7. Addresses in parts.
        self.assertIn("made_up_detail", guard("So that's number 24, Ocean Street.", caller="twenty two Ocean Street", have_number=True).fixes)
        self.assertIn("made_up_detail", guard("So that's Unit 22, number 22 Ocean Street.", caller="unit two, twenty two Ocean Street",
                                              have_number=True).fixes)
        self.assertNotIn("made_up_detail", guard("Is that 21 Bay Street, Unit 5?", caller="Unit five, Number twenty one. Bay Street",
                                                 have_number=True).fixes)
        # 9. A long read-back keeps a street number said in words.
        g = guard("Lovely. Thanks for that. So that's twenty one Bay Street. Dave will see you Thursday at 4pm. Anything else?",
                  caller="twenty one Bay Street", diary=diary, have_number=True)
        self.assertIn("Bay Street", g.text)
        # 10. Re-asking with the caller's correction is not a repeat.
        last = "So that's 12 Harborview Street?"
        self.assertNotIn("repeat", guard(last, caller="No, I said Harborview", last_reply=last, have_number=True).fixes)

    def test_launch_thread_v15_faults(self):
        """Faults found in the launch thread's v15 text check (24 Nov 2026)."""
        from guard import spoken_numbers
        card = ShopCard({"shop_name": "Birch and Co", "trade": "plumber", "owner_name": "Dave", "country": "au", "open_hours": "7am to 5pm"})
        diary = [("Tuesday", "9:30am"), ("Thursday", "4pm")]
        # 1. Street and numbers in different sentences or turns.
        g = guard("So that's Unit 3, 47 Ocean Street.", caller="No, it's Unit 3, and the street number is 47",
                  heard_so_far="It's on Ocean Street.", have_number=True)
        self.assertNotIn("made_up_detail", g.fixes)
        g = guard("So that's 22 Ocean Street.", caller="The street is Ocean Street. Sorry, number 22.", have_number=True)
        self.assertNotIn("made_up_detail", g.fixes)
        # 2. Run-together or differently spelled streets.
        self.assertNotIn("made_up_detail", guard("So that's 5 Wattle Street.", caller="five Wattlestreet", have_number=True).fixes)
        self.assertNotIn("made_up_detail", guard("So that's 8 Harbour View Road.", caller="eight Harborview Road", have_number=True).fixes)
        self.assertIn("made_up_detail", guard("So that's 8 Banksia Road.", caller="eight Harborview Road", have_number=True).fixes)
        # 3. Not refusals.
        for line in ("Can't you do Thursday?", "I won't be home till Thursday.", "Thursday isn't bad actually."):
            g = guard("Sure, I've got you down for 4pm.", caller=line, diary=diary, have_number=True)
            self.assertNotIn("time", g.fixes, line)
        # 4. A made-up unit said in words.
        self.assertIn("made_up_detail", guard("So that's Unit twenty two, number twenty two, Ocean Street.",
                                              caller="unit two, twenty two Ocean Street", have_number=True).fixes)
        # 5. A confirm question after "No." is not a repeat.
        last = "So that's 12 Ocean Street, is that right?"
        self.assertNotIn("repeat", guard(last, caller="No.", last_reply=last, heard_so_far="twelve Ocean Street", have_number=True).fixes)
        # 6, 7. Spoken numbers.
        self.assertEqual(spoken_numbers("unit two three Smith Street"), "unit 2 3 Smith Street")
        self.assertEqual(spoken_numbers("nine hundred ninety nine"), "999")
        self.assertEqual(spoken_numbers("three thousand four hundred and two"), "3402")
        # 8. Hours with no am or pm that match the card.
        self.assertNotIn("hours", guard("We're open Monday to Friday, 7 to 5.", card=card).fixes)
        self.assertIn("hours", guard("We're open Monday to Friday, 7 to 9.", card=card).fixes)

    def test_launch_thread_v16_faults(self):
        """Faults found in the launch thread's v16 text check (24 Nov 2026)."""
        from guard import spoken_numbers
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]
        # 1. Number words read back before the street.
        self.assertNotIn("made_up_detail", guard("Is that Twenty Two Ocean Street?", caller="Twenty Two Ocean Street", have_number=True).fixes)
        # 2. A phone number she made up.
        self.assertIn("made_up_detail", guard("And your phone number is 0412 345 678?", caller="It's Shane").fixes)
        # 3, 4. Numbers belong to their role.
        self.assertIn("made_up_detail", guard("So that's Unit 3, 47 Ocean Street.", caller="47 Ocean Street",
                                              heard_so_far="I've got 3 taps leaking.", have_number=True).fixes)
        self.assertIn("made_up_detail", guard("So that's Unit 22, number 22 Ocean Street.", caller="22 Ocean Street",
                                              heard_so_far="It's 22 Ocean Street.", have_number=True).fixes)
        self.assertIn("made_up_detail", guard("So that's Unit 47, number 3 Ocean Street.", caller="unit 3, 47 Ocean Street", have_number=True).fixes)
        # 5. Street type, and short names inside words.
        self.assertIn("made_up_detail", guard("So that's 22 Ocean Road.", caller="22 Ocean Street", have_number=True).fixes)
        self.assertIn("made_up_detail", guard("So that's 5 Park Street.", caller="5 Street, near the parking", have_number=True).fixes)
        # 6. The same house number said twice.
        self.assertNotIn("made_up_detail", guard("So that's number 22, at 22 Ocean Street.", caller="22 Ocean Street", have_number=True).fixes)
        # 7. Spoken numbers.
        self.assertEqual(spoken_numbers("a hundred and six"), "106")
        self.assertNotIn("made_up_detail", guard("So that's 321 Ocean Road.", caller="three two one Ocean Road", have_number=True).fixes)
        # 8. Refusals.
        from guard import refused_days
        self.assertEqual(refused_days("Can't Dave do Thursday?"), set())
        self.assertEqual(refused_days("No, I'd like Thursday."), set())
        self.assertEqual(refused_days("I'm flat out Thursday."), {"thursday"})
        self.assertEqual(refused_days("Anything but Thursday."), {"thursday"})
        # 9. Spoken and bare times.
        self.assertIn("time", guard("I can do Tuesday at two pm.", diary=diary).fixes)
        self.assertIn("time", guard("I can do ten on Thursday.", diary=diary).fixes)
        self.assertNotIn("time", guard("I can do two on Thursday.", diary=diary).fixes)

    def test_booking_only_after_yes_to_full_read_back(self):
        card = ShopCard({"shop_name": "Birch and Co", "trade": "plumber", "owner_name": "Dave", "country": "au", "bookings": "book"})
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]
        heard = "It's Shane. 0412 345 678. 14 Banksia Crescent. Thursday works."
        g = guard("Great, you're booked for Thursday at 2:00pm.", caller="Thursday works.", card=card, diary=diary,
                  heard_so_far="It's Shane. 0412 345 678. 14 Banksia Crescent.", have_number=True)
        self.assertEqual(g.fixes, ["booking"])
        self.assertTrue(g.text.endswith("Just to check: Thursday at 2:00pm, Shane on 0412 345 678, at 14 Banksia Crescent. Is that right?"))
        read_back = "Just to check: Thursday at 2:00pm, Shane on 0412 345 678, at 14 Banksia Crescent. Is that right?"
        g = guard("Great, you're booked for Thursday at 2:00pm.", caller="Yes, that's right.", card=card, diary=diary,
                  heard_so_far=heard, last_reply=read_back, have_number=True)
        self.assertNotIn("booking", g.fixes)
        g = guard("I've booked you in.", caller="Yep.", card=card, diary=None, heard_so_far=heard, last_reply=read_back, have_number=True)
        self.assertIn("booking", g.fixes)
        msg = ShopCard({"shop_name": "Birch and Co", "trade": "plumber", "owner_name": "Dave", "country": "au", "bookings": "message"})
        g = guard("You're booked for Thursday at 2:00pm.", caller="Yes.", card=msg, diary=diary, heard_so_far=heard,
                  last_reply=read_back, have_number=True)
        self.assertIn("booking", g.fixes)

    def test_launch_thread_v17_faults(self):
        """Faults found in the launch thread's v17 text check (24 Nov 2026)."""
        from guard import caller_name, spoken_numbers
        card = ShopCard({"shop_name": "Birch and Co", "trade": "plumber", "owner_name": "Dave", "country": "au", "bookings": "book"})
        diary = [("Tuesday", "8am"), ("Thursday", "2:00pm")]
        heard = "It's Shane. 0412 345 678. 14 Banksia Crescent. Thursday works."
        # Booking: the read-back must carry the caller's own number and address.
        for lr in ("Just to check: Thursday at 2:00pm, Shane, at 14 Banksia Crescent. Is that right?",
                   "Just to check: Thursday at 2:00pm, Shane on 0499 999 999, at 14 Banksia Crescent. Is that right?",
                   "Just to check: Thursday at 2:00pm, Shane on 0412 345 678, at 99 Elm Street. Is that right?"):
            g = guard("Great, you're booked.", caller="Yes.", card=card, diary=diary, heard_so_far=heard, last_reply=lr, have_number=True)
            self.assertIn("booking", g.fixes, lr)
        good = "Just to check: Thursday at 2:00pm, Shane on 0412 345 678, at 14 Banksia Crescent. Is that right?"
        for said in ("Your booking is confirmed.", "Dave's locked it in."):
            self.assertIn("booking", guard(said, caller="Thursday works.", card=card, diary=diary, heard_so_far=heard).fixes, said)
        for yes in ("That's all correct.", "Thanks."):
            self.assertNotIn("booking", guard("You're booked.", caller=yes, card=card, diary=diary, heard_so_far=heard,
                                              last_reply=good, have_number=True).fixes, yes)
        # After a booking, saying so again is fine even though that spot has left the diary.
        g = guard("You're all booked in for Thursday at 2:00pm.", caller="Thanks!", card=card, diary=[("Tuesday", "8am")],
                  heard_so_far=heard, last_reply="Great, you're booked for Thursday at 2:00pm.", have_number=True)
        self.assertEqual(g.fixes, [])
        # A blank template is never read out.
        self.assertIn("template", guard("Monday 8 am | [Name]").fixes)
        # 1. An invented phone number, even once a number is known.
        self.assertIn("made_up_detail", guard("So that's 0499 999 999?", caller="yes", heard_so_far="0412 345 678", have_number=True).fixes)
        # 3. "It's Unit twelve" is not a name.
        self.assertIsNone(caller_name("It's Unit twelve."))
        self.assertEqual(caller_name("It's Unit twelve. I'm Joe Brown."), "Joe Brown")
        # 4. Slash and over.
        self.assertEqual(spoken_numbers("3 slash 47 Ocean Street"), "3/47 Ocean Street")
        self.assertEqual(spoken_numbers("five over twenty one"), "5/21")
        # 5. "We have one on Tuesday at 8 am" offers Tuesday at 8am, not 1pm.
        self.assertNotIn("time", guard("We have one on Tuesday at 8 am.", diary=diary).fixes)
        self.assertNotIn("time", guard("Dave has three on Thursday, but 2:00pm is free.", caller="Thursday?", diary=diary).fixes)
        # 6. Clock words.
        self.assertIn("time", guard("I can do ten o'clock Tuesday.", diary=diary).fixes)
        self.assertIn("time", guard("I can do half past nine on Tuesday.", diary=diary).fixes)
        self.assertNotIn("time", guard("I can do eight o'clock Tuesday.", diary=diary).fixes)

    def test_live_06_slips_are_caught(self):
        """Real replies from live round 6 (untrained Qwen, card kept ready, 24 Nov 2026)."""
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm"), ("Friday", "11:00am")]
        # Call 8: a plain list of the free spots is left alone.
        g = guard("We have Tuesday at 9:30am, Thursday at 2:00pm, or Friday at 11:00am. Which suits?", caller="Righto, what have you got then?",
                  diary=diary)
        self.assertNotIn("time", g.fixes)
        # Call 12: inviting the caller to ring back on a goodbye is not a promise of a call.
        g = guard("Thanks for calling Birch and Co Plumbing. If you need help with plumbing, feel free to call back.", caller="No worries. Bye.")
        self.assertNotIn("need_number", g.fixes)
        # Fillers.
        self.assertIn("sign_off", guard("Got it, Bec. Is there anything else you'd like to add?", caller="it's about the quote").fixes)
        self.assertIn("sign_off", guard("We don't do roofing, sorry. Let me know how we can help with your issue!", caller="roofing?").fixes)
        # Wording.
        g = guard("I'll pass your message to Dave right away.", caller="get Dave to ring me", have_number=True)
        self.assertNotIn("message", g.text)
        self.assertNotIn("right away", g.text)
        g = guard("Would you like to book a time for Dave to call?", have_number=True)
        self.assertEqual(g.text, "Would you like to have Dave call you back?")

    def test_one_ask_and_prices(self):
        """Wobbles from live round 6: two asks at once, an address for a call back, no price on a price question."""
        card = ShopCard.load(Path(__file__).resolve().parent.parent / "shop" / "examples" / "birch-and-co.json")
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm")]
        g = guard("Can I get your address and phone number so I can book you in?", caller="Nah yeah, Thursday works.", card=card, diary=diary,
                  heard_so_far="G'day, my hot water's carked it. It's Shane.")
        self.assertEqual(g.text, "What's the best number to reach you on?")
        g = guard("Could you give me your name and number, and what address you're at?", caller="Yeah alright, get him to call me.",
                  card=card, diary=diary)
        self.assertEqual(g.text, "Can I grab your name?")
        g = guard("I'm sorry, but I can't give you a price over the phone. Dave will need to assess the job.",
                  caller="Come on, you must have some idea.", heard_so_far="Just give me a ballpark, fifty bucks?", card=card, have_number=True)
        self.assertIn("$90", g.text)
        g = guard("I'm sorry, but I can't give you a price over the phone.", caller="How much roughly?", card=card, have_number=True)
        self.assertIn("$90", g.text)

    def test_live_07_slips_are_caught(self):
        """Real replies from live round 7 (v22, 27 Nov 2026)."""
        card = ShopCard.load(Path(__file__).resolve().parent.parent / "shop" / "examples" / "birch-and-co.json")
        diary = [("Tuesday", "9:30am"), ("Thursday", "2:00pm"), ("Friday", "11:00am")]
        # Call 10: the shop works Wednesdays.
        g = guard("We don't do Wednesday. Would you like to book one of our free spots instead?", caller="Can I book Wednesday at 10am?",
                  card=card, diary=diary)
        self.assertNotIn("don't do Wednesday", g.text)
        self.assertIn("Wednesday at 10am isn't free", g.text)
        self.assertNotIn("closed_day", guard("We don't do Sundays, sorry.", caller="Sunday?", card=card, diary=diary).fixes)
        # Call 2: a visit is never "as soon as possible" when the diary has spots.
        g = guard("Sure, I can have someone come out today.", caller="Could someone come out this week?", card=card, diary=diary)
        self.assertNotIn("as soon as possible", g.text)
        self.assertIn("Tuesday at 9:30am", g.text)
        # Call 1: booked before a yes.
        self.assertIn("booking", guard("Got you booked for Thursday 2:00pm.", caller="Nah yeah, Thursday works.", card=card, diary=diary).fixes)
        # Call 7: "as soon as" once.
        g = guard("I'll pass your message to Dave right away. He'll ring you as soon as he can.", caller="get Dave to ring me", card=card,
                  have_number=True)
        self.assertEqual(g.text.count("as soon as"), 1)
        # Call 9: urgent asks address and number before name, then says the card's promise.
        g = guard("That's urgent. Can I grab your name?", caller="There's water pouring through my ceiling!", card=card, diary=diary)
        self.assertIn("address", g.text)
        g = guard("So that's 0411 000 999. Your name?", caller="0411 000 999.", heard_so_far="Water pouring through my ceiling! 22 Old Coach Road.",
                  card=card, diary=diary)
        self.assertIn("within fifteen minutes", g.text)
        # Call 11: the price line is not said twice word for word.
        line = "The call-out fee is $90, and the rest depends on the job. Would you like Dave to call you with a proper price?"
        g = guard("I'm sorry, I can't give you a price.", caller="Come on, you must have some idea.", card=card, last_reply=line, have_number=True)
        self.assertNotEqual(g.text, line)

    def test_spoken_numbers(self):
        from guard import spoken_numbers
        self.assertEqual(spoken_numbers("forty seven Ocean Street"), "47 Ocean Street")
        self.assertEqual(spoken_numbers("oh four one two, three four five, six seven eight"), "0412345678")
        self.assertEqual(spoken_numbers("ring 0412 345 678"), "ring 0412 345 678")

    def test_live_05_slips_are_caught(self):
        g = guard("I've booked Dave for Thursday 2:00pm. He'll be with you shortly.", caller="yeah Thursday's good",
                  diary=[("Thursday", "2:00pm")], have_number=True)
        self.assertNotIn("shortly", g.text)           # and no booking yet: no name, number or address
        self.assertEqual((g.fixes, g.text), (["booking"], "Can I grab your name?"))
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
        # No booking until the address is in and the caller says yes to the read-back.
        self.assertEqual(out.text, "So that's Linda Park on 0498 111 222. What's the address for the job?")
        same = "Thanks, Shane, 14 Banksia Crescent. We'll have Dave out on Thursday 2:00pm. Is there anything else I can help with?"
        out = self.g(same, "0412 345 678.", heard_so_far="It's Shane, 14 Banksia Crescent.", last_reply=same)
        # The caller just gave a number, so this is not a repeat: the number is read back in front (launch thread, 24 Nov).
        self.assertEqual(out.fixes, ["read_back"])
        self.assertTrue(out.text.startswith("So that's 0412 345 678.") and "14 Banksia Crescent" in out.text)
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
