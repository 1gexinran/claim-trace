import unittest
from collections import Counter

import claimtrace as ct


class CorpusTests(unittest.TestCase):
    def test_planned_design_and_pairs(self):
        bank = ct.load_bank()
        self.assertEqual(len(bank), 30)
        skills = Counter(p["skill"] for p in bank)
        self.assertEqual(sorted(skills.values()), [5] * 6)
        self.assertEqual(sum(p["variants"][0]["answer"] == p["variants"][1]["answer"]
                             for p in bank), 9)
        for p in bank:
            a, b = p["variants"]
            with self.subTest(pair=p["id"]):
                self.assertEqual(len(a["sentences"]), len(b["sentences"]))
                self.assertEqual(sum(x != y for x, y in zip(a["sentences"], b["sentences"])), 1)
                self.assertEqual({q["tier"] for q in bank if q["skill"] == p["skill"]}, set(ct.TIERS))

    def test_full_keys_and_absence_of_key_metadata_in_export(self):
        bank = ct.load_bank()
        for seed in (41, 107):
            items = ct.prepare(bank, seed)
            self.assertEqual(len({x["id"] for x in items}), 60)
            for x in items:
                self.assertTrue(ct.grade(x, {"choice": x["answer"], "evidence": x["evidence"][0]})["grounded"])
                self.assertNotIn(x["why"], x["prompt"])

if __name__ == "__main__":
    unittest.main()
