#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from listening_score import detail_kept, errors, score, table, words  # noqa: E402


class ListeningScore(unittest.TestCase):
    def test_numbers_match_either_way(self):
        self.assertEqual(words("0412 345"), words("oh four one two, three four five"))

    def test_errors(self):
        self.assertEqual(errors(words("old coach road"), words("old coach road")), 0)
        self.assertEqual(errors(words("old coach road"), words("old couch road")), 1)
        self.assertEqual(errors(words("old coach road"), words("old road")), 1)
        self.assertEqual(errors(words("a b"), words("")), 2)

    def test_details(self):
        heard = words("it's bec at twenty two old coach road on oh four one two")
        self.assertTrue(detail_kept("Old Coach Road", heard))
        self.assertTrue(detail_kept("0412", heard))
        self.assertFalse(detail_kept("Old Couch Road", heard))

    def test_score_and_table(self):
        rows = [{"clip": "c1", "said": "It's Bec, 0412 345 678", "details": ["Bec", "0412 345 678"],
                 "heard": {"good": {"text": "its bec oh four one two three four five six seven eight", "delay_ms": 150},
                           "bad": {"text": "its beck 0412 345 6", "delay_ms": 90}}}]
        s = score(rows)
        self.assertEqual((s["good"]["wrong_per_100"], s["good"]["details_kept_pct"], s["good"]["avg_delay_ms"]), (0.0, 100, 150))
        self.assertEqual(s["bad"]["details_kept_pct"], 0)
        self.assertGreater(s["bad"]["wrong_per_100"], 0)
        self.assertLess(table(s).index("good"), table(s).index("bad"))


if __name__ == "__main__":
    unittest.main()
