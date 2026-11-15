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

One square is **5 yards**, yielding a 50×100-yard grid. **Placeholder, not UFA data:** baseline completion is `1/(1+exp((5*d-60)/20))`, with d in squares. The 60-yard midpoint and 20-yard slope scale are illustrative assumptions, not fitted professional statistics. Defender effects implement the specified formula exactly. At zero defender/receiver distance the directional cosine is defined as 1; at zero throw distance it is also 1, avoiding undefined angles.

Public-data reconnaissance on 2026-11-15 found [official UFA API documentation](https://www.docs.ufastats.com/) (the accessible page is a JavaScript shell) and a [CMU UFA pass-completion project](https://www.stat.cmu.edu/capstoneresearch/spring2024/460files/team16.html). No verified downloadable distance/completion table was obtained during this build. The placeholder is deliberately retained rather than claiming invented UFA numbers. Replacing it requires a separately verified raw data snapshot and fit.

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
