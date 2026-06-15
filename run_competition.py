#!/usr/bin/env python3
"""Thread competition harness for the Clock-Asymmetry Economy claims.

v0 is deliberately local and deterministic:
- generates 24 candidates per claim from six rhetorical lanes
- scores each candidate with transparent heuristics
- runs pairwise competitions by score
- writes candidate JSONL and per-claim winners

Upgrade path: replace generate_candidate() and heuristic_scores() with LLM calls,
while preserving the same JSONL schema and outcome log. The artifact matters more
than the model. Annoying, but historically true.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "claims.json"
OUT = ROOT / "outputs"

LANES = [
    "mechanism_first",
    "fight_first",
    "steelman_first",
    "concrete_example",
    "paper_bridge",
    "builder_practical",
]

RUBRIC_WEIGHTS = {
    "hook_force": 0.18,
    "mechanism_clarity": 0.18,
    "counter_readiness": 0.14,
    "audience_fit": 0.16,
    "falsifiability": 0.12,
    "novelty_compression": 0.10,
    "retweetability": 0.08,
    "misread_risk": -0.14,
}

POWER_WORDS = {
    "trillion", "collapses", "cannot", "worst", "crowded", "frontier", "trust",
    "cheap", "expensive", "phase", "runaway", "defense", "offense", "local",
    "generator", "validation", "audits", "stationarity", "redistribute",
}
MECHANISM_WORDS = {
    "because", "when", "rate", "signal", "validation", "cost", "clock", "market",
    "position", "incentive", "sample", "substrate", "feedback", "check", "trust",
    "generator", "interference", "stationarity", "equilibrium",
}
COUNTER_WORDS = {"true", "yes", "concede", "counter", "objection", "but", "if", "unless"}
FALSIFIER_WORDS = {"if", "unless", "falsifier", "wrong", "breaks", "would change", "fails"}


@dataclass
class Candidate:
    claim_id: str
    candidate_id: str
    lane: str
    variant: int
    thread: list[str]
    scores: dict[str, float]
    total_score: float
    status: str


def load_claims() -> list[dict[str, Any]]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zλμ][A-Za-z0-9_λμ'-]*", text.lower())


def clamp(x: float, lo: float = 0, hi: float = 10) -> float:
    return max(lo, min(hi, x))


def tweet_len_penalty(text: str) -> float:
    # Soft penalty after 260 chars, hard after 300. X allows longer for Premium;
    # the hook still has to breathe in a screenshot and a reader's cortex.
    if len(text) <= 240:
        return 0
    if len(text) <= 280:
        return (len(text) - 240) / 40
    return 1 + (len(text) - 280) / 30


def make_hook(claim: dict[str, Any], lane: str, variant: int) -> str:
    title = claim["title"]
    base = claim["hook"].strip()
    counter = claim["real_counter"].strip()
    hold = claim["hold_line"].strip()

    if lane == "mechanism_first":
        openers = [
            f"The mechanism behind {claim['id']}: ",
            "This is not a moral claim first. It is a timing claim: ",
            "Strip the tribe off and the claim is simple: ",
            "The useful version is narrower than the viral one: ",
        ]
        return openers[variant - 1] + base
    if lane == "fight_first":
        openers = [
            f"Unpopular version: {title.lower()}. ",
            "The argument people will hate: ",
            "The sacred number is doing less work than you think. ",
            "Most people are arguing over the output because the generator is harder to see. ",
        ]
        return openers[variant - 1] + base
    if lane == "steelman_first":
        openers = [
            "The smart objection is real. ",
            "Concede the strongest counter first: ",
            "If this claim is wrong, it is wrong here: ",
            "Do not argue with the dumb version. The real counter is: ",
        ]
        return openers[variant - 1] + counter + " Still: " + base
    if lane == "concrete_example":
        examples = [
            "Imagine everyone tries to leave through the same narrow door at once. ",
            "A price is not a vault. It is a handshake between the next buyer and next seller. ",
            "A map drawn yesterday is useful only if the road still exists today. ",
            "A floor is boring until a tower is standing on it. ",
        ]
        return examples[variant - 1] + base
    if lane == "paper_bridge":
        openers = [
            "Paper version: ",
            "Formalize it this way: ",
            "The missing variable is time. ",
            "This is the slow-signal limit breaking. ",
        ]
        return openers[variant - 1] + base
    if lane == "builder_practical":
        openers = [
            "Builder translation: ",
            "If you are choosing what to build, start here: ",
            "The market lesson is brutal and useful: ",
            "Distribution is not the same thing as durable value. ",
        ]
        return openers[variant - 1] + base
    raise ValueError(lane)


def compress_hook(hook: str) -> str:
    # Keep v0 safe for X's 280-char hook. Compression is crude by design;
    # the LLM generator should later do this with taste, assuming it has any.
    hook = re.sub(r"\s+", " ", hook).strip()
    replacements = [
        (" because ", "; "), (" that ", " "), (" the ", " the "),
        ("It is", "It's"), ("You cannot", "You can't"),
        ("does not", "doesn't"), ("will not", "won't"),
    ]
    for a, b in replacements:
        hook = hook.replace(a, b)
    if len(hook) <= 275:
        return hook
    sentences = re.split(r"(?<=[.!?])\s+", hook)
    out = []
    for s in sentences:
        if len(" ".join(out + [s])) <= 275:
            out.append(s)
    if out:
        return " ".join(out)
    return hook[:272].rstrip() + "..."


def generate_candidate(claim: dict[str, Any], lane: str, variant: int) -> list[str]:
    hook = compress_hook(make_hook(claim, lane, variant))
    title = claim["title"]
    counter = claim["real_counter"]
    hold = claim["hold_line"]
    recruits = claim["recruits"]
    falsifier = "If the counter predicts the live replies better than the mechanism, mark the thread as a miss and rewrite the claim, not the audience."

    if lane == "fight_first":
        close = f"Fight worth picking: {recruits}. The point is not to win the dunk; it is to make the real counter show up."
    elif lane == "paper_bridge":
        close = "If this survives replies, it becomes a section of the paper. If it only gets applause, it was probably too vague."
    elif lane == "builder_practical":
        close = "Action test: choose the substrate where feedback arrives before the opportunity moves. Otherwise you are buying yesterday's map."
    else:
        close = "The thesis means nothing without the artifact: prediction first, outcome log after."

    return [
        hook,
        f"Claim: {title}.",
        f"Mechanism: {hold}",
        f"Steelman: {counter}",
        falsifier,
        close,
    ]


def heuristic_scores(thread: list[str], claim: dict[str, Any], lane: str) -> dict[str, float]:
    joined = " ".join(thread)
    ws = words(joined)
    hook_ws = words(thread[0])
    hook_power = sum(1 for w in hook_ws if w in POWER_WORDS)
    mech_hits = sum(1 for w in ws if w in MECHANISM_WORDS)
    counter_hits = sum(1 for w in ws if w in COUNTER_WORDS)
    falsifier_hits = sum(1 for w in ws if w in FALSIFIER_WORDS)
    avg_tweet_len = sum(len(t) for t in thread) / len(thread)
    overlong = sum(tweet_len_penalty(t) for t in thread)
    specificity = len(set(w for w in ws if len(w) > 6)) / max(1, len(set(ws)))

    lane_bonus = {
        "mechanism_first": (0.5, 1.2, 0.4),
        "fight_first": (1.5, -0.1, -0.2),
        "steelman_first": (0.4, 0.3, 1.6),
        "concrete_example": (1.0, 0.3, 0.2),
        "paper_bridge": (-0.1, 1.0, 0.6),
        "builder_practical": (0.7, 0.6, 0.4),
    }[lane]

    hook_force = clamp(5.2 + hook_power * 0.45 + lane_bonus[0] - tweet_len_penalty(thread[0]) * 1.2)
    mechanism_clarity = clamp(5.4 + min(mech_hits, 18) * 0.22 + lane_bonus[1] - overlong * 0.10)
    # Counter-readiness is intentionally generous when the thread explicitly
    # names the steelman. A useful thread should summon the right opponent, not
    # merely survive a cheap one.
    counter_readiness = clamp(5.3 + min(counter_hits, 10) * 0.38 + lane_bonus[2])
    audience_fit = clamp(5.4 + (1.0 if claim["tier"] <= 2 else 0.2) + (0.6 if lane in {"builder_practical", "fight_first"} else 0))
    falsifiability = clamp(5.0 + min(falsifier_hits, 7) * 0.45 + (0.8 if "If" in joined or "if" in joined else 0))
    novelty_compression = clamp(5.0 + specificity * 5.0 - max(0, avg_tweet_len - 230) / 35)
    retweetability = clamp(5.0 + hook_power * 0.25 + (0.8 if len(thread[0]) <= 240 else -0.4))

    # Misread risk: C2/C1/fight-first and missing counter language are dangerous.
    base_risk = 3.5
    if claim["id"] in {"C1", "C2", "C11"}:
        base_risk += 1.3
    if lane == "fight_first":
        base_risk += 1.0
    if lane == "steelman_first":
        base_risk -= 1.3
    if counter_readiness >= 7:
        base_risk -= 0.7
    misread_risk = clamp(base_risk + overlong * 0.08)

    return {
        "hook_force": round(hook_force, 2),
        "mechanism_clarity": round(mechanism_clarity, 2),
        "counter_readiness": round(counter_readiness, 2),
        "audience_fit": round(audience_fit, 2),
        "falsifiability": round(falsifiability, 2),
        "novelty_compression": round(novelty_compression, 2),
        "retweetability": round(retweetability, 2),
        "misread_risk": round(misread_risk, 2),
    }


def total_score(scores: dict[str, float]) -> float:
    return round(sum(scores[k] * w for k, w in RUBRIC_WEIGHTS.items()), 3)


def status_for(scores: dict[str, float], total: float) -> str:
    if scores["mechanism_clarity"] < 7.0 or scores["counter_readiness"] < 7.0:
        if total >= 5.6:
            return "viral_but_dangerous"
        return "reject"
    if total >= 6.2:
        return "publish_candidate"
    return "needs_rewrite"


def build_candidates(claims: list[dict[str, Any]], variants: int) -> list[Candidate]:
    candidates = []
    for claim in claims:
        for lane in LANES:
            for v in range(1, variants + 1):
                thread = generate_candidate(claim, lane, v)
                scores = heuristic_scores(thread, claim, lane)
                total = total_score(scores)
                cid = f"{claim['id']}-{lane}-v{v}"
                candidates.append(Candidate(claim["id"], cid, lane, v, thread, scores, total, status_for(scores, total)))
    return candidates


def write_outputs(candidates: list[Candidate], claims: list[dict[str, Any]]) -> None:
    OUT.mkdir(exist_ok=True)
    by_claim = {c["id"]: c for c in claims}
    jsonl = OUT / "candidates.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    winners = []
    for claim_id in sorted(by_claim, key=lambda x: int(x[1:])):
        pool = [c for c in candidates if c.claim_id == claim_id]
        safe_pool = [c for c in pool if c.status == "publish_candidate"] or pool
        best = max(safe_pool, key=lambda c: c.total_score)
        wins = sum(1 for other in pool if best.total_score >= other.total_score)
        losses = len(pool) - wins
        winners.append({
            "claim_id": claim_id,
            "claim_title": by_claim[claim_id]["title"],
            "winner_id": best.candidate_id,
            "lane": best.lane,
            "score": best.total_score,
            "status": best.status,
            "pairwise_wins": wins,
            "pairwise_losses": losses,
            "hook": best.thread[0],
            "thread": best.thread,
            "strongest_counter": by_claim[claim_id]["real_counter"],
            "falsifier_log_prompt": "After posting, record 2h/24h/72h metrics and whether the real counter appeared from P+ or only from P-.",
        })

    (OUT / "winners.json").write_text(json.dumps(winners, indent=2, ensure_ascii=False), encoding="utf-8")

    with (OUT / "winners.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["claim_id", "winner_id", "lane", "score", "status", "pairwise_wins", "pairwise_losses", "hook"])
        writer.writeheader()
        for w in winners:
            writer.writerow({k: w[k] for k in writer.fieldnames})

    lines = ["# Thread Competition Winners", ""]
    for w in winners:
        lines += [
            f"## {w['claim_id']} — {w['claim_title']}",
            f"Winner: `{w['winner_id']}` | score {w['score']} | {w['status']} | pairwise {w['pairwise_wins']}-{w['pairwise_losses']}",
            "",
            "Thread:",
        ]
        for i, tweet in enumerate(w["thread"], 1):
            lines.append(f"{i}. {tweet}")
        lines += ["", f"Strongest counter to watch: {w['strongest_counter']}", ""]
    (OUT / "winners.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=int, default=4, help="variants per lane; default 4 = 24 candidates per claim")
    args = parser.parse_args()
    if args.variants < 1:
        raise SystemExit("--variants must be >= 1")
    claims = load_claims()
    candidates = build_candidates(claims, args.variants)
    write_outputs(candidates, claims)
    print(f"claims={len(claims)} candidates={len(candidates)} outputs={OUT}")
    print(f"winners={OUT / 'winners.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
