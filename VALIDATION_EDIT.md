# Whole-point highlights

Highlights now select whole completed points. No live turn is omitted within
any selected point: line-up/pull, recorded pickup and cover run, every possession
and turnover, and the goal are shown in order. `--highlights N` is retained for
CLI compatibility; N no longer means approach turns. `--points 1 2 3` explicitly
selects point numbers and implies highlights. Automatic selection prefers a
clean hold, a turnover break, and the final point, filling to three when possible.
A 150-second default budget removes whole earlier selections, preserving the
final point. If even one whole point cannot fit, raise an error; explicit lists
also raise rather than silently truncate.

Routine moves and completed passes <=15 yd use approximately 3x speed (seven
frames per move, ten per short throw), with drawn fast-forward triangles and a
3x badge. Each motion uses smoothstep easing with zero endpoint velocity, so
speed transitions settle smoothly. Long throws, pulls and setup, turnovers,
1.5-second event holds, and goal replays retain normal pacing. Fast-forward
segments generate no audio cues; normal whistle, crowd and long-throw sounds
remain. Each point starts with a 1.5-second score card; omitted points are
summarized there by number range and each team's goals. Full mode retains all
turns at normal speed, with the same cards.

## Actual verification

`uv run python -m unittest discover -q`: **60 tests, 58 passed, two optional
legacy artifact checks skipped**. New contracts check whole-point coverage,
budget rejection, original adjacent turn-state identity and <=1-square movement
for all nonadministrative transitions, plus recorded setup motion. Existing
engine force seals after catches, turnover pickup and occupied-cell displacement
remain exceptions after catch/drop/interception transitions; no rules changed.
Dead-ball line-up resets occur only across the explicit point card.

Rendered source: `outputs_dev/v8/demo/Calculator_vs_Scripted_games.json`, game 0.

```sh
uv run python render_full.py outputs_dev/v8/demo/Calculator_vs_Scripted_games.json --highlights 3 --points 1 2 3 --max-seconds 150 --out outputs_dev/v8/media/edit
```

Output `outputs_dev/v8/media/edit/Calculator_vs_Scripted_game0_highlights.mp4`:
**106.1 s**, 3,183 frames, all **181 live turns**, three complete points.
FFmpeg full decode passed; stream inspection reports H.264 High/yuv420p,
1920x1080/30 fps and AAC LC mono 44.1 kHz. Encoder retains faststart and strips
source metadata. Actual decoded PNGs opened and checked alongside the MP4:

- `_fast_forward.png`, 9.3 s: clear gold double triangle and 3x badge.
- `_between_points.png`, 42.5 s: Point 2, Calculator 1–0 Scripted.
- `_midfield.png`, 11.1 s: first-point live pass in midfield, disc arc and trail.

Timing JSON and all extracted frames share the MP4 stem in that directory.
No histories, game rules, solver or existing outputs outside media/edit changed.
No LLM calls or pushes.
