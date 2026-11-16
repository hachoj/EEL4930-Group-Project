# 3v3 Ultimate: sampled stochastic abstraction versus Claude

Local research prototype. The owner completed the original Haiku pilot on e9446f7; the revised rules/prompt have not been run with an LLM. This revision validates only Calculator/Scripted, with N=30 per matchup. See VALIDATION.md for measured results and limitations.

## Run

Python is pinned to 3.12; dependencies are locked by uv. ffmpeg must be on PATH.

```sh
uv sync
uv run python -m unittest -v
uv run python ultimate.py --n 3 --model haiku --out outputs_haiku
# Same pipeline, only model switch (not executed here):
uv run python ultimate.py --n 3 --model opus --out outputs_opus
# Auth-independent 2x2 validation:
uv run python ultimate.py --n 30 --no-llm --samples 30 --start-depth 12 --out outputs_dev/calibrated
```

The Claude CLI must be authenticated. The full 3×3 uses the same three seeded starts in each matchup, four worker threads, and disk caching keyed by model and full prompt. A failing authentication preflight stops the run; it cannot silently label fallback policies as Haiku. Malformed choices are retried once then stationary hold. Use --out DIR to isolate runs (default outputs_dev). Commands overwrite files in that directory. Importing the module never writes outputs. Cached successful responses are retained. A full uncached pilot can require up to 450 LLM moves plus retries; wall time is recorded in outputs/run.json after completion. There is no measured Haiku wall time yet.

## Rules and explicit conventions

Coordinates x=0..9, y=0..19; scoring catches have y>=17. Each individual side move counts toward the 30-turn budget. Offense starts. Receiver movement occurs before the throw; a catch on turn 30 takes precedence over timeout. Players cannot share squares. Sequential reservations block opponents, unprocessed teammates and already moved teammates; a colliding proposal stays put. Starts put defenders 1–2 rows ahead, without overlaps. --start-depth 0 puts offense near its own goal line (y=0,1,2). The default calibrated attacking scenario uses y=12,13,14, explicitly a different experiment, to avoid degenerate scoring in only 15 offense opportunities. The 30 alternating-side-turn rule is unchanged. No score merely for carrying the disc into an endzone. Initial positions are seeded and shared across matchups. Identical players are canonicalized by moving the new holder into index zero after a catch. Receiver labels may permute under this symmetry.

One square is **5 yards** (50×100-yard grid). Baseline completion is now the 2025 UFA fit, `sigmoid(4.15701518 - 0.06417449 * d_yards)`, from 84,099 attempts in 157 games; see data/THROWS.md for inferred event semantics and missing-coordinate limitations. UFA rates already include real defense; our receiver-pressure factors add another modeling layer and may double-count pressure.

Force flick: at possession start and immediately after every successful catch (before the next turn), the fixed defender assigned to the holder is placed one square left (negative x), adjacent to the holder facing +y. If unavailable, choose the vacant field square nearest that target by Euclidean distance; ties prefer proximity to holder, then x/y lexicographic order. This placement is an explicit teleport exception to one-square movement. Afterwards the marker moves normally. The final scoring catch terminates immediately. A throw breaks if its x component is negative and exceeds sin(15°) times its total distance (more than 15° off straight forward/backward toward left). This includes lateral and backward-left throws.

Break p_catch is multiplied by `--break-multiplier` (default **1.0**). This is a **team design assumption, not a UFA estimate**; force side is absent from the data. The sensitivity grid could not meet 15% frequency and 95% completion simultaneously (see VALIDATION_V6.md). No extra penalty was selected. Scripted considers forward break targets using the same probability threshold as open throws. Calculator sampled successful successors include the seal and probability multiplier; concrete refinement retains actual fixed marks. The abstraction still omits marker coordinates/force-side geometry, so this is not an exact concrete-game solution. LLM probabilities include the penalty and the prompt explains it. Replay rings identify the holder's marker; throws are labeled BREAK/OPEN.

Reproduce: `uv run python calibrate_force.py`, then `uv run python ultimate.py --n 30 --no-llm --samples 30 --break-multiplier 1 --out outputs_dev/v6`.

## Abstract game and scientific limits

3 lanes × 5 depth bins (0–4, 5–9, 10–14, 15–16, 17–19) per offensive player; nearest-defender label for each non-holder is close-in-front (distance <3 and nonnegative thrower dot product), close-behind, or far. Canonical holder zero reduces the refined 91,125 position/holder/label combinations by a factor of three. There are **30,375 states per side, 60,752 including two terminal states**. The endzone now has its own depth bin; the original four-bin version aliased scoring and non-scoring catches.

For each key, 30 independently sampled concrete representatives are conditioned by exact key equality. Sampling proposes zone-uniform offense coordinates and distance-1/2 near-receiver defenders; far and third defenders are sampled uniformly by rejection from field squares at least three squares from both receivers, then mismatched keys and overlaps are rejected. This biases sampled defenders toward sparse coverage; it is not a realistic distribution or calibrated guarantee. This is a documented proposal distribution, **not uniform over all concrete states**. All action transitions and catch probabilities are averaged over those samples. Increase `--samples` for a convergence study; 30 is the default; this remains a proposal-distribution model rather than a concrete guarantee.

The Calculator solves this finite sampled game by 30 exact backward Bellman backups (max offense, min defense); finite-horizon convergence is by construction. Positive and almost-sure bounded regions use support-based alternating predecessor attractors. These are bounded-horizon regions, not unbounded almost-sure guarantees. No guarantees are asserted for the original concrete game.

Offense now has **300 joint abstract actions**: two independently chosen receiver intents (stay, eight compass directions, get open) × hold/throw B/throw C. Directions are relative field/zone directions realized as the best legal one-square step; get open maximizes separation from the nearest defender, with forward progress as a small tie preference. A non-stay intent chooses a moving legal neighbor when available. Defense has **27 joint actions**: independently tight-front/tight-behind/trail for each fixed mark, including the holder's marker. Collision reservations can force a player to stay if another proposal blocks it. All player proposals are applied in the same turn.

The sampled game uses SciPy sparse stochastic matrices, averaging the same 30 representative states for every action. Bellman backups and support attractors solve that sampled finite game exactly; transition estimation and abstraction remain approximations. The Calculator concretely evaluates every joint action's exact immediate probability followed by the abstract continuation value. This is a concrete refinement of the abstract value function, rather than a pure abstract policy lookup. Equal offense values prefer forward receiver progress and then movement. `abstract_alternatives` contains all 300/27 sampled Q values, in `joint_calculator.OFF_ACTIONS`/`DEF_ACTIONS` order. `solver.pkl` is an ignored local analysis cache (load only caches you trust).
 The LLM sees named A/B/C and D1–D3 coordinates, distances, receiver movement options with catch probabilities, and readable directions. It returns named movement fields and hold/throw_B/throw_C. Colliding choices are retried once; fallback is stationary hold. The CLI uses --output-format json and reported model identifiers are saved in run.json when available (an empty list means unavailable or no LLM calls).

Regret evaluates the concrete chosen action's one-step expected abstract value against the best sampled joint-action Q at the remaining horizon. It is clipped at zero; epsilon=0.02. **This is a joint-action-comparator diagnostic, not regret against every legal concrete action**, and sample noise means Calculator moves can show nonzero regret. Results pool both sides' moves per game. Scripted offense advances receivers and throws to the largest catch probability among strictly forward targets if >=0.65 (a revision to prevent repeated backward possession cycling); defense marks in front of fixed assignments.

Rate CIs are Wilson 95%; mistake and conditional score-turn CIs are percentile bootstrap across games (2000 resamples). Gap CIs subtract the win-rate Wilson endpoints from mean abstract initial value, treating model estimates as fixed; they exclude abstraction sampling uncertainty. The predicted value assumes optimal abstract opposition; gaps against a different coach are descriptive, not pure model calibration errors. No scores means conditional turns-to-score and CI are null. Small pilot intervals can be very wide or bootstrap-degenerate. A fixed-defense external MDP solver cross-check and refined/interval abstractions from proposal.tex are not implemented.

## Outputs

`<out>/games.json` contains every recorded move, catch probability, regret and outcome; `games.csv` has game metrics; `summary.json` has rates/CIs; `solver.json` has state counts, sampling/build and solve timing and attractor sizes; `run.json` has model, N and wall time. `run.log` prints the actual results table as structured JSON. Each of win_rate, turnover_rate, mistake_rate and abstraction_gap has PNG and PDF heatmaps. `demo_<coach>.mp4` renders real recorded trajectories, with `demo_<coach>_frame.png` for inspection. Videos are generated for every available offensive coach; no LLM video exists until an authenticated run succeeds.

## Fixed-mark revision

Run `uv run python ultimate.py --n 30 --no-llm --out outputs_dev/v3`.
Defensive assignments are a nearest-distance bijection at possession start and follow player identity through catches. Calculator actions position around that mark; Scripted marks tight-front; the LLM prompt names each assignment. The compressed model does not store assignments, so representative sampling uses a nearest bijection and concrete policy refinement uses the actual fixed marks.

Replays now contain synchronized concrete and abstract panels, landscape grass pitch, jersey labels, throw/result annotations, smooth steps and a two-second final hold. `--hide-marks` hides defensive assignment links. MP4s use H.264 yuv420p, `+faststart`, and metadata stripping. `calculator_view.{png,pdf}` compares the same moment; it shows the actual 3×5 zones after the endzone-alias repair. Detailed measured results are in `VALIDATION_V3.md`.

## Symmetric lanes and coverage rendering (v4)

Lane cells are x=0–2, 3–6, 7–9 (3/4/3); depth bands remain y=0–4, 5–9, 10–14, 15–16, 17–19. The only endzone is y=17–19. Sampler and mapping share the lane function. Abstract red D icons indicate each receiver's nearest defender front/behind relative to the holder; far has no icon. No holder coverage or exact defender positions are encoded. These are coverage icons, not fixed-mark identities.

Every action applies all player proposals before resolving collisions, and replay interpolation updates entire team arrays at the same fraction. Calculator uses the complete Cartesian product of its receiver intents and defender positioning modes (see above). LLM named fields independently choose both receiver/all defender moves. Scripted now independently selects open-space cuts with forward progress rather than repeatedly walking into a fixed marker. `movement_report.py` compares identity-aligned recorded moves (including post-catch relabeling).

Measured joint-action results and remaining abstraction limits: `VALIDATION_V5.md`. Reproduce with `uv run python ultimate.py --n 30 --no-llm --samples 30 --out outputs_dev/v5`. No rule, start, catch-curve or Scripted policy changes were made in v5.

## v7: full games (v1 preserved)

Use `full_game.py` for v7; `ultimate.py --single-possession` retains the v1 rules,
solver and outputs. v7 runs go in `outputs_dev/v7/` by default. No LLM is used
unless a team is explicitly `LLM`. Each team uses its coach on both sides.

```sh
uv run python -m unittest -v
uv run python full_game.py --team0 Calculator --team1 Scripted --n 20 --jobs 2
uv run python full_game.py --team0 Calculator --team1 Calculator --n 20 --jobs 2
# Owner runs this (not run during implementation):
uv run python full_game.py --team0 LLM --team1 Calculator --n 10 --jobs 4 --model haiku
```

`--max-hold 3` counts offensive decisions since gaining the disc. The third
must throw; successful catches reset the counter. `--max-hold 5 --rebuild`
changes the rule and rebuilds its explicit counter states. There are **no
stall turnovers**. `--safety-cap 20000` is a game-level bug guard; an interrupted
game has `finished=false` and `safety_cap_triggered=true`, never a fabricated
winner or turnover. Games alternate which team receives first. Final histories,
per-possession throw/score stats and summaries are saved under matchup-specific
names. The runner uses separate processes; decisions and LLM requests within
each game are sequential. LLM answers are cached by model and complete prompt;
malformed replies retry once, then use the legal Scripted move. CLI failures
propagate instead of silently impersonating an LLM. `--model haiku|opus` remains.

The v7 Calculator has 300 offense actions and **1,372 defense actions**: seven
independent positioning modes for each defender, for each of four mark
permutations (no switch or any one of the three reciprocal pair switches).
Modes are tight-front, tight-behind, trail, poach-lane, poach-deep, double-B,
double-C. No combinations are pruned. Movement and reservations remain one
square; switches change assignments rather than teleporting players. The
force-flick seal after catches retains v1's explicit teleport exception.

Turnovers rotate all players by 180 degrees and exchange teams, placing the new
holder at the receiver for drops or at the blocking defender for interceptions.
If the old receiver occupies that pickup spot it moves to the nearest vacant
square; this explicit administrative exception prevents cross-team overlap.
After scores the other team starts in rows 0–2. Coordinates always attack +y.

v7 adds a modest lane hazard to the unchanged UFA/receiver-pressure curve.
The new discounted Calculator values scoring and the opponent's next possession;
it is solved to a measured Bellman residual, rather than the v1 30-turn horizon.
`VALIDATION_V7.md` describes the math, restart approximation, timings and measured
full-game baselines. The default uses eight representatives per base state;
`--samples 30 --rebuild` increases transition sampling. Caches are trusted local
pickle files; rebuild when implementation or configuration changes. The sampled
abstraction omits exact player positions and mark identities, so solving it does
not establish guarantees for the concrete game.

### Full-game media

```sh
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json --game-index 0
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json --game-index 0 --highlights 12
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json outputs_dev/v7/Calculator_vs_Calculator_games.json --figures
```

Media defaults to `outputs_dev/v7/media/`. `--figures --video` makes both.
Indices are zero-based across the supplied files. Video is a fixed-camera,
1920×1080, 30 fps broadcast with both endzones, stable team colors and jersey
identities, eased motion, throw arcs, disc trails, score bug, title/legend and
final cards. Turnovers reverse attack direction without rotating the camera.
After points, teams switch ends: the new receiver attacks the previous scorer's
direction. Visual pulls do not alter simulation starts. Slow replays follow goals
and interceptions. Encoding is H.264/yuv420p, faststart, with metadata stripped.

`--highlights N` shows every goal/turnover, approaching each finish with up to
min(N,4) side turns; routine stretches are skipped. Playback is budgeted below
90 seconds for ordinary games to 10, including pulls and replays. Full mode
retains every side turn at 0.4 seconds plus cards, pulls and slow replays.
Decoded title/pull/turnover/goal-replay/final PNG extracts and a timing JSON are
written alongside each MP4. Use `--out outputs_dev/v7/media/broadcast` to keep
broadcast exports separate from older media.

Histories omit tactic names. Baseline modes are reconstructed without a solver:
Scripted's deterministic rules, Calculator's first matching joint action.
Identical realized positions and marks have identical continuation value, so
Calculator's first-minimum tie break identifies the selected matching action.
Switches are separate assignment-change counts (overlap positioning modes).
For LLM histories, tactic modes are reported as unknown: positions alone cannot
recover its intended action. Figures pool supplied games, including both teams
in self-play; PPP denominators are completed possessions.


### v8 real pulls and pressure calibration

`full_game.py` now defaults to `outputs_dev/v8/`. Each point starts with receivers
on row 2 and pullers on row 17. Default pickup is uniform across x, with 60/40
probability on rows 2/3 (the own goal line is the boundary at y=2.5). Override
with `--pull-min LO --pull-max HI`; nondefault ranges are discrete uniform.
`--pull-run-turns 3` controls the cover/setup run after pickup. Setup is scripted,
not coach decisions: the nearest receiver legally walks to the landing square,
then holds while teammates spread and pullers run down. Every setup frame is
saved under `pulls`, independently of the coach-turn history, and the first
live hold counter is zero. No pull/setup movement exceeds one grid square.

`--pressure P` (0..1, default 1) multiplies both the receiver-pressure 0.6
coefficient and lane hazard 0.06 coefficient. UFA distance probability is
unchanged. Use a separate cache/output directory per P, sample count and pull
configuration; incompatible caches are refused. Processes run one game at a
time; the game sets process-local pressure for Scripted and LLM option tables,
while Calculator evaluations carry their own pressure explicitly. v1 is untouched.

```sh
uv run python calibrate.py --pressures .2 .6 1 --samples 1 --n 10 --target 10
uv run python full_game.py --pressure .2 --target 3 --n 1 --samples 1 --out outputs_dev/v8/demo
uv run python render_full.py outputs_dev/v8/demo/Calculator_vs_Scripted_games.json --highlights 4 --out outputs_dev/v8/media
```

`calibrate.py` writes histories, cache/timings, a sweep table and selected pressure
with target comparisons. Selection uses equal squared relative errors in
Calculator self-play hold rate and turnovers/point. Other statistics are diagnostics,
not hidden selection criteria. A small sampled model/grid and ten games per
pairing give exploratory evidence; this does not establish a calibrated model.
The renderer uses recorded pull flight/pickup/run-down frames for v8, and retains
presentation-only pulls for legacy files. New action names replace tactic guesses.
