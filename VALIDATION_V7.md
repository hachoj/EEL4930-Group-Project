# v7: full-game model and validation

This version plays games to 10 points. A team uses the same coach on offense
and defense; games alternate which team receives first. v1 is preserved in
`ultimate.py --single-possession`, including its original solver and tests.
No Claude CLI calls are made by this validation; no pushes or writes to
`outputs/` are part of this change.

## Rules and defense

The field, UFA curve, receiver pressure, one-square moves, collision reservations,
and force-flick seal are inherited from v1. On an incomplete throw, offense
changes: a drop is picked up at the receiver, and a block/interception at the
responsible defender. All coordinates rotate `(x,y) -> (9-x,19-y)` when teams
exchange roles, so offense always attacks +y. The new holder is selected from
the former defenders and placed at the pickup spot. The old receiver, if it
occupies that spot, is displaced to the nearest vacant square (distance, then
lexicographic tie break). This is an explicit pickup administration exception,
not an ordinary move. Other player positions persist. After a score the other
team receives with offense in rows 0–2 and fresh nearest-distance marks.

There are **no stall turnovers**. `--max-hold K` defaults to 3: the Kth offensive
decision since taking possession or catching must throw. Offense hold increments
the counter; defense leaves it unchanged; a catch resets it to zero. Every
coach follows this rule, including invalid-LLM fallback. A configurable 20,000
side-turn game cap is only a bug guard. If reached, the game is explicitly
unfinished, with a safety-cap flag, and no invented turnover or winner.

Each defender independently chooses tight-front, tight-behind, trail,
poach-lane, poach-deep, double-B or double-C. Poach-lane targets the midpoint
between its assigned player and the disc; poach-deep targets that player's x
and at least row 16; double targets one square in front of B/C. Any pair can
swap marks before positioning. The Calculator enumerates the full Cartesian
product: **4 mark permutations × 7³ modes = 1,372 joint defense actions**.
There is at most one reciprocal pair switch per turn; all three pair choices
are included, and no combinations within this action definition are pruned.
The 300 offense actions remain unchanged. Switches persist in concrete marks
through catches. All positioning is realized as a legal one-square step.

Scripted switches two nearby crossing marks when the nearest bijection changes;
poaches when its mark is more than seven squares from the disc; its holder
marker doubles a nearby receiver; otherwise it plays tight-front. Its offense
keeps the v1 forward-progress probability threshold and must choose the best
available throw at K, even if all receivers are behind. LLM menus explicitly
list all modes plus reciprocal switches; choosing a switch puts that defender
in tight-front around the new mark. The parser requires reciprocal switches,
accepts the tactical names and excludes hold at K. The prompt includes the
score, counter and current lane-adjusted throw probabilities. Calls are sequential
inside each process/game, cached by complete prompt and model; invalid replies
retry once then use a legal Scripted action. CLI failures propagate.

## Lane and interception model

Let `p0` be the UFA logistic probability including the configured break
multiplier. Let `R = 1 - product_j(1-h_j)` be the unchanged v1 receiver-pressure
failure probability. For each defender, project its location onto the throw
segment: projection parameter `t_j` and perpendicular segment distance `l_j`.
The additional lane hazard is

`L_j = 0.06 max(0, 1-l_j/1.5) 1{0.1 < t_j < 0.98}`.

Thus `p_catch = p0 (1-R) product_j(1-L_j)`. A defender behind the receiver has
no lane hazard; one four squares before the receiver on the segment has full
lane hazard even when both are beyond the receiver-pressure radius. Endpoint
exclusion avoids adding lane pressure to a defender directly beside the marker
or exactly at the receiver. The maximum extra hazard of one lane defender is
six percentage points conditional on surviving the other factors. This is an
assumed modest lane effect, not another UFA fit.

Failures are disjoint masses summing with `p_catch` to one: drop mass `1-p0`;
receiver-pressure block mass `p0 R`, assigned to the nearest defender; then
successive lane block masses `p0(1-R)L_j product_{i<j}(1-L_i)` in D1–D3 order.
The simulator first samples completion and, conditional on failure, samples
these masses to determine the turnover spot. The D-index order only assigns
credit when multiple hazards overlap; it does not change total completion.
Receiver pressure is consequently classified as block/interception, and base
UFA failures as drops/other incompletions. This division is a simulator
assumption: the UFA curve itself does not identify failure causes.

## Calculator objective and restart approximation

In plain language, gaining a point has value, but handing the opponent a short
field costs more than handing it a long field. The Calculator repeatedly solves
for both effects together. It discounts distant points so this feedback has a
unique numerical solution. It optimizes expected discounted point differential,
not the exact probability of winning a finite race to 10.

There are 30,375 base states per side (the existing 3×5 offensive zones and
per-receiver coverage labels), now with K explicit hold-counter states:
`2 × 30,375 × K` nonterminal states. At default K=3 this is **182,250 states**.
Counter-independent sampled movement matrices are shared by all counters.
Transition sampling uses eight representatives per base state by default,
with the original biased proposal distribution and seed 1201; `--samples 30`
is available. This is a sampling-cost choice, not a convergence claim.

Write `V_c^O(s)` and `V_c^D(s)` from the current offense's point of view. Set
`gamma=0.97` per side decision. Ordinary moves have continuation
`gamma V_{c'}^{other-side}(s')`; hold sets `c'=c+1`, defense preserves c,
and non-scoring catches set c to zero. Terminal continuations are

`score: +1 - gamma V_0^O(G)`

`failure at z: -gamma V_0^O(T(mirror(z)))`.

Here G is the sampled abstraction of a fresh row-0 goal-line start. T projects
a new possession at the turnover location to a representative restart formation.
It first maps the mirrored pickup spot to one of the 15 field zones, takes its
center, then constructs receivers two/three squares ahead and nearby defenders
with the force seal. The abstract failure transition stores the 15 possible
restart columns, separately for the receiver drop and each defender block.
Concrete refinement uses the actual throw probabilities and actual endpoint
zone, but evaluates that same projected opponent restart value. **Concrete
play does not reset to this formation**: it preserves players through the flip.
This approximation omits the new team's inherited spacing. It preserves
turnover-location value at zone resolution and is a limitation to test later,
not an exact representation of every opposing possession.

Bellman backups maximize over offense actions and minimize over defense actions,
excluding all hold actions at counter K−1. Score/failure probabilities sum to
one, max/min are nonexpansive, and every continuation derivative has absolute
coefficient at most gamma. Therefore the combined backup is a sup-norm
contraction, including the negative opponent continuations. We iterate from
zero to residual below `1e-7`; a residual r bounds value error by
`r/(1-gamma)`. This is a simultaneous discounted fixed point, rather than
substituting the old reachability value once. Policies evaluate every concrete
joint action against this fixed point. The omitted exact geometry, assignments,
restart spacing and finite target score remain abstraction/objective limitations.

## Reproduction

```sh
uv run python -m unittest -v
uv run python full_game.py --samples 8 --team0 Calculator --team1 Scripted --n 20 --jobs 2 --rebuild
uv run python full_game.py --samples 8 --team0 Calculator --team1 Calculator --n 20 --jobs 2
uv run python audit_v7.py
```

Only trusted local solver pickle caches should be loaded. Matchup histories and
summaries, solver counts/timings and the audit are in `outputs_dev/v7/`.
The process runner loads one solver per worker and alternates receiving first;
there are no thread-parallel decisions within a game. Changing K or sample
count requires a matching cache or `--rebuild`.

## Actual measured output

Unit-test output (29 legacy tests retained, 17 v7 tests):

```text
----------------------------------------------------------------------
Ran 46 tests in 0.605s

OK (skipped=2)
```

The two skips are optional legacy recorded-artifact checks; all 44 executed tests pass.
V7 checks cover every defense action, reciprocal switches, poach/double parsing,
lane-versus-behind ordering at equal distance, probability mass, pickup spots,
mirroring, score restarts, forced throws and absence of stall turnovers,
fixed-point convergence/contraction, and batched concrete-policy equivalence.

Measured solver output:

```json
{
  "states": 182250,
  "states_per_side": 91125,
  "base_states": 30375,
  "actions_offense": 300,
  "actions_defense": 1372,
  "samples_per_state": 8,
  "max_hold": 3,
  "gamma": 0.97,
  "build_seconds": 178.6262520410237,
  "solve_seconds": 324.4042402500054,
  "iterations": 404,
  "residual": 9.786662846789085e-08,
  "error_bound": 3.262220948929692e-06,
  "convergence": "discounted max/min Bellman contraction; hold counter explicit"
}
```

Build: **178.63 s** (2.98 minutes). Solve: **324.40 s** (5.41 minutes).
Maximum transition row-mass error: 4.440892098500626e-16.
Independent saved-value Bellman residual: 9.49306289133034e-08.

Seeds 1700–1719, ten receiving starts per team, target 10, K=3, jobs=2:

Pairing | Team-0 wins | Points/possession (team 0, team 1) | Completion | Mean side turns | Safety caps
---|---:|---|---:|---:|---:
Calculator vs Scripted | 16/20 | 0.5316, 0.2135 | 78.66% | 389.50 | 0
Calculator vs Calculator | 11/20 | 0.3878, 0.4111 | 82.23% | 628.55 | 0

Final-score distributions (team 0–team 1, counts):

```json
{
  "Calculator_vs_Scripted": {
    "10-0": 5,
    "10-1": 4,
    "10-2": 3,
    "10-3": 1,
    "10-5": 1,
    "10-7": 1,
    "10-8": 1,
    "3-10": 1,
    "6-10": 1,
    "7-10": 1,
    "9-10": 1
  },
  "Calculator_vs_Calculator": {
    "0-10": 3,
    "1-10": 1,
    "10-1": 1,
    "10-4": 4,
    "10-5": 1,
    "10-7": 4,
    "10-8": 1,
    "2-10": 1,
    "4-10": 1,
    "6-10": 1,
    "8-10": 1,
    "9-10": 1
  }
}
```

All **40 games** completed at exactly 10 points for the winner. The audit checks
every history for overlap, bijective marks, mandatory throws and mirrored pickup
spots; every possession ends only by score, drop or interception. Per-possession
throws/completions sum exactly to game totals. Four complete histories (two per
pairing) were reproduced exactly in serial from the parallel outputs.

Pooled completion: **80.61%**, across 4461 attempts.
This is materially below raw UFA 94.09%; the existing receiver-pressure layer
adds defensive failure to a curve already fitted to defended throws, and forced
throws can select lower-quality attempts. The extra lane hazard is modest, but
the overall concrete game is **not calibrated to reproduce UFA completion**.
No calibration claim or real-game guarantee is made. Eight samples per state
and the restart-formation approximation are further model limitations.

For a Haiku-vs-Calculator game to 10, replacing one coach in Calculator self-play
gives **314.3 decision calls/game on average**, observed counterfactual range
**133–575**. This counts both its offense and defense turns (mean total game
length 628.55 side turns). Expect roughly **3,143 calls for ten games** before
cache reuse or invalid-answer retries; one retry can double requests per decision.
Actual Haiku tactics may change game length. Calculator-vs-Scripted gives a
shorter-game reference of 194.9 calls (87–352). No LLM calls were executed.

Files: `full_game.py`, `test_full_game.py`, `audit_v7.py`; local data are
`outputs_dev/v7/{solver.json,solver.pkl,audit.json,tests.log,build.log}`, and
`{Calculator_vs_Scripted,Calculator_vs_Calculator}_{games,summary,run}.json`.
Cached final-run wall times were 6.37 s and 15.08 s respectively while the two
matchups ran concurrently; these are not isolated throughput benchmarks.
