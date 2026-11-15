# Symmetry and movement validation

Offense | Defense | Win | 95% CI
---|---|---|---
Calculator | Calculator | 43.3% | 27.4%–60.8%
Calculator | Scripted | 43.3% | 27.4%–60.8%
Scripted | Calculator | 50.0% | 33.2%–66.8%
Scripted | Scripted | 56.7% | 39.2%–72.6%

Coach | Side | Before players/turn | After players/turn | Before turns | After turns
---|---|---|---|---|---
Calculator | offense | 0.630 | 0.618 | 810 | 900
Calculator | defense | 0.343 | 0.830 | 616 | 481
Scripted | offense | 0.091 | 2.000 | 594 | 182
Scripted | defense | 0.473 | 1.027 | 706 | 481

22 tests pass. 60,752 states; 30 samples/state/action; build 121.02 s, solve 3.10 s; full pipeline 143.48 s.

Movement counts compare each post-move record against its pre-move state, remapping labels after catches. Original Scripted offense moved 54 players across 594 turns (0.091), not zero. It stalled behind markers with straight cuts. Independent open-space cuts now move both receivers on every recorded offense turn. Defense can stay when positioned; Calculator can intentionally hold. All coaches already supported simultaneous joint updates; no sequential video movement bug was found (entire arrays interpolate at the same fraction). Calculator retains restricted joint macros, not exhaustive independent directions.

Symmetric lanes are 0–2 / 3–6 / 7–9. Depth bands unchanged. Only endzone 17–19 is shaded. Red abstract icons encode nearest receiver coverage front/behind; absent means far. Holder defender coverage is omitted by the abstraction. Opened calculator_view.png and an actual MP4-extracted split-screen frame; checked lane boundaries, single endzone, red coverage icons, and legend.

Outputs: outputs_dev/v4/calculator_view.{png,pdf}, demo_{Calculator,Scripted}.mp4, extracted_frame.png, games.{json,csv}, summary.json, solver.json, run.json. Outputs are ignored by git. No Claude calls or changes to protected output/data folders.
