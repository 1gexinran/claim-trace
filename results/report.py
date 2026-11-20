"""Reproduce the checked-in calibration tables from both raw response directories."""
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import claimtrace as ct

HERE = Path(__file__).resolve().parent
MODELS = {
    "qwen-0.5B": "Qwen2.5 0.5B",
    "qwen-3B": "Qwen2.5 3B",
    "gemma-4B": "Gemma 3 4B",
    "gemma-12B": "Gemma 3 12B",
}
SERVED = {
    "qwen-0.5B": "Qwen2.5-0.5B-Instruct-Q4_K_M",
    "qwen-3B": "Qwen2.5-3B-Instruct-Q4_K_M",
    "gemma-4B": "Gemma-3-4B-IT-Q4_K_M",
    "gemma-12B": "Gemma-3-12B-IT-Q4_K_M",
}
ORDERS = {41: "local-pilot", 107: "order-check"}


def load_runs(bank):
    runs = {}
    for seed, folder in ORDERS.items():
        items = ct.prepare(bank, seed)
        fingerprint = ct.digest(items)
        for model in MODELS:
            rows = ct.read_rows(HERE / folder / (model + ".jsonl"))
            if any(row["config"]["bank"] != fingerprint or row["config"]["seed"] != seed or
                   row["served_model"] != SERVED[model] or row["config"]["model"] != SERVED[model] or
                   row["config"]["temperature"] != 0 or not row["config"]["structured"]
                   for row in rows.values()):
                raise ValueError(f"{folder}/{model}: unexpected run configuration")
            runs[model, seed] = ct.summarize(items, rows)
    return runs


def table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        print("| " + " | ".join(map(str, row)) + " |")
    print()


def choices_by_packet(report):
    chosen = {}
    for row in report["items"]:
        try:
            letter = json.loads(row["response"])["choice"]
            options = row["prompt"].rsplit("\n\n", 1)[1].splitlines()
            text = options[ct.LETTERS.index(letter)][3:]
        except (ValueError, KeyError, IndexError, TypeError):
            text = None
        chosen[row["pair"], row["variant"]] = text
    return chosen


def main():
    bank = ct.load_bank()
    runs = load_runs(bank)
    means = {}
    totals = []
    diagnostics = []
    skills = {}
    tiers = {}
    paired_verdicts = []
    for model, name in MODELS.items():
        first, second = (runs[model, seed] for seed in ORDERS)
        packets = first["items"] + second["items"]
        credits = {p: (first["pair_credit"][p] + second["pair_credit"][p]) / 2
                   for p in first["pairs"]}
        means[model] = credits
        skills[name] = {s: mean(x["credit"] for x in packets if x["skill"] == s)
                        for s in sorted({x["skill"] for x in packets})}
        tiers[name] = {t: mean(x["credit"] for x in packets if x["tier"] == t) for t in ct.TIERS}
        one, two = choices_by_packet(first), choices_by_packet(second)
        layouts = [{(r["pair"], r["variant"]): r["prompt"].rsplit("\n\n", 1)[-1]
                    for r in run["items"]} for run in (first, second)]
        reshuffled = [k for k in one if layouts[0][k] != layouts[1][k]]
        same = sum(one[k] is not None and one[k] == two[k] for k in reshuffled)
        cite_all = mean(ct.grade(row, {"choice": row["answer"], "evidence": list(range(1, row["count"] + 1))})
                        ["citation_f1"] if row["verdict"] else 0 for row in packets)
        paired = Counter()
        for run in (first, second):
            correct = {(r["pair"], r["variant"]): r["verdict"] for r in run["items"]}
            for p in bank:
                changed = p["variants"][0]["answer"] != p["variants"][1]["answer"]
                if correct[p["id"], 0] and correct[p["id"], 1]:
                    paired[changed] += 1
        paired_verdicts.append([name, f"{paired[True]}/42", f"{paired[False]}/18"])
        verdicts = sum(x["verdict"] for x in packets)
        strict = sum(first["pairs"].values()) + sum(second["pairs"].values())
        totals.append([name, f"{mean(credits.values()):.1%}", f"{verdicts}/120", f"{strict}/60"])
        diagnostics.append([
            name, *(f"{mean(r['pair_credit'].values()):.1%}" for r in (first, second)),
            f"{same}/{len(reshuffled)}", f"{cite_all:.1%}",
            sum(x["status"] == "invalid" for x in packets),
        ])
    print("### Model scores\n")
    table(["Model (Q4_K_M)", "Mean evidence score", "Correct verdicts", "Strict pair passes"], totals)
    print("Each model answered 60 prompts twice. The strict rule requires a correct verdict "
          "and exact citations on both variants in the same ordering.\n")
    print("### Answer order and citation selection\n")
    table(["Model", "Evidence, seed 41", "Evidence, seed 107", "Choice retained",
           "Same verdicts, cite all", "Invalid"], diagnostics)
    print("Choice retention counts the 55 packets whose options changed order. The cite-all "
          "column preserves each model's verdict and replaces its citations with every record.\n")
    print("### Does the model follow a change in the evidence?\n")
    print("Both verdicts must be correct within a pair and ordering. A fixed semantic answer "
          "cannot pass a pair whose supported conclusion changes. Invariant pairs test whether "
          "a model keeps the conclusion when the edit leaves its support intact.\n")
    table(["Model", "Changed conclusion, both correct", "Invariant conclusion, both correct"],
          paired_verdicts)
    print("### Skill profile\n")
    table(["Evidence skill"] + list(skills),
          [[s] + [f"{values[s]:.1%}" for values in skills.values()] for s in sorted({p["skill"] for p in bank})])
    print("### Intended difficulty and measured scores\n")
    table(["Intended tier"] + list(tiers),
          [[t] + [f"{values[t]:.1%}" for values in tiers.values()] for t in ct.TIERS])
    print("### Matched comparisons\n")
    contrasts = []
    for a, b in combinations(MODELS, 2):
        diffs = [means[b][p] - means[a][p] for p in sorted(means[a])]
        interval = ct.paired_interval(diffs)
        contrasts.append([f"{MODELS[b]} minus {MODELS[a]}", f"{100 * mean(diffs):+.1f}",
                          f"[{interval[0]:+.1f}, {interval[1]:+.1f}]" if interval else "Constant"])
    table(["Models", "Mean difference (percentage points)", "95% paired bootstrap interval"], contrasts)
    profile = Counter()
    strict_profile = Counter()
    for pair in bank:
        p = pair["id"]
        values = [scores[p] for scores in means.values()]
        profile["Near floor" if max(values) <= .10 else "Near ceiling" if min(values) >= .90
                else "Interior"] += 1
        passes = sum(r["pairs"][p] for r in runs.values())
        strict_profile["Always failed" if passes == 0 else "Always passed" if passes == len(runs)
                       else "Split"] += 1
    print("### Where the benchmark separates these runs\n")
    print(f"After averaging the two orderings within each model, {profile['Near floor']} of 30 pairs "
          f"fall near the evidence-score floor, {profile['Near ceiling']} are near the ceiling, "
          f"and {profile['Interior']} fall between those thresholds. Under the strict rule, "
          f"{strict_profile['Always failed']} pairs failed in every run, "
          f"{strict_profile['Always passed']} passed in every run, and "
          f"{strict_profile['Split']} had mixed outcomes.\n")
    spreads = [max(d[p["id"]] for d in means.values()) - min(d[p["id"]] for d in means.values())
               for p in bank]
    print(f"On {sum(x >= .25 for x in spreads)} pairs the highest and lowest model scores "
          "differed by at least 25 percentage points. The following three had the widest "
          "observed spread. These examples were selected after scoring.\n")
    top = sorted((p["id"] for p in bank), key=lambda p: max(d[p] for d in means.values()) -
                 min(d[p] for d in means.values()), reverse=True)[:3]
    table(["Example pair", "Skill"] + list(MODELS.values()),
          [[p, next(pair["skill"] for pair in bank if pair["id"] == p)] +
           [f"{score[p]:.1%}" for score in means.values()] for p in top])
    baseline = ct.shortcuts(ct.prepare(bank, 41))
    print(f"Citing every record yields {baseline['cite_all_mean_f1']:.1%} mean citation F1. "
          f"Coupled with a uniformly random choice, that strategy earns an expected "
          f"{baseline['random_verdict_cite_all_expected_evidence_score']:.1%} evidence score. "
          "The expected verdict accuracy for random choice is 25%.")


if __name__ == "__main__":
    main()
