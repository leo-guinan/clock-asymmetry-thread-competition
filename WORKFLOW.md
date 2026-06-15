# Twitter Thread Competition Workflow: Clock-Asymmetry Claims

Goal: for each of 13 claims, generate multiple thread candidates, evaluate them against the same audience and epistemic rubric, run pairwise competitions, and emit one winner plus a falsifier/log row before publishing.

This is not an engagement-farming machine. It is a prediction machine with a public-facing output. Worse, it will tempt us to believe the judges when they flatter our priors. Log the misses.

## Population objective

Default P+:
- founders/operators who understand capital formation and crowded markets
- AI builders/eval people who care about cheap validation
- economists/complexity people who can turn the frame into paper-quality objections
- infrastructure/platform people who understand dependable floors

Default P-:
- pure outrage accounts
- generic redistribution dunkers with no mechanism interest
- pure AI hype accounts
- crypto-style number-go-up tourists if they ignore the artifact/falsifier

Net objective:
`NTG = useful_P+ engagement - 1.5 * wrong_P- engagement`

## Candidate generation lanes

For every claim Cn, generate 24 candidates:

1. Mechanism-first: precise causal model, lower heat.
2. Fight-first: sharpest scissor, higher heat.
3. Steelman-first: opens by naming the real counter.
4. Concrete-example: starts from an image/story, then abstracts.
5. Paper-bridge: converts toward theorem/paper language.
6. Builder-practical: makes it actionable for founders/operators.

Each lane gets 4 variants. Max thread length: 7 tweets. Tweet 1 must survive alone.

## Evaluation dimensions

Score 0-10 each:
- Hook force: would the first tweet stop the right reader?
- Mechanism clarity: can a smart opponent restate the claim?
- Counter-readiness: does it invite the real counter, not strawman sludge?
- Audience fit: P+ likely to engage, P- constrained.
- Falsifiability: does it state what would change the thesis?
- Novelty/compression: not generic, not bloated.
- Retweetability: portable phrase without losing the mechanism.
- Misread risk: reverse-scored; lower is better.

Primary score:
`0.18*hook + 0.18*mechanism + 0.14*counter + 0.16*audience + 0.12*falsifiability + 0.10*novelty + 0.08*retweetability - 0.14*misread_risk`

The subtraction matters. Otherwise C2 wins every contest by becoming a worse person.

## Pairwise competition

Run round-robin within each claim:
- Judge sees claim brief, P+/P-, candidate A, candidate B.
- Judge must pick winner and give one sentence reason.
- Use three judge personas:
  1. sympathetic target reader
  2. smart hostile critic
  3. distribution editor
- Aggregate by Bradley-Terry/Elo or simple win rate for v0.

Minimum promotion rule:
- A candidate cannot win on heat alone.
- It needs score >= 7.0 on mechanism clarity and counter-readiness, or it is marked `viral_but_dangerous`.

## Human final gate

Before tweeting, fill:
- winner_id
- predicted strongest reply
- expected P+ carrier group
- expected P- contamination
- falsifier / what outcome would count as miss
- reason this is worth publishing now

## Live outcome log

At 2h, 24h, 72h record:
- impressions
- likes
- reposts
- replies
- bookmarks if available
- profile clicks/follows if available
- high-quality disagreement count
- bridge comments
- P+ replies/quotes
- P- replies/quotes
- actual strongest counter
- verdict: hit / mixed / miss / data-missing

A thread with 100K impressions and zero useful disagreement may be distribution noise. The market has enough applause pretending to be evidence.
