# ClaimTrace

ClaimTrace asks a language model to read a short set of records, choose the conclusion they support, and identify the records needed to establish it. For example, a reporter can check a 30% decrease from two published averages or recompute the averages from individual visits. The same percentage can represent two different levels of verification.

The benchmark contains **30 matched pairs, 60 independent prompts, and six evidence skills**. A single record changes within each pair. In 21 pairs the supported answer changes. In nine it stays the same. Each skill has five pairs. The eight anchor, ten intermediate, and twelve stretch pairs are author estimates of difficulty. The [calibration report](results/README.md) gives measured performance, order sensitivity, and limitations.

| Skill | Example decision |
| --- | --- |
| Source lineage | Do two reports with different archive numbers ultimately use the same count? |
| Scope of verification | Does witnessing an opening verify the accompanying claim about wait times? |
| Measurement independence | Could two separately operated gauges share the same systematic error? |
| Denominators and coverage | What bounds follow when some passengers can be matched across routes and others cannot? |
| Causal attribution | Which effect can a comparison identify when assignment and uptake differ? |
| Conflicting records | Which figure survives a correction that restores only one entry in an earlier return? |

## Try it

From the repository root, use Python 3.9 or newer. The commands use the standard library. These examples work offline using the included model responses.

~~~sh
python3 claimtrace.py validate
python3 claimtrace.py score results/local-pilot/qwen-3B.jsonl
python3 claimtrace.py compare --table results/local-pilot/*.jsonl
python3 claimtrace.py --seed 107 compare --table results/order-check/*.jsonl
~~~

For a qualitative test with a chat interface, copy one of the [six open-response clinic prompts](pilot/prompts.md) into a fresh conversation. The [separate keys and worked scorecard](pilot/keys.md) show how to grade the response. This is a companion exercise with its own scoring rule.

## Test another model

For an endpoint that implements Chat Completions, supply its API root and model ID. Use a fresh output filename per model and seed. The HTTP runner supports macOS and Linux. The endpoint must support JSON Schema output to use the same constrained-decoding condition as the included runs.

~~~sh
mkdir -p runs
python3 claimtrace.py run --base-url http://localhost:11434/v1 \
  --model YOUR_MODEL --structured --temperature 0 --output runs/model-a.jsonl
python3 claimtrace.py score --details runs/model-a.jsonl > runs/model-a-score.json
python3 claimtrace.py compare --table results/local-pilot/qwen-3B.jsonl runs/model-a.jsonl
~~~

Every request contains one prompt in a fresh message list. The runner records raw text, requested and served model names, seed, temperature, finish reason, and benchmark fingerprint. Rerun the same command to resume. For authenticated endpoints, pass the name of a credential variable with the --key-env option. For endpoints that accept ordinary text only, omit --structured and report this as a separate condition.

To bring your own adapter, export prompts with the command below. Send only the prompt field to the model and retain the opaque ID locally. Each line of the response file must contain an id copied from the export and a response holding either the raw model text or a JSON object such as {"choice":"B","evidence":[2,4]}. Scoring requires every exported ID exactly once. Use the same seed when exporting, scoring, and comparing.

~~~sh
python3 claimtrace.py export > runs/prompts.jsonl
~~~

## Scoring

- **Evidence score.** Each packet earns zero for a wrong choice. A correct choice earns the F1 overlap between the submitted and keyed sets of record numbers, calculated as twice their intersection size divided by the sum of their sizes. If several complete proofs are keyed, the best match counts. The overall score is the mean across 60 packets. A correct choice with two of three required citations and no extras earns 0.8.
- **Verdict accuracy.** Count each correct choice, including a recognizable choice in an object with invalid citations. A single Markdown JSON fence is accepted. Record invalid or unparseable answers separately.
- **Exact grounding and strict pair pass.** Exact grounding requires the right choice and an exact accepted citation set. A pair passes only when both packets meet that rule. The matched-verdict count gives the corresponding pair score for conclusions alone.
- **Calibration.** Compare returns counts by skill and intended difficulty, per-packet outcomes, per-pair panel ranges, and matched differences. On the evidence score, a pair is near the floor when every tested configuration scores at most 0.10, and near the ceiling when every configuration scores at least 0.90. Each configuration's pair score averages its two packets. The strict-pair bands separately count unanimous failures, unanimous passes, and splits.

The default comparison output is JSON. Use --table for a compact view. The 95% descriptive intervals resample 30 whole pairs with replacement 2,000 times. A constant difference yields no interval. These intervals describe variation across the authored cases. They do not estimate variability across prompts collected from the world, repeated decoding, or models outside the panel.

## Inspect and extend

The [case bank](cases/) contains the options, both variants, keys, and explanations for auditing. In source JSON, answer is the one-based index into options and evidence lists acceptable sets of one-based record numbers. Export shuffles option order independently for each packet and excludes pair membership, skill, tier, and keys. The public bank is suitable for development and comparisons with disclosed exposure. Reserve fresh, unseen cases before making a general model-ranking claim.

~~~sh
python3 -m unittest discover -s tests -v
~~~
