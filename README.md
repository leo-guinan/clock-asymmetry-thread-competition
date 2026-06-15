# Thread Competition Harness

A local v0 workflow for choosing the best X/Twitter thread for each Clock-Asymmetry Economy claim.

## Run

```bash
cd /Users/leoguinan/Projects/semantic-axis-alt/backend/thread_competition
python3 run_competition.py --variants 4
```

Outputs:
- `outputs/candidates.jsonl` — every generated thread candidate with rubric scores
- `outputs/winners.json` — structured winners per claim
- `outputs/winners.csv` — compact review table
- `outputs/winners.md` — readable winning threads

## What v0 does

For each claim it generates 24 candidates:
- 6 lanes: mechanism_first, fight_first, steelman_first, concrete_example, paper_bridge, builder_practical
- 4 variants per lane

Then it scores:
- hook_force
- mechanism_clarity
- counter_readiness
- audience_fit
- falsifiability
- novelty_compression
- retweetability
- misread_risk, subtracted

Promotion rule:
A thread cannot win on heat alone. It must have mechanism_clarity >= 7 and counter_readiness >= 7 or it is marked `viral_but_dangerous`.

## LLM upgrade path

Keep the JSON schemas. Replace only two functions in `run_competition.py`:

1. `generate_candidate(claim, lane, variant)`
2. `heuristic_scores(thread, claim, lane)`

Generator prompt:

```text
You are generating X/Twitter thread candidates for a falsification-first public argument.

Claim:
{claim_json}

Lane:
{lane}

Rules:
- Produce exactly 6 tweets.
- Tweet 1 must stand alone under 280 chars.
- Name the mechanism, not just the vibe.
- Include the real counter without weakening the claim.
- Include a falsifier or outcome condition.
- Avoid hype, dunk bait, and moral-flattery language.
- Optimize for useful disagreement from P+, not raw outrage.

Return JSON:
{"thread": ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5", "tweet 6"]}
```

Judge prompt:

```text
You are judging two X/Twitter thread candidates for a claim competition.

P+ = founders/operators, AI eval builders, economists, infra/platform people who produce useful disagreement.
P- = outrage dunkers, generic AI hype, people who engage without mechanism.

Claim:
{claim_json}

Candidate A:
{thread_a}

Candidate B:
{thread_b}

Judge persona:
{sympathetic_target_reader | smart_hostile_critic | distribution_editor}

Pick the candidate more likely to recruit useful P+ disagreement while surviving the real counter.
Do not reward heat if it increases misread risk.

Return JSON:
{
  "winner": "A" or "B",
  "reason": "one sentence",
  "scores": {
    "hook_force": 0-10,
    "mechanism_clarity": 0-10,
    "counter_readiness": 0-10,
    "audience_fit": 0-10,
    "falsifiability": 0-10,
    "novelty_compression": 0-10,
    "retweetability": 0-10,
    "misread_risk": 0-10
  }
}
```

## Live outcome log

After publishing a winning thread, add a row with:

```csv
claim_id,winner_id,posted_url,posted_at,window,impressions,likes,reposts,replies,bookmarks,profile_clicks,follows,p_plus_replies,p_minus_replies,high_quality_disagreement,actual_strongest_counter,verdict,notes
```

Verdict options:
- hit
- mixed
- miss
- data_missing

Misses are not a blemish. They are the only thing preventing the whole exercise from becoming marketing astrology with a spreadsheet.
