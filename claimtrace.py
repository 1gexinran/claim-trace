"""Export, administer and score the ClaimTrace evidence benchmark (Python 3.9+)."""
import argparse
import hashlib
import json
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
LETTERS = "ABCD"
TIERS = ("anchor", "intermediate", "stretch")
INSTRUCTIONS = (
    "Use only the fictional records below. Select the single best interpretation. "
    "Cite the smallest complete set of numbered records that establishes the whole interpretation. "
    "Include premises shared by multiple options when needed to establish the conclusion. "
    'Return a JSON object with the selected letter in "choice" and a list of supporting record numbers in "evidence".'
)


def digest(obj):
    encoded = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def prepare(bank, seed):
    if not bank or len({p["id"] for p in bank}) != len(bank):
        raise ValueError("Expected a nonempty bank with unique pair IDs")
    items = []
    for p in sorted(bank, key=lambda p: p["id"]):
        if (p["tier"] not in TIERS or len(p["variants"]) != 2 or
                len(p["options"]) != 4 or len(set(p["options"])) != 4):
            raise ValueError("Invalid pair: " + p["id"])
        for v, packet in enumerate(p["variants"]):
            lines = packet["sentences"]
            answer = packet["answer"]
            proofs = packet["evidence"]
            if (type(answer) != int or answer not in range(1, 5) or not lines or
                    not all(isinstance(s, str) and s.strip() for s in lines) or
                    not proofs or not all(valid_cites(x, len(lines)) for x in proofs)
                    or not packet["why"].strip()):
                raise ValueError("Invalid answer key: " + p["id"])
            order = list(range(4))
            random.Random(digest([seed, p["id"], v])).shuffle(order)
            options = [f"{letter}. {p['options'][i]}" for letter, i in zip(LETTERS, order)]
            passages = [f"[{n}] {s}" for n, s in enumerate(lines, 1)]
            prompt = "\n\n".join([INSTRUCTIONS, "\n".join(passages), p["question"], "\n".join(options)])
            uid = digest([seed, p["id"], v, prompt])[:16]
            items.append(dict(id=uid, prompt=prompt, pair=p["id"], variant=v,
                              skill=p["skill"], tier=p["tier"], count=len(lines),
                              answer=LETTERS[order.index(answer - 1)],
                              evidence=proofs, why=packet["why"]))
    random.Random(seed).shuffle(items)
    return items


def valid_cites(cites, count):
    return (isinstance(cites, list) and bool(cites) and
            all(type(n) == int and 1 <= n <= count for n in cites) and
            len(set(cites)) == len(cites))


def grade(item, response):
    invalid = dict(status="invalid", verdict=False, grounded=False, citation_f1=0.0)
    if isinstance(response, str):
        fenced = re.fullmatch(r"\s*```(?:json)?\s*(\{.*\})\s*```\s*", response, re.S | re.I)
        try:
            response = json.loads(fenced.group(1) if fenced else response)
        except ValueError:
            return invalid
    if not isinstance(response, dict):
        return invalid
    choice, cites = response.get("choice"), response.get("evidence")
    if choice not in tuple(LETTERS):
        return invalid
    verdict = choice == item["answer"]
    if not valid_cites(cites, item["count"]):
        return dict(invalid, verdict=verdict)
    citations = set(cites)
    overlap = max(2 * len(citations.intersection(proof)) / (len(citations) + len(proof))
                  for proof in item["evidence"])
    return dict(status="valid", verdict=verdict, grounded=verdict and overlap == 1,
                citation_f1=overlap)


def parse_rows(lines, path):
    rows = {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or "response" not in row:
            raise ValueError(f"{path}:{n}: expected id and response")
        if row["id"] in rows:
            raise ValueError(f"{path}:{n}: duplicate response ID")
        rows[row["id"]] = row
    return rows


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        return parse_rows(stream, path)


def check_ids(items, rows, require_all=True):
    expected = {item["id"] for item in items}
    extra, missing = rows.keys() - expected, expected - rows.keys()
    if extra or (require_all and missing):
        raise ValueError(f"Run does not match this export: {len(extra)} unexpected, {len(missing)} missing")


def summarize(items, rows):
    check_ids(items, rows)
    first = next(iter(rows.values()))
    config = first.get("config")
    if any(r.get("config") != config or r.get("served_model") != first.get("served_model")
           for r in rows.values()):
        raise ValueError("Response file mixes model identities or run settings")
    if config is not None and (not isinstance(config, dict) or config.get("bank") != digest(items)):
        raise ValueError("Response file was recorded against a different bank revision")
    scored = []
    groups = defaultdict(list)
    for item in items:
        raw = rows[item["id"]]["response"]
        result = grade(item, raw)
        result["credit"] = result["citation_f1"] if result["verdict"] else 0.0
        scored.append(dict(item, response=raw, **result))
        groups[item["pair"]].append(result)
    passed = {k: all(x["grounded"] for x in v) for k, v in sorted(groups.items())}
    credits = {k: statistics.mean(x["credit"] for x in v) for k, v in groups.items()}
    return dict(items=scored, pairs=passed, pair_credit=credits)


def counts(scored, pairs):
    return dict(packets=len(scored), pairs=len(pairs), pair_pass=sum(pairs.values()),
                evidence_score=round(statistics.mean(x["credit"] for x in scored), 4),
                verdict=sum(x["verdict"] for x in scored),
                grounded=sum(x["grounded"] for x in scored),
                citation_f1=round(statistics.mean(x["citation_f1"] for x in scored), 4),
                invalid=sum(x["status"] == "invalid" for x in scored))


def scorecard(report):
    scored, pairs = report["items"], report["pairs"]
    data = {"overall": counts(scored, pairs)}
    for dimension in ("skill", "tier"):
        groups = defaultdict(list)
        for row in scored:
            groups[row[dimension]].append(row)
        data[dimension] = {k: counts(v, {x["pair"]: pairs[x["pair"]] for x in v})
                           for k, v in sorted(groups.items())}
    by_pair = defaultdict(list)
    for row in scored:
        by_pair[row["pair"]].append(row)
    data["matched_verdict_pass"] = sum(all(x["verdict"] for x in group) for group in by_pair.values())
    return data


def shortcuts(items):
    """Expected scores for prompt-independent guesses and indiscriminate citations."""
    overlaps = []
    exact = []
    for item in items:
        guess = {"choice": item["answer"], "evidence": list(range(1, item["count"] + 1))}
        result = grade(item, guess)
        overlaps.append(result["citation_f1"])
        exact.append(int(result["grounded"]))
    return dict(random_verdict_rate=0.25, cite_all_mean_f1=statistics.mean(overlaps),
                random_verdict_cite_all_expected_evidence_score=statistics.mean(overlaps) / 4,
                cite_all_exact_packets=sum(exact), correct_letter_counts=dict(Counter(x["answer"] for x in items)))


def paired_interval(diffs):
    """Matched-pair bootstrap, preserving both responses within each scenario."""
    if len(set(diffs)) < 2:
        return None
    rng = random.Random(20261119)
    samples = sorted(statistics.mean(rng.choices(diffs, k=len(diffs))) for _ in range(2000))
    return [round(100 * samples[i], 1) for i in (49, 1949)]


def contrast(a, b):
    diffs = [int(a["pairs"][k]) - int(b["pairs"][k]) for k in sorted(a["pairs"])]
    credits = [a["pair_credit"][k] - b["pair_credit"][k] for k in sorted(a["pairs"])]
    return dict(a_only=diffs.count(1), b_only=diffs.count(-1),
                evidence_delta_pp=round(100 * statistics.mean(credits), 1),
                evidence_interval95_pp=paired_interval(credits),
                delta_pp=round(100 * statistics.mean(diffs), 1),
                interval95_pp=paired_interval(diffs))


def calibrate(items, runs):
    if len(runs) < 2:
        raise ValueError("Comparison requires at least two complete runs")
    pairs = sorted({item["pair"] for item in items})
    rates = {p: statistics.mean(int(r["pairs"][p]) for r in runs.values()) for p in pairs}
    def band(rate):
        return "floor" if rate == 0 else "ceiling" if rate == 1 else "split"
    evidence_pairs = {}
    for pair in pairs:
        values = [r["pair_credit"][pair] for r in runs.values()]
        low, high = min(values), max(values)
        band_name = "near floor" if high <= .10 else "near ceiling" if low >= .90 else "interior"
        evidence_pairs[pair] = dict(min=round(low, 4), max=round(high, 4),
                                    spread=round(high - low, 4), band=band_name)
    packet_rates = {}
    for idx, item in enumerate(items):
        outcomes = [r["items"][idx] for r in runs.values()]
        packet_rates[item["id"]] = dict(
            pair=item["pair"], variant=item["variant"], skill=item["skill"], tier=item["tier"],
            verdict_rate=statistics.mean(int(o["verdict"]) for o in outcomes),
            grounded_rate=statistics.mean(int(o["grounded"]) for o in outcomes),
            invalid=sum(o["status"] == "invalid" for o in outcomes))
    return dict(shortcuts=shortcuts(items), scores={name: scorecard(r) for name, r in runs.items()},
                pair_bands=dict(Counter(map(band, rates.values()))),
                pairs={p: {"pass_rate": rate, "band": band(rate)} for p, rate in rates.items()},
                packets=packet_rates, evidence_pairs=evidence_pairs,
                contrasts=[dict(a=a, b=b, **contrast(runs[a], runs[b]))
                           for a, b in combinations(runs, 2)])


def print_table(comparison):
    print("| Run | Evidence score | Correct verdicts | Exact packets | Strict pairs | Invalid |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name, card in comparison["scores"].items():
        s = card["overall"]
        print(f"| {name} | {s['evidence_score']:.1%} | {s['verdict']}/{s['packets']} | "
              f"{s['grounded']}/{s['packets']} | {s['pair_pass']}/{s['pairs']} | {s['invalid']} |")
    bands = Counter(p["band"] for p in comparison["evidence_pairs"].values())
    print(f"\nEvidence score across pairs: {bands['near floor']} near floor, "
          f"{bands['interior']} interior, {bands['near ceiling']} near ceiling.")
    base = comparison["shortcuts"]["random_verdict_cite_all_expected_evidence_score"]
    print(f"Uniformly random verdict with every record cited: {base:.1%} expected evidence score.")
    print("\nMatched evidence-score differences in percentage points (A minus B):")
    for r in comparison["contrasts"]:
        bounds = r["evidence_interval95_pp"]
        interval = f"[{bounds[0]:+.1f}, {bounds[1]:+.1f}]" if bounds else "constant observed difference"
        print(f"  {r['a']} / {r['b']}: {r['evidence_delta_pp']:+.1f}  {interval}")


def emit(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def load_bank():
    return [p for f in sorted((ROOT / "cases").glob("*.json")) for p in json.loads(f.read_text())]


def request_answer(url, key, model, prompt, temperature, timeout, structured):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        payload["temperature"] = temperature
    if structured:
        schema = {"type": "object", "properties": {
            "choice": {"type": "string", "enum": list(LETTERS)},
            "evidence": {"type": "array", "items": {"type": "integer"}, "minItems": 1}},
            "required": ["choice", "evidence"], "additionalProperties": False}
        payload["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "evidence_judgment", "strict": True, "schema": schema}}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urlopen(req, timeout=timeout) as reply:
        data = json.load(reply)
    choice = data["choices"][0]
    message = choice["message"]
    body = message.get("content")
    if body is None and message.get("refusal"):
        body = message["refusal"]
    if not isinstance(body, str):
        raise ValueError("Endpoint returned no assistant text")
    return body, data.get("model"), choice.get("finish_reason")


def administer(items, args):
    import fcntl
    url = args.base_url.rstrip("/") + "/chat/completions"
    dest = urlparse(url)
    if (dest.username or dest.password or dest.query or dest.fragment or
            not dest.hostname or (dest.scheme != "https" and
            not (dest.scheme == "http" and dest.hostname in ("localhost", "127.0.0.1", "::1")))):
        raise ValueError("Use HTTPS or a loopback HTTP base URL without credentials or query")
    config = dict(model=args.model, endpoint=url, temperature=args.temperature, seed=args.seed,
                  bank=digest(items), structured=args.structured)
    key = os.environ.get(args.key_env) if args.key_env else None
    if args.key_env and not key:
        raise ValueError(f"No value set for {args.key_env}")
    with args.output.open("a+b") as output:
        fcntl.flock(output, fcntl.LOCK_EX | fcntl.LOCK_NB)
        output.seek(0)
        lines = output.readlines()
        partial = b""
        if lines and not lines[-1].endswith(b"\n"):
            try:
                json.loads(lines[-1])
            except (ValueError, UnicodeDecodeError):
                if len(lines) == 1 or not lines[-1].startswith(b'{"id":'):
                    raise ValueError("Unrecognized incomplete run file")
                partial = lines.pop()
        rows = parse_rows(lines, args.output)
        check_ids(items, rows, require_all=False)
        if any(r.get("config") != config for r in rows.values()):
            raise ValueError("Existing run uses a different configuration")
        if partial:
            output.truncate(output.tell() - len(partial))
        elif lines and not lines[-1].endswith(b"\n"):
            output.write(b"\n")
        for item in items:
            if item["id"] in rows:
                continue
            answer, served, finish = request_answer(url, key, args.model, item["prompt"],
                                                   args.temperature, args.timeout, args.structured)
            row = dict(id=item["id"], response=answer, config=config, served_model=served,
                       finish_reason=finish)
            output.write((json.dumps(row, ensure_ascii=False) + "\n").encode())
            output.flush()
            print(f"{len(rows) + 1}/{len(items)}", file=sys.stderr)
            rows[item["id"]] = row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=41, help="prompt and option ordering seed")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export", help="write model-facing JSONL to stdout")
    sub.add_parser("validate", help="check keys and summarize the bank")
    score = sub.add_parser("score", help="grade a complete response JSONL file")
    score.add_argument("responses", type=Path)
    score.add_argument("--details", action="store_true", help="include keys and per-response results")
    compare = sub.add_parser("compare", help="compare two or more complete response JSONL files")
    compare.add_argument("--table", action="store_true", help="print a compact Markdown scorecard")
    compare.add_argument("responses", nargs="+", type=Path)
    run = sub.add_parser("run", help="query a chat completions endpoint in fresh contexts")
    run.add_argument("--base-url", required=True, help="API root e.g. http://localhost:11434/v1")
    run.add_argument("--key-env", help="name of the environment variable containing the endpoint key")
    run.add_argument("--model", required=True)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--structured", action="store_true", help="request JSON Schema constrained decoding")
    run.add_argument("--temperature", type=float)
    run.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    bank = load_bank()
    items = prepare(bank, args.seed)
    if args.cmd == "validate":
        emit(dict(pairs=len(bank), packets=len(items), skill=dict(Counter(p["skill"] for p in bank)),
                  tier=dict(Counter(p["tier"] for p in bank)), fingerprint=digest(items)))
    elif args.cmd == "export":
        for row in items:
            print(json.dumps({k: row[k] for k in ("id", "prompt")}, ensure_ascii=False))
    elif args.cmd == "run":
        administer(items, args)
    elif args.cmd == "score":
        report = summarize(items, read_rows(args.responses))
        emit(dict(scorecard=scorecard(report), **(report if args.details else {})))
    else:
        if len(set(p.resolve() for p in args.responses)) != len(args.responses):
            raise ValueError("Use a different run file for each entry")
        reports = {str(p): summarize(items, read_rows(p)) for p in args.responses}
        comparison = calibrate(items, reports)
        if args.table:
            print_table(comparison)
        else:
            emit(comparison)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit(f"Endpoint returned HTTP {error.code}: {error.reason}")
    except (ValueError, OSError, IndexError, KeyError) as error:
        sys.exit(f"ClaimTrace: {error}")
