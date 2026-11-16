# Fixed-field broadcast validation

Renderer: `render_full.py`; no rule or solver changes. Source history is the
unchanged `outputs_dev/v7/Calculator_vs_Scripted_games.json`, index 0 (10–7).

## Coordinate and identity contract

The initial receiving team attacks right. Engine coordinates are transformed
by `(x,y) -> (9-x,19-y)` whenever the current possession attacks left. Toggle
that transform on turnovers, so the same six people stay in the same stadium
positions while the attack arrow reverses. After a score, retain the current
transform: the other team receives and attacks the previous scorer's direction,
which switches the two teams' attacking ends. Both endzones are always visible.

Track stable team/jersey identities through the engine's post-catch holder swap
and nearest-defender turnover pickup. Pickup at a dropped disc and displacement
of a player occupying that cell are documented engine exceptions. Force-seal
movement after catches is also inherited. The turnover continuity test checks
every transfer in game 0: every other player moves at most one grid square
(Chebyshev distance, because diagonal moves are legal). Presentation-only pulls
line up both teams, arc the disc from scorer to receiver, then cut to the saved
start formation. Engine positions are never edited.

## Actual output

Command:

```sh
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json --game-index 0 --highlights 12 --out outputs_dev/v7/media/broadcast
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json --game-index 0 --out outputs_dev/v7/media/broadcast
```

- Highlights: `Calculator_vs_Scripted_game0_highlights.mp4`, **81.80 s**, 2,454 frames.
- Full: `Calculator_vs_Scripted_game0.mp4`, **359.70 s**, 10,791 frames, all 703 side turns.
- Both: H.264 High, yuv420p, **1920×1080 / 30 fps**. Complete FFmpeg decoding
  passed. Encoder enables faststart and strips source metadata.
- Actual decoded highlights frames opened and visually checked:
  `_title.png` (0.0 s), `_pull.png` (2.4 s), `_turnover.png` (3.8 s),
  `_goal_replay.png` (10.7 s), `_final.png` (79.8 s), with the highlights stem.
  Cards, readable score bug, both endzones, reversal arrow, goal replay banner,
  disc trail and final 10–7 score checked. Camera/jersey continuity is verified
  by the automated test rather than inferred from a single still image.
- Corresponding timing JSON and full-mode decoded frames accompany the videos.

Highlights retain every goal/turnover finish and all pulls; routine stretches
are omitted. Up to min(N,4) approach turns are kept, with frame time allocated
to fit the ordinary game-to-10 budget. Full mode retains every turn. Goals and
interceptions replay more slowly than normal action. Intro explains markings;
no persistent debug annotation is shown. Baseline tactic names are reconstructed
as before; LLM intentions cannot be recovered from old histories and are not
invented. The same coordinate pipeline supports LLM histories (fixture tested).
No LLM calls executed and no run output outside `media/` modified.

`python -m unittest discover -v`: **50 tests; 48 passed, 2 optional legacy
artifact checks skipped**. Includes turnover continuity, scoring-end changes,
highlight event/pull coverage and duration, and unknown-LLM-mode support.

## Paced broadcast (current)

```sh
uv run python render_full.py outputs_dev/v7/Calculator_vs_Scripted_games.json --game-index 0 --highlights 4 --max-seconds 150 --out outputs_dev/v7/media/paced
```

New output: `outputs_dev/v7/media/paced/Calculator_vs_Scripted_game0_highlights.mp4`,
**149.5 seconds / 4,485 frames**. H.264 High/yuv420p, 1920×1080, 30 fps;
AAC LC mono, 44.1 kHz. FFmpeg decoded both streams completely without errors.
Normal moves take 0.7 seconds; throws take 1 second of flight. Every shown
turnover and goal has a separate frozen 1.5-second banner. Goals then replay
the final half of the motion at half speed. Pulls take 1 second, followed by
1 second on the saved formation. Full mode keeps all turns and all event holds.

Highlights retain all 17 goals, all 18 interceptions, all 17 pulls, and 45
play turns in this fixture. Drop-only possessions are omitted. The budget
removes approach turns first, then interceptions if necessary; it never speeds
up retained plays. Goals and pulls are mandatory: an impossibly small budget
raises a clear error. Increase `--max-seconds` to retain more approaches.
The budget applies only to highlights (default 150 seconds).

Audio is deterministic NumPy synthesis: a 3 kHz vibrato/trill whistle at play
start, softer turnover whistle, filtered noise crowd swell on goals, and quiet
filtered noise whooshes on long throws. Peak limiting caps mixed amplitude at
0.65; no downloaded assets. `--no-audio` omits the audio stream.

Actual decoded `_interception_hold_start.png` and `_interception_hold_end.png`
(at 5.0 and 6.0 seconds) were opened and checked: identical player/disc positions,
fixed field and the same turnover banner and new direction arrow.

Legacy LLM histories omit the model. Supply the actual run model explicitly:

```sh
uv run python render_full.py outputs_dev/v7/LLM_vs_Calculator_games.json --model haiku --highlights 4 --max-seconds 150 --out outputs_dev/v7/media/haiku_paced
```

This displays **Haiku** throughout (including filenames), retaining LLM action
reconstruction semantics. New histories with a `model` field use that metadata.
An unlabeled legacy LLM file requires `--model`, avoiding a guessed model name.
No engine, solver or saved history changes; no LLM calls.

Tests: **51 run, 49 passed, 2 optional legacy artifact checks skipped**.
