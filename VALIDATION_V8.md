# v8 pulls and pressure

## Mechanics and coordinate conventions

The physical receiving goal line is between rows 2 and 3, y=2.5. Default landing
x is uniform 0..9 and y is 2 (60%) or 3 (40%), corresponding to cell-center depths
-2.5 or +2.5 yards. This coarse two-cell approximation captures the observed
median just inside the endzone but has mean -0.5 yd, rather than UFA +1.7 yd;
the grid cannot match both targets with the requested weights. Receivers line
up at [2,2], [5,2], [8,2]; pullers at x=2,5,8 on row 17. Custom inclusive depth
ranges are uniform. Picks, ties and moves are deterministic from the game seed.

The nearest receiver walks to the landing spot (others wait), using one-square
moves with the same stationary-opponent/sequential reservation rules as live
play. Once the disc is picked up, both sides run for K setup rounds (default 3):
the holder stays, receivers spread three rows ahead, defenders run toward the
corresponding receiver. This is a scripted formation run, not decisions or LLM
calls, and does not consume the live forced-throw clock. Defensive marks are
assigned after setup; no seal teleport is applied during pulls. All lineups,
landing spots, pickup identities and setup frames are saved under game `pulls`.
The first live turn starts with hold counter 0. Coach history/possession turn
indices continue to count only live decisions.

Continuity tests follow stable player identities across every consecutive
recorded setup frame, into the first live move, with no exceptions inside a
pull. Dead-ball relocation to the next point's lineup remains an explicit
between-point reset/cut, rather than recorded live movement. In live play the
inherited post-catch force seal, nearest-defender pickup on drops, and occupied
pickup-cell displacement remain administrative movement exceptions. Highlights
also intentionally cut omitted live turns; these are not claimed continuous.

## Pressure and Calculator

For P in [0,1], multiply each receiver pressure hazard by P and each lane hazard
by P: coefficient .6 becomes .6P; .06 becomes .06P. Base distance/break risk is
unchanged. Drop and defender failure masses remain disjoint and sum with catch
to one. All coaches' displayed/evaluated outcomes and realized throws use P.
Default remains 1 until an owner chooses a calibrated experiment configuration.

Every resulting start maps into the existing 30,375 base-state keys: positions
in all field zones and receiver coverage tags are already represented. Counts
remain 182,250 counter/side states at K=3, 300 offense/1,372 defense actions.
Score continuation now uses `1 - gamma mean(V_0^O(G_i))` for 128 deterministic
seeded pull/setup starts (9500..9627), replacing the single fixed goal-line
formation. This is a sampled expectation under the configured distribution.
The max/min Bellman contraction and error bound remain valid; turnover restart
geometry is still approximated as documented in VALIDATION_V7.md. Cache checks
include pressure, pull configuration, hold cap and representative sample count.

## Sweep interpretation

Targets come from `data/POINTS.md`: 4,368 conservative complete UFA points.
Hold means the receiver scores on its first possession, not eventual receiving
team point victory. Turnovers/point counts every failed possession before the
goal; possessions/point would add one. Completed passes include the goal catch.
Short-turnover goals use ALL goals as denominator, matching UFA 14.8%. Pickup
mean is measured from physical y=2.5. Unfinished trailing points are excluded
from point metrics and safety-cap counts are reported explicitly.

Selection minimizes the sum of squared *relative* errors in self-play hold
rate (target .535) and turnovers/point (.82), with equal weighting. Scripted
self-play and completion, pass counts and short-turnover goals are diagnostics.
This avoids claiming that lowering pressure alone can fix inherited turnover
pickup, spatial scale, scripted tactics or abstract model approximations.

## Actual validation and output

`uv run python -m unittest discover -q`: **59 tests, 57 passed, 2 optional
legacy artifact checks skipped**. Includes 100 seeded pull/setup continuity
checks, start-state abstraction membership, full-game seed determinism and
hold-counter reset, actual fixed-field renderer identities through pulls,
pressure probability partition/monotonicity, and all v1/v7/prompt regressions.
Syntax and `git diff --check` pass.

Sweep command:

```sh
uv run python calibrate.py --pressures .2 .6 1 --samples 1 --n 10 --target 10
```

Seeds 8100..8109, alternating first receiver; ten games to 10 for EACH coach
self-play and EACH pressure (60 games total). One representative per abstract
state is an explicit exploratory cost compromise, not the v7 eight-sample
production baseline. Every solver converged below 1e-7. Full table with each
metric next to its target: `outputs_dev/v8/near_line/calibration.md`;
raw metrics/config: `calibration.json`; recommendation: `selection.json`.
Each pressure directory contains its own trusted local pickle and build timings,
plus both self-play histories. Superseded wide-pull exploratory outputs in the
v8 root are identified by `outputs_dev/v8/README.md`.

Pressure | Coach | Points | Completion % | Hold % | TO/point | Passes/goal | Pull passes/goal | Short-turnover goals %
---|---|---:|---:|---:|---:|---:|---:|---:
0.2 | Calculator | 170 | 92.91 | 47.65 | 0.712 | 6.37 | 9.70 | 32.35
0.2 | Scripted | 158 | 88.85 | 19.62 | 2.013 | 7.99 | 12.00 | 6.33
0.6 | Calculator | 166 | 88.60 | 32.53 | 1.127 | 5.26 | 9.13 | 41.57
0.6 | Scripted | 153 | 84.23 | 7.19 | 3.072 | 6.32 | 11.91 | 21.57
1.0 | Calculator | 165 | 86.47 | 31.52 | 1.364 | 4.64 | 8.00 | 46.06
1.0 | Scripted | 171 | 83.24 | 7.60 | 3.140 | 5.72 | 11.23 | 19.30

Choose **P=0.2 for the next experiment** from this grid. Its Calculator hold
rate is 47.65% vs target 53.5%, and turnovers/point .712 vs .82. It cannot hit
both exactly: we prioritize the joint normalized discrepancy, with equal
relative weight on each, rather than privileging completion or silently tuning
to the video. It is much closer than .6 or 1 on both primary criteria. Defaults
remain P=1.0 per the requested API; pass `--pressure .2` explicitly. Completion
92.91% and 9.70 pull-origin passes/goal are close to the supplied UFA targets,
but all-origin passes/goal 6.37 vs 8.30 and short-turnover goals 32.35% vs 14.8%
remain materially different. Pressure alone does not make this a calibrated
UFA model. All 60 games finished; **zero safety-cap triggers**.

Measured builds/solves (seconds; same 182,250 states and action counts):

Pressure | Build | Solve | Iterations | Residual
---|---:|---:|---:|---:
0.2 | 24.73 | 129.10 | 422 | 9.9e-08
0.6 | 23.00 | 98.08 | 421 | 9.87e-08
1 | 22.09 | 79.60 | 422 | 9.86e-08

Demo: seed 1700, Calculator vs Scripted, target 3, P=.2: **3–0**, 181 live
turns, 41 throws, completion 90.24%, seven possessions, no cap. History:
`outputs_dev/v8/demo/Calculator_vs_Scripted_games.json`. Highlights:
`outputs_dev/v8/media/Calculator_vs_Scripted_game0_highlights.mp4`, **38.40 s**,
1,152 frames. FFmpeg reports H.264 High/yuv420p, **1920x1080, 30 fps**, AAC LC
mono 44.1 kHz. Full video+audio decode completed without errors; faststart and
metadata stripping remain enabled in the encoder.

Opened and visually checked decoded `_pull.png` (disc in flight, teams on their
lines) and `_rundown.png` (continuous cover motion, disc at receiving player,
COVER RUN label), alongside the highlights stem. `_run.png` captures pickup;
the timing JSON also includes title, scores/replays, interception holds and final.
The automated continuity check verifies movement numerically rather than
inferring it from stills. The whistle follows the recorded run-down at live
play start, then the existing paced action and generated audio continue.

No real LLM calls or pushes; no files under `data/`, `outputs/` or
`outputs_dev/v7/` changed by this work. New histories record the model so later
Haiku replays label correctly.
