# 3v3 Ultimate: sampled stochastic abstraction versus Claude

Local research prototype; **the full Haiku round-robin has not run** because the installed Claude CLI is unauthenticated (`Not logged in · Please run /login`). The checked-in results are a 2×2 Calculator/Scripted smoke experiment, not LLM evidence. N=3 is a deliberately small pilot, not adequate power for substantive performance claims.

## Run

Python is pinned to 3.12; dependencies are locked by uv. ffmpeg must be on PATH.

```sh
uv sync
uv run python -m unittest -v
uv run python ultimate.py --n 3 --model haiku
# Same pipeline, only model switch (not executed here):
uv run python ultimate.py --n 3 --model opus
# Auth-independent 2x2 validation:
uv run python ultimate.py --n 3 --no-llm
```

Authenticate your Claude CLI first. The full 3×3 uses the same three seeded starts in each matchup, four worker threads, and disk caching keyed by model and full prompt. A failing authentication preflight stops the run; it cannot silently label fallback policies as Haiku. Malformed choices are retried once then stationary hold. Commands overwrite the summary/demo outputs; preserve runs in separate copies before comparing models. Cached successful responses are retained. A full uncached pilot can require up to 450 LLM moves plus retries; wall time is recorded in outputs/run.json after completion. There is no measured Haiku wall time yet.

## Rules and explicit conventions

Coordinates x=0..9, y=0..19; scoring catches have y>=17. Each individual side move counts toward the 30-turn budget. Offense starts. Receiver movement occurs before the throw; a catch on turn 30 takes precedence over timeout. Players may overlap (no collision rule was specified). No score merely for carrying the disc into an endzone. Initial positions are seeded and shared across matchups. Identical players are canonicalized by moving the new holder into index zero after a catch. Receiver labels may permute under this symmetry.

One square is **5 yards**, yielding a 50×100-yard grid. **Placeholder, not UFA data:** baseline completion is `1/(1+exp((5*d-60)/20))`, with d in squares. The 60-yard midpoint and 20-yard slope scale are illustrative assumptions, not fitted professional statistics. Defender effects implement the specified formula exactly. At zero defender/receiver distance the directional cosine is defined as 1; at zero throw distance it is also 1, avoiding undefined angles.

Public-data reconnaissance on 2026-11-15 found [official UFA API documentation](https://www.docs.ufastats.com/) (the accessible page is a JavaScript shell) and a [CMU UFA pass-completion project](https://www.stat.cmu.edu/capstoneresearch/spring2024/460files/team16.html). No verified downloadable distance/completion table was obtained during this build. The placeholder is deliberately retained rather than claiming invented UFA numbers. Replacing it requires a separately verified raw data snapshot and fit.

## Abstract game and scientific limits

3 lanes × 4 equal five-row depth bins per offensive player; nearest-defender label for each non-holder is close-in-front (distance <3 and nonnegative thrower dot product), close-behind, or far. Canonical holder zero reduces the original 46,656 position/holder/label combinations by a factor of three. There are **15,552 states per side, 31,106 including two terminal states**. Endzone cuts through the top depth bin; goal probabilities are sampled accordingly.

For each key, two independently sampled concrete representatives are conditioned by exact key equality. Sampling proposes zone-uniform offense coordinates and near-receiver or uniform defenders, then rejects mismatched keys. This is a documented proposal distribution, **not uniform over all concrete states**. All action transitions and catch probabilities are averaged over those samples. Increase `--samples` for a convergence study; two is only a functional pilot.

The Calculator solves this finite sampled game by 30 exact backward Bellman backups (max offense, min defense); finite-horizon convergence is by construction. Positive and almost-sure bounded regions use support-based alternating predecessor attractors. These are bounded-horizon regions, not unbounded almost-sure guarantees. No guarantees are asserted for the original concrete game.

Offense abstract actions: stationary hold; advance both receivers; spread toward the two far endzone corners; advance then throw to receiver 1 or 2. Defense: stationary; move each defender toward one row in front of its assigned player; behind; or cyclically switch assignments and move in front. These macros move at most one concrete square per player. The Calculator optimizes this restricted macro set. Haiku can select every concrete movement combination and throw/hold through a mixed-radix enumerated menu (243 offensive or 729 defensive choices, including duplicate boundary-clipped positions).

Regret evaluates the concrete chosen action's one-step expected abstract value against the best sampled macro Q at the remaining horizon. It is clipped at zero; epsilon=0.02. **This is a macro-comparator diagnostic, not regret against every legal concrete action**, and sample noise means Calculator moves can show nonzero regret. Results pool both sides' moves per game. Scripted offense advances receivers and throws to the largest catch probability if >=0.65; defense marks in front of fixed assignments.

Rate CIs are Wilson 95%; mistake and conditional score-turn CIs are percentile bootstrap across games (2000 resamples). Gap CIs subtract the win-rate Wilson endpoints from mean abstract initial value, treating model estimates as fixed; they exclude abstraction sampling uncertainty. The predicted value assumes optimal abstract opposition; gaps against a different coach are descriptive, not pure model calibration errors. No scores means conditional turns-to-score and CI are null. Small pilot intervals can be very wide or bootstrap-degenerate. A fixed-defense external MDP solver cross-check and refined/interval abstractions from proposal.tex are not implemented.

## Outputs

`outputs/games.json` contains every recorded move, catch probability, regret and outcome; `games.csv` has game metrics; `summary.json` has rates/CIs; `solver.json` has state counts, sampling/build and solve timing and attractor sizes; `run.json` has model, N and wall time. `run.log` prints the actual results table as structured JSON. Each of win_rate, turnover_rate, mistake_rate and abstraction_gap has PNG and PDF heatmaps. `demo_<coach>.mp4` renders real recorded trajectories, with `demo_<coach>_frame.png` for inspection. Videos are generated for every available offensive coach; no LLM video exists until an authenticated run succeeds.
