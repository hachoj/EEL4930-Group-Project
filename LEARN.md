# Sequential in-context learning experiment

Run (the human launches real Claude calls):

```sh
uv run python full_game.py --team0 LLM --team1 Calculator --learn --n 6 --target 5 --model opus --pressure .1 --cover-speed 3 --samples 4 --out outputs_dev/v10/opus_learn
```

`--target` was already available and now also controls the learning runner.
`--learn` requires exactly one LLM team; `--jobs` is explicitly ignored. Games
execute sequentially in one process with seeds `seed+i` (default 1700+i) and
first receiver `i%2`, identical to the normal runner. The same Calculator cache
and policy are used throughout. A new directory builds its own configured solver.
Game mechanics, readable decision prompts and rendering are unchanged.

## Session and feedback protocol

Local `claude --help` verified `-p`, `--model`, `--session-id <uuid>`,
`--resume [value]` and `--output-format json` before implementation. No inference
calls were made during development. The first call is:

```text
claude -p --model opus --session-id <uuid> --output-format json <prompt>
```

Later calls use `--resume <uuid>` in place of `--session-id`. The default UUID4
is recorded in run metadata and each game's learning metadata. `--session-id`
optionally supplies the initial UUID (it creates that session; it does not import
an existing run). Returned `session_id` always becomes the next resume ID.
The requested model alias is recorded; exact model IDs are recorded from returned
`modelUsage`/`model` fields when supplied by the CLI. An absent exact ID is not
guessed. Prompt-cache reads and writes are completely bypassed in learning mode.

Each newly created session starts with: “You will coach many consecutive games
against the same opponent; learn from results.” Every decision otherwise uses
the existing readable offense/defense prompt and named-field action parser.
After every goal, including the winning point, one non-decision call reports the
scorer, score, and this point's LLM offensive turnovers with types and rows.
Rows use the offense's coordinates at the time of that turnover. It asks for OK.
After every game (also a safety-capped one), another call reports both teams'
score, points per possession, turnovers by type, attempted-throw mean row gain,
and backward-throw share, requesting up to five bullet lessons. Lessons are
printed and saved per game; accumulated lessons are also saved in histories.

## Recovery and accounting

A failed CLI call, timeout, error envelope, invalid JSON/action or malformed
lesson response is retried once in the current session. After the second failure,
a fresh UUID session is seeded with accumulated lessons and the pending message
is attempted once there. If that recovery attempt also fails, decision calls
execute the existing Scripted fallback; failed feedback/lessons are recorded as
missing, and the next message starts fresh. No feedback retry can block forever.
On a first-call timeout the CLI may already have persisted the requested UUID;
the retry can therefore fail with a duplicate ID, triggering the same recovery.

Each game's `learning` field contains session IDs, per-attempt events/errors,
requested/returned model IDs, call totals by kind, failures, session resets and
Scripted decision fallbacks. `llm_calls` includes feedback, lessons and retries
in this mode. `llm_decisions` still counts live decisions. `wall_seconds` includes
all decision and feedback/lesson calls, excluding solver build and plot time.
The run summary totals calls, failures and both fallback counts. Lesson-seeded
resets break uninterrupted context: graphs mark those games with red dotted lines.
Normal non-learning cache behavior and deterministic game histories are preserved.

## Metrics and figures

After each completed game, checkpoints update the regular `*_games.json`,
`learning_metrics.json`, `learning_metrics.csv`, and `learning_curve.png/.pdf`.
The metrics include game index, seed, first receiver, score, model, session IDs,
call/failure/fallback counts, wall time, LLM and opponent points per possession,
Calculator points per possession (null for other opponents), LLM turnovers per
possession, mean rows gained per attempted throw, and backward-throw share.
Both teams' detailed metrics live in each game's history. An unfinished final
possession at the safety cap enters the denominator; finished=false flags it.
Undefined ratios are null. Row gain uses the intended receiver's row minus the
thrower's row, including failed throws, in the offense-oriented coordinate frame.

The four-panel plot shows points/possession for both teams and the three LLM
behavior metrics. It is descriptive evidence, not a causal learning estimate:
seeds, first receiver and realized trajectories vary across games. Real improvement
must be measured from the human-run Opus experiment; mocked artifacts do not
measure model strength. Existing `render_full.py --figures` remains compatible
with the additive history fields and still produces its pooled baseline plots.

## Validation

`uv run python -m unittest discover -q`: 69 tests, 67 passed and 2 optional
legacy-artifact checks skipped. Added tests verify startup/resume flags, returned
session identity changes, preamble, cache bypass, context/CLI retry and lesson-
seeded reset, Scripted fallback counts, point-local turnover feedback, and a full
mocked three-game CLI runner with feedback/lesson counts and metrics/figure output.

Saved reproducible mock: `outputs_dev/v10/mocked_learn/`. Its Calculator is a
Scripted adapter to avoid a solver build; all Claude responses are mocks. Each
game targets two points. It tests plumbing only; see `mock_validation.json` for
actual scores, turns and call counts. No real LLM experiment was run.
