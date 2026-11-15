# Joint-action Calculator: N=30 per matchup

Offense | Defense | Wins | Win 95% CI | Turnovers
---|---|---|---|---
Calculator | Calculator | 73.3% | 55.6%–85.8% | 26.7%
Calculator | Scripted | 66.7% | 48.8%–80.8% | 33.3%
Scripted | Calculator | 50.0% | 33.2%–66.8% | 50.0%
Scripted | Scripted | 56.7% | 39.2%–72.6% | 43.3%

Coach | Side | v4 players/turn | v5 players/turn | v5 turns
---|---|---|---|---
Calculator | offense | 0.618 | 1.867 | 805
Calculator | defense | 0.830 | 2.944 | 432
Scripted | offense | 2.000 | 2.000 | 183
Scripted | defense | 1.027 | 1.706 | 436

Balanced-opposition offense difference: 16.7%; seed-cluster paired bootstrap 95% interval 3.3% to 30.0%.

All 327 transition matrices have row sum one (maximum absolute error 5.55e-16). Batched concrete policy independently reproduced all 120 complete histories exactly in 7.36s using the cached model.

State/action counts, build and solve timing:
```json
{
  "states": 60752,
  "states_per_side": 30375,
  "actions_offense": 300,
  "actions_defense": 27,
  "samples_per_state": 30,
  "build_seconds": 165.81635262497002,
  "solve_seconds": 7.6126187079935335,
  "horizon": 30,
  "positive_30": [
    30375,
    30375
  ],
  "almost_sure_30": [
    0,
    0
  ],
  "convergence": "exact 30 finite-horizon Bellman backups of sampled joint-intent game"
}
```

## Interpretation and limitations

The Calculator now outscores Scripted against each same defense on the shared 30 starts: 22 vs 15 scores against Calculator, 20 vs 17 against Scripted. Balanced across defenses: 42/60 (70.0%) vs 32/60 (53.3%). Individual Wilson intervals overlap; the seed-cluster paired interval above is descriptive evidence on this benchmark, not a universal superiority claim or a held-out evaluation.

The previous five offense macros tied receiver movement together; neither receiver could independently cut around a mark, and only forward-moving throws existed. The expanded Cartesian product includes independent lateral/backward/diagonal cuts, stationary catches, and separation-seeking cuts. Average Calculator receiver movement rises from 0.618 to 1.867 players per offense turn; defense rises from 0.830 to 2.944. Non-stay intents move when a vacant neighbor exists, with sequential reservations preventing collisions. Defense may have to stay if another proposal reserves its available cell. Fixed mark identity is preserved by the unchanged possession logic.

Scripted logic is unchanged; its different average defense movement reflects the different opposing paths and game durations. Scripted vs Scripted remains exactly 17/30 scores. Rules, starts, placeholder catch curve, horizon and seeds were not recalibrated for this result.

All 300 offense actions are independent receiver intents × hold/B/C; all 27 defense actions independently choose tight front, tight behind or trail about each assigned mark. Front means toward the thrower; the holder is marked from downfield. Trail targets the current marker side of its mark. Compass intents select a legal one-square step best aligned with that field/zone direction; get-open selects separation from the nearest defender (the defender relation retained in the abstraction). Every action uses the same 30 representatives of its abstract state (common random numbers). No transitions are pruned to make solving faster. Sparse matrices sum duplicate successors exactly up to floating-point arithmetic; value iteration performs 30 bounded-horizon max/min backups. Attractors use positive support, not approximate equality to one.

This does not make the abstraction exact for concrete play: sub-zone location, exact distances, fixed assignments and defender coordinates are omitted. Representatives use the previously documented biased proposal distribution. Thirty samples are retained, but no claim of statistical transition convergence is made. Concrete one-step refinement evaluates the joint action's immediate risk and then abstract continuation; sampled Q alternatives and clipped regret remain diagnostics against the sampled joint-action optimum, not exhaustive concrete regret. Almost-sure nonterminal bounded winning regions remain empty; positive regions contain all 30,375 states per side.

## Validation and artifacts

26 unit tests pass. Added joint-action counts and typical two-receiver movement, 100-representative vector key/catch/transition checks, max/min sparse Bellman fixture, and batched-policy equivalence with scalar action enumeration. All 120 recorded histories were additionally reproduced exactly with the final vectorized concrete evaluator; matrices were checked for row mass one.

Initial complete pipeline: 217.53 seconds, including sampling/build, solve, 120 games, figures and two videos. Final batched evaluator replayed the same 120 games in 7.36 seconds with the saved model, without rebuilding. The final output-path fix explicitly passes the requested directory to Solver; it does not change any game decisions. Local solver cache is approximately 1.2 GB and ignored by git.

Opened and checked actual MP4-extracted `outputs_dev/v5/extracted_frame.png` and `extracted_throw.png`. Both concrete/abstract panels align; turn 25 visibly shows the scoring arc labeled p=0.760, CAUGHT. Videos retain H.264/yuv420p, faststart and metadata stripping.

Outputs: `outputs_dev/v5/{RESULTS.md,games.csv,games.json,summary.json,solver.json,run.json,solver.pkl}`, four PNG/PDF metric figures, `calculator_view.{png,pdf}`, `demo_{Calculator,Scripted}.mp4`, and the two extracted PNGs. Output artifacts remain ignored; code, dependencies and this validation are committed. No LLM calls, pushes, main edits, data edits or writes to protected outputs/Haiku folders.

Reproduce: `uv run python ultimate.py --n 30 --no-llm --samples 30 --out outputs_dev/v5`. Audit cached outputs: `uv run python report_v5.py` (load only trusted pickle caches).
