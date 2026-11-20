# Local calibration

Four quantized instruction models answered each of 60 packets twice, for 480 responses. Both administrations used fresh, single-turn contexts. Changing the benchmark seed shuffled the choices and the packet order. The same underlying 30 scenarios appear in both administrations.

The evidence score awards citation overlap only when the conclusion is correct. Average the two variants and both orders within each pair before comparing models. The unit of resampling is a scenario pair. Each skill profile rests on five pairs. Differences and intervals below are descriptive, with no multiple-comparison adjustment.

The clearest observed gap was 16.8 percentage points between Gemma 3 12B and Qwen2.5 0.5B. Its paired bootstrap interval was +5.7 to +27.5 points. The 3.2-point gap between Gemma 3 4B and Qwen2.5 3B had an interval of −5.0 to +12.1 points. The benchmark separated some configurations while leaving close comparisons unresolved. Across models, using the selected citations improved the evidence score by only 0.3 to 2.8 points over citing every record with the same verdicts. Most of the observed separation therefore came from choosing the supported conclusion.

### Model scores

| Model (Q4_K_M) | Evidence, order 41 | Evidence, order 107 | Mean evidence | Correct verdicts | Strict pair passes | Same choice on reshuffled packets | Same verdicts, cite all | Invalid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5 0.5B | 21.1% | 20.6% | 20.8% | 34/120 | 1/60 | 28/55 | 19.7% | 0 |
| Qwen2.5 3B | 26.0% | 23.0% | 24.5% | 40/120 | 0/60 | 28/55 | 23.6% | 0 |
| Gemma 3 4B | 27.0% | 28.5% | 27.7% | 45/120 | 2/60 | 36/55 | 27.4% | 0 |
| Gemma 3 12B | 38.5% | 36.7% | 37.6% | 59/120 | 0/60 | 34/55 | 34.8% | 0 |

The cite-all column keeps each observed verdict and substitutes every numbered record for the model’s citations. The agreement column excludes packets with identical option order in both runs.

### Does the model follow a change in the evidence?

Both verdicts must be correct within a pair and ordering. A fixed semantic answer cannot pass a pair whose supported conclusion changes. Invariant pairs test whether a model keeps the conclusion when the edit leaves its support intact.

| Model | Changed conclusion, both correct | Invariant conclusion, both correct |
| --- | --- | --- |
| Qwen2.5 0.5B | 2/42 | 2/18 |
| Qwen2.5 3B | 2/42 | 3/18 |
| Gemma 3 4B | 4/42 | 4/18 |
| Gemma 3 12B | 4/42 | 10/18 |

### Skill profile

| Evidence skill | Qwen2.5 0.5B | Qwen2.5 3B | Gemma 3 4B | Gemma 3 12B |
| --- | --- | --- | --- | --- |
| causal attribution | 10.0% | 23.1% | 13.6% | 47.3% |
| conflicting records | 41.0% | 40.7% | 48.6% | 52.1% |
| denominators and coverage | 13.3% | 7.8% | 36.8% | 27.0% |
| measurement independence | 15.2% | 24.4% | 15.8% | 33.6% |
| scope of verification | 29.0% | 15.5% | 22.6% | 32.4% |
| source lineage | 16.4% | 35.5% | 29.0% | 33.1% |

### Intended difficulty and measured scores

| Intended tier | Qwen2.5 0.5B | Qwen2.5 3B | Gemma 3 4B | Gemma 3 12B |
| --- | --- | --- | --- | --- |
| anchor | 17.2% | 28.3% | 33.4% | 50.4% |
| intermediate | 23.0% | 30.1% | 33.2% | 34.7% |
| stretch | 21.5% | 17.3% | 19.4% | 31.5% |

### Matched comparisons

| Models | Mean difference (percentage points) | 95% paired bootstrap interval |
| --- | --- | --- |
| Qwen2.5 3B minus Qwen2.5 0.5B | +3.7 | [-5.3, +12.1] |
| Gemma 3 4B minus Qwen2.5 0.5B | +6.9 | [-2.0, +17.1] |
| Gemma 3 12B minus Qwen2.5 0.5B | +16.8 | [+5.7, +27.5] |
| Gemma 3 4B minus Qwen2.5 3B | +3.2 | [-5.0, +12.1] |
| Gemma 3 12B minus Qwen2.5 3B | +13.1 | [+5.9, +20.5] |
| Gemma 3 12B minus Gemma 3 4B | +9.9 | [-1.7, +20.3] |

### Where the benchmark separates these runs

After averaging the two orderings within each model, 1 of 30 pairs are near the evidence-score floor, 0 are near the ceiling, and 29 fall between those thresholds. Under the strict rule, 28 pairs failed in every run, 0 passed in every run, and 2 had mixed outcomes.

On 18 pairs the highest and lowest model scores differed by at least 25 percentage points. The following three had the widest observed spread. These examples were selected after scoring.

| Example pair | Skill | Qwen2.5 0.5B | Qwen2.5 3B | Gemma 3 4B | Gemma 3 12B |
| --- | --- | --- | --- | --- | --- |
| m10 | denominators and coverage | 0.0% | 0.0% | 100.0% | 0.0% |
| m08 | denominators and coverage | 0.0% | 18.8% | 18.8% | 75.0% |
| p05 | source lineage | 0.0% | 70.0% | 56.7% | 44.9% |

Citing every record yields 73.2% mean citation F1. Coupled with a uniformly random choice, that strategy earns an expected 18.3% evidence score. The expected verdict accuracy for random choice is 25%.

## Interpretation and reproducibility

The first draft exposed a floor in strict pair passing. We adopted the partial-credit evidence score after observing that floor. An independent model reviewer checked the original cases. We clarified one ambiguous matching claim, added context that readers need to exclude, and removed a sample answer from the formatting instructions. The tables use fresh responses to the revised packets. The two orders repeat the same material and these are development results. A claim about fine rankings or frontier models would require additional models and new cases held out from this development cycle.

Each model ran locally using llama.cpp build b12556, Q4_K_M weights, temperature 0, a 2,048-token context, a single slot, a 110-token generation cap, server seed 41, and JSON Schema constrained decoding. The two order seeds were 41 and 107. The schema specified an answer letter and an array of integers. It supplied no answer key or evidence numbers. All eight JSONL files contain the raw returned assistant content. To reproduce the tables, run the command below from the repository root.

~~~sh
python3 results/report.py
~~~

The tested weight revisions are [Qwen2.5 0.5B](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67), [Qwen2.5 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/tree/7dabda4d13d513e3e842b20f0d435c732f172cbe), [Gemma 3 4B](https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/tree/d0976223747697cb51e056d85c532013931fe52e), and [Gemma 3 12B](https://huggingface.co/ggml-org/gemma-3-12b-it-GGUF/tree/ec0cbabd8dbff316f659876a50202295c3c4a314). The runtime is available from the [llama.cpp release](https://github.com/ggml-org/llama.cpp/releases/tag/b12556).
