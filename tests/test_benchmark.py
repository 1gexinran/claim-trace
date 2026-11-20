import unittest

import claimtrace as ct


PAIR = {
    "id": "p", "skill": "lineage", "tier": "stretch",
    "question": "What does the note establish?",
    "options": ["Shared logs", "Independent logs", "Both", "Unknown"],
    "variants": [
        {"sentences": ["City counted.", "Desk copied.", "Unrelated."],
         "answer": 1, "evidence": [[1, 2]], "why": "Common source."},
        {"sentences": ["City counted.", "Desk counted.", "Unrelated."],
         "answer": 2, "evidence": [[1, 2]], "why": "Separate counts."}
    ]
}


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.items = ct.prepare([PAIR], 23)

    def test_projection_and_determinism(self):
        self.assertEqual(self.items, ct.prepare([PAIR], 23))
        for item in self.items:
            self.assertNotIn("Common source.", item["prompt"])
            self.assertNotIn("stretch", item["prompt"])
            self.assertNotIn('"choice":"A"', item["prompt"])
            option = item["answer"]
            original = PAIR["variants"][item["variant"]]["answer"]
            self.assertIn(option + ". " + PAIR["options"][original - 1], item["prompt"])

    def test_grade_separates_verdict_and_grounding(self):
        item = self.items[0]
        score = ct.grade(item, {"choice": item["answer"], "evidence": [1, 2, 3]})
        self.assertTrue(score["verdict"])
        self.assertFalse(score["grounded"])
        self.assertAlmostEqual(score["citation_f1"], .8)
        score = ct.grade(item, {"choice": item["answer"], "evidence": [2, 1]})
        self.assertTrue(score["grounded"])

    def test_invalid_format_distinct_from_wrong_judgment(self):
        item = self.items[0]
        for ev in ([True], [0], [7], [1, 1], "1", []):
            self.assertEqual(ct.grade(item, {"choice": item["answer"], "evidence": ev})["status"], "invalid")
        wrong = next(x for x in "ABCD" if x != item["answer"])
        self.assertEqual(ct.grade(item, {"choice": wrong, "evidence": [1, 2]})["status"], "valid")

    def test_choice_survives_citation_error_and_markdown_fence(self):
        item = self.items[0]
        self.assertTrue(ct.grade(item, {"choice": item["answer"], "evidence": []})["verdict"])
        wrapped = '```json\n{"choice":"%s","evidence":[1,2]}\n```' % item["answer"]
        self.assertTrue(ct.grade(item, wrapped)["grounded"])

    def test_empty_or_duplicate_input_rejected(self):
        for bank in ([], [PAIR, PAIR]):
            with self.assertRaises(ValueError):
                ct.prepare(bank, 0)

if __name__ == "__main__":
    unittest.main()
