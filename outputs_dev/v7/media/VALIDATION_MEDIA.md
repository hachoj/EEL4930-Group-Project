# Full-game media verification

Calculator–Scripted game index 0: highlights N=12, 122 selected side turns,
732 frames, 61.00 seconds. FFmpeg decoded all 732 frames successfully:
H.264 High, yuv420p, 1280x720, 12 fps. Encoder uses faststart and strips
input metadata. Actual MP4 extracts checked: extracted_turnover.png at
2.416667 s (INTERCEPTED, TURNOVER — Calculator ball), extracted_tactics.png
at 4.416667 s (DOUBLE B). Persistent colors checked with red on offense
and blue on defense. Four PNG figures opened and checked for readable
labels, legends and unclipped axes; matching PDF versions generated.

Figures combine 20 Calculator–Scripted and 20 Calculator self-play games.
Defensive modes reconstruct baseline choices; LLM modes remain unknown.
Switches reported separately because they overlap positioning choices.

Existing suite: Ran 46 tests in 0.506s; OK (skipped=2), all 44 executed pass.
No game-rule or solver modifications, no LLM execution.

Full replay: same game, all 703 side turns, 4,218 frames, 351.50 seconds.
PPP: Calculator 473/1069 = 0.44247; Scripted 73/342 = 0.21345.
Switches: Calculator 208, Scripted 186. Positioning counts in figure_stats.json.
