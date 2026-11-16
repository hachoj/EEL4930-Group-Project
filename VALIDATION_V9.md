# v9: cover arrives during the pull

## Pull mechanics and coverage

Default pulls still land on rows 2/3 with 60/40 weights. The scripted setup
now represents approximately six seconds of hang time. There is one initial
cover round followed by the existing three receiving/setup rounds. Each round
lets cover take up to three legal one-square substeps (`--cover-speed 3`);
receivers take one square per setup round. The nearest receiver runs to the
landing spot during flight and waits for the disc. No live decision, forced
throw counter, or LLM call occurs before the pull lands and setup finishes.

Defenders run toward a position three rows goal-side of their corresponding
lineup receiver, between their mark and the endzone they defend. This extra
initial flight round matters: nine steps alone cannot get a defender from row
17 within four squares of a receiver at row 2. The four-round allowance is up
to 12 steps (60 yd); actual cover typically travels roughly 45–60 yd, a coarse
hang-time approximation on this grid, not a calibrated running-speed model.
The speed option is an integer number of substeps, not a change to live speed.

Every substep is recorded; the renderer runs the disc flight simultaneously
with these exact player frames, over approximately six seconds. Receivers
already at the landing spot do not begin live play early. After landing, one
second of set formation and the existing whistle precede the first decision.
Stable identities remain continuous through setup and the first live turn.

Across identical seeds 0–999 (3,000 defender/mark pairs), Euclidean grid distance
at the first live decision:

| Version | Mean | p90 | Maximum |
|---|---:|---:|---:|
| v8 | 9.917 | 12 | 12 |
| v9 | 3.000 | 3 | 3 |

Saved measurement: `outputs_dev/v9/coverage.json`. The seeded coverage bound
test uses 500 pulls; existing tests also check seed determinism, uniqueness,
each recorded one-square substep and first-live continuity. The final marks are
assigned normally after setup; no seal teleport is introduced during pulls.
Inherited live catch seals, turnover pickup/displacement, and between-point
dead-ball lineup resets remain the previously documented exceptions.

The Calculator keeps 30,375 base keys, 182,250 hold/side states, 300 offense
actions and 1,372 defense actions. New pull starts map into those keys.
Its score continuation samples 128 starts under the new setup. Cache identity
includes the cover speed, and old three-item pull configuration caches are
rejected; builds must be refreshed.

## Calibration

Sources and limitations remain `data/POINTS.md`: conservative reconstructed
2025 UFA points, describing professional 7v7 rather than this 3v3 model.
Seeds 8100–8119, alternating first receiver, 20 games to 10 for EACH pairing
and pressure; 160 games total, **zero safety-cap triggers**. Each Calculator
uses **four concrete representatives per abstract state**. Pressure-specific
trusted local caches, solver residuals/timings and game histories are under
`outputs_dev/v9/calibration/pressure_*/`.

Reproduce sequentially (the measured run used separate pressure processes
after the first build, then combined their rows):

```sh
uv run python calibrate.py --pressures .1 .2 .35 .5 --n 20 --samples 4 --target 10 --out outputs_dev/v9/calibration
```

| Pressure | Coach | Points | Completion % | Hold % | TO/point | Passes/goal | Short-turnover goals % |
|---|---|---:|---:|---:|---:|---:|---:|
| Target | UFA | — | 94.09 | 53.50 | 0.820 | 8.30 | 14.80 |
| .10 | Calculator | 334 | 93.01 | 55.09 | .584 | 5.81 | 34.43 |
| .20 | Calculator | 340 | 90.83 | 49.41 | .718 | 5.17 | 37.06 |
| .35 | Calculator | 336 | 90.77 | 43.75 | .783 | 5.37 | 37.50 |
| .50 | Calculator | 324 | 88.01 | 36.42 | .932 | 4.56 | 50.31 |
| .10 | Scripted | 310 | 89.96 | 18.06 | 1.458 | 7.51 | 14.19 |
| .20 | Scripted | 303 | 88.27 | 15.18 | 1.746 | 6.97 | 19.14 |
| .35 | Scripted | 310 | 87.49 | 14.19 | 1.926 | 6.61 | 23.55 |
| .50 | Scripted | 299 | 85.55 | 9.36 | 2.321 | 6.02 | 32.44 |

Select **P=.10** by minimizing the sum of squared relative errors across the
five requested metrics in Calculator self-play:
`sum_metric ((observed-target)/target)^2`. Equal relative weight is deliberate;
Scripted is a secondary diagnostic, not part of selection. This expands the v8
criterion, which considered only hold and turnovers/point. Using only those two
would instead select .20; neither choice matches all targets. The five-metric
choice improves completion and passes/goal and reduces the large short-turnover
goal excess, while conceding too few turnovers/point. It is a grid recommendation,
not evidence that pressure alone calibrates the model. API pressure default
remains 1.0; pass `--pressure .1` explicitly for this configuration.

At .10, pull-origin scoring possessions average 8.26 completed passes (target
9.75). Pickup mean remains about -0.4 yd versus +1.7 yd observed, reflecting the
unchanged two-cell distribution. All goal possessions average only 5.81 passes;
34.43% of goals still follow a turnover within three throws versus 14.8% UFA.
Those structural discrepancies remain material.

| Pressure | Build seconds | Solve seconds | Iterations | Residual |
|---|---:|---:|---:|---:|
| .10 | 90.09 | 272.01 | 416 | 9.93e-8 |
| .20 | 172.22 | 352.50 | 416 | 9.80e-8 |
| .35 | 190.26 | 331.55 | 415 | 9.98e-8 |
| .50 | 190.46 | 331.18 | 415 | 9.87e-8 |

All builds under four minutes; latter timings include concurrent builds/solves.
Full metric-vs-target comparisons and selection are in `calibration.md`,
`calibration.json` and `selection.json` in that directory.

## Rendering and throw outcomes

Offense roles are always blue A/B/C and defense roles red D1/D2/D3. Roles follow
the current holder/marks, while underlying identities continue to track motion
across catches and possession changes. The title explains these role colors;
the score bug continues to name the teams. Jerseys, mark lines, seal rings and
tactic labels now use the same interpolated identity positions. DOUBLE/POACH
remain visible when combined with a switch (`/ SW`), rather than being hidden
by SWITCH labels.

Interceptions animate to the recorded intercepting defender, rather than
drawing the arc to the intended receiver. A small quarter-cell anticipation
step illustrates the interception; the defender returns to its recorded spot
at completion. Labels and rings follow that rendered motion too. Drops reach
the receiver at 75% of the flight, then visibly bounce/fall and skid beside
them; the receiver does not retain the disc. The 1.5-second event hold preserves
the final outcome pose and banner. The current engine calls non-interception
failures drops; it has no separate throwaway result. The renderer also supports
an overthrown endpoint if a future history distinguishes that result.

Whole-point selection, visible 3x routine turns, normal-speed event holds,
between-point cards, and synthesized audio are preserved. No within-point
history cuts were added.

## Actual verification and media

`uv run python -m unittest discover -q`: **64 tests, 62 passed, 2 optional
legacy artifact checks skipped**, 7.729 seconds. Includes the seeded coverage
bound, every pull-flight substep, anchor identity/end-position contracts,
interception/drop/throwaway endpoint geometry and all existing regressions.
`git diff --check` passed.

Demo: Calculator vs Scripted, P=.10, seed 1705, game to 3, final **3–2**.
Saved history: `outputs_dev/v9/demo/Calculator_vs_Scripted_games.json`.
The seed was chosen for visual failure-mode coverage, not as a performance
sample. Calibration uses only the fixed 8100–8119 seeds above.

```sh
uv run python render_full.py outputs_dev/v9/demo/Calculator_vs_Scripted_games.json --highlights 3 --max-seconds 150 --out outputs_dev/v9/media
```

MP4: `outputs_dev/v9/media/Calculator_vs_Scripted_game0_highlights.mp4`,
**85.667 seconds**, 2,570 frames, 1920x1080, 30 fps, H.264 High/yuv420p + AAC,
faststart, source metadata stripped. Whole points **1, 2 and 5** retain all
**115 live turns**; points 3–4 are summarized on the intervening card. Complete
video/audio decode passed; stream evidence is in `media/ffmpeg_validation.log`.
The timing JSON beside the MP4 records extracted-frame times.

Opened and visually checked these actual decoded frames, sharing the MP4 stem:

- `_pull.png`, 6.233 s: defenders and disc moving simultaneously in flight.
- `_after_pull.png`, 10.067 s: red D1/D2/D3 close to blue A/B/C.
- `_double.png`, 12.167 s: DOUBLE / SW immediately above the actual D2;
  seal ring also centered on D2, not an empty destination.
- `_midfield.png`, 12.967 s: continuous first-point passing with 3x badge.
- `_interception.png`, 69.867 s: disc ends on red D3, short of intended B,
  with the new-possession banner.
- `_drop.png`, 72.400 s: disc on the ground beside blue B with skid/DROP,
  rather than secured at the receiver.

No push, LLM calls, data edits, or changes to existing v7/v8 outputs.
