# v7 full-game LLM decision prompt

The LLM now receives readable field, player/mark, score/team, goal distance,
hold-counter and forced-throw information. It sees the most recent actual
selected defensive modes when available (initial setups are explicitly unknown).
The sole strategic instruction is to maximize team point differential; no coach
heuristics or recommended choices are added.

Offense sees all ten receiver intents, including stay and get_open. Tables give
post-move squares and unconditional catch, drop and interception probabilities.
`offense_menu` uses `joint_calculator.proposals`, `resolve_batch` and the same
`throw_model` used by the concrete Calculator evaluation and game. Probabilities
are computed at full precision and displayed to six decimal places. Base rows
assume the other receiver stays; every joint collision that changes a destination
has an explicit correction. Thus all 100 joint receiver choices are covered
without a 200-row duplicated throw table. Drop consequences are stated per row;
interception consequences are stated per defender. Receiver-pressure blocks and
lane interceptions both count as interception, exactly as in the game.

Defense sees each named mode/switch, its proposed square and the coverage it
gives up. Other defenders stay for those proposals; sequential collision
resolution may cause a stay. Reciprocal switches retain the existing parser's
tight-front positioning. JSON field names, examples, cache/retry handling and
scripted fallback remain. New prompt text produces new cache keys; no old cache
or results were modified.

Each new history row has `action_names`: offense `action` plus B/C `intents`, or
defense D1/D2/D3 `modes` plus a zero-based defender `switch` pair (null otherwise).
Calculator records its selected joint action; LLM records its validated named
answer; Scripted records `scripted_cut` receiver intents and actual defensive
modes/switches. A switch token in an LLM modes entry implies tight_front on its
new mark. Fallback logs the Scripted action actually executed. Positions remain
the post-resolution truth. Existing histories are unchanged and cannot acquire
missing historical LLM tactics retroactively. Renderers can consume this additive
field; renderer changes are outside this patch.

## Actual checks

`uv run python -m unittest discover -v`: 55 tests, 53 passed, 2 optional legacy
artifact checks skipped. New tests compare all 100 joint receiver choices against
the mocked parser's realized positions and game throw probabilities, including
collisions; printed numbers agree within 0.0000005. They check all-coach action
logging, defensive modes/forced status, and a mocked CLI game to 10.

Mocked full-game smoke (seed 1700, two LLM teams, deterministic named JSON):
score [0, 10], finished true, safety cap false, 52 turns, 36 throws, 52 mocked
CLI calls. This verifies integration, not Haiku strength. No real LLM calls ran.
No rules, transition probabilities, policies, solver values or output histories
were changed. Calculator logging adds only the chosen action's names.

`PROMPT_V7_EXAMPLES.md` contains both full rendered prompts from game 0's first
saved concrete state in the existing Calculator–Scripted history. The source
history was read only. No improvement in Haiku results is claimed without a
fresh human-run experiment using this prompt.
