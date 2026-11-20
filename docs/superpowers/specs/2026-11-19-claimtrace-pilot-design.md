# ClaimTrace pilot design

ClaimTrace tests whether a language model can say exactly what a document supports. A reporter who calculates a 30% decrease from two published averages has checked the arithmetic. A reporter who obtains individual records and recomputes both averages has checked an additional step. Both reporters may still depend on the same underlying measurements.

## Approaches

Start with controlled fictional packets modeled on familiar reporting practices. A small edit can change the evidence available for one claim, and the answer key can identify that edit precisely. A collection of real published claims would offer more realistic language and messier judgments, but would require reconstructing what sources were available at a given time. The pilot uses the controlled approach we discussed. A later collection of real cases could test whether results carry over.

## Three paired cases

Use the same headline claim throughout this pilot. A fictional clinic reports that average waiting time fell from 50 minutes in May to 35 minutes in June. Each case adds a short excerpt with numbered sentences. Present each of the six excerpts independently in a fresh conversation with the same question:

> What does the reporting establish about the clinic's claim? Trace the evidence back as far as this packet allows. Describe any separate observation or calculation and cite the sentence numbers that support your answer.

| Pair | First packet | Second packet | Distinction to grade |
| --- | --- | --- | --- |
| Repeated reporting | A newspaper attributes the figure to the clinic's announcement. | A second newspaper quotes the first. | Both chains terminate at the announcement. The additional outlet adds no independent verification of the figure. |
| Scope of verification | A reporter quotes the clinic about a new desk opening and the decrease in waiting time. | The reporter attends the opening and quotes the clinic for the decrease. | The visit independently confirms the opening. Support for the numerical decrease stays the same. |
| Depth of verification | A reporter computes the percentage from the clinic analyst's published monthly averages. | The reporter computes the averages and percentage from the clinic staff's individual records. | Both check the arithmetic. Only the second checks the aggregation. Both rely on the clinic's observations. |

Draft both versions in comparable language. Keep the claim and question identical. Keep case IDs, pair membership, and grading notes outside the model prompt. Each key specifies the required conclusions, acceptable supporting sentence IDs, and consequential overclaims, such as inferring that a new desk caused the decrease.

## Grading and output

My proposed scoring rule is one pass per pair. For each response, a grader checks whether it states every required conclusion, supports each with an appropriate passage, and avoids contradicting the key. Accept equivalent wording. A pair passes when both responses pass independently. The model sees only its own packet and never has to describe an unseen counterpart. Preserve each response and the grader's reason for each missed criterion. Report the count out of three and the six individual outcomes. Three pairs illustrate behavior and are too few to rank models reliably.

The pilot deliverables are six prompts, separate answer keys, and one worked scorecard using explicitly labeled example responses. Check the keys against the excerpts and try plausible wrong answers before calling a case usable. The project owner can delegate all case review. The eventual release could add a model runner and grow to 30 pairs if the pilot yields clear judgments.

The builder can choose file formats and filenames. The first pilot should be usable by copying a prompt into a chat and grading the response from the key. A hosted service, API credentials, and an automated judge are outside the pilot scope.
