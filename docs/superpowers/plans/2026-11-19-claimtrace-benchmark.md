# ClaimTrace benchmark implementation plan

Goal: extend the pilot into a reproducible comparison of evidence judgments with measurable floor and ceiling effects. Build on the pilot design in docs/superpowers/specs/2026-11-19-claimtrace-pilot-design.md.

1. Write 30 controlled pairs across six evidence skills. Keep three clinic anchor pairs. Mix direct judgments, multi-step cases and challenging reconciliations. Include both changed and unchanged conclusions. Store each pair as an authored question, four plausible interpretations, and two packets with a keyed interpretation, acceptable minimal citation sets, and an explanation.
2. Export anonymous, shuffled, independently administered prompts. Preserve the free-response clinic pilot. Add deterministic structured scoring for comparisons, with separate verdict, citation and strict pair scores. Implement local-file grading and an optional HTTP model runner using Python's standard library.
3. Compare complete runs on identical prompts. Measure empirical item pass rates, flag floor and ceiling items, report skill breakdowns and paired uncertainty. Distinguish missing, malformed and substantive answers. Record the run configuration and fingerprint the bank.
4. Exercise the public commands against fixtures and check the live model options available. Retain a worked scorecard, clearly label its source, and document the remaining calibration needed before ranking real models.
