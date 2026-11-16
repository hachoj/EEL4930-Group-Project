# Validation and diagnosis

The original e9446f7 Calculator loss (seed 1700, Scripted defense) is reproduced in `outputs_dev/baseline/trace.json`. Actions are hold, advance, spread, advance+throw1, advance+throw2. Each row below lists all five sampled offense Q values, the selected action, and its actual throw probability. These are the old two-sample values, not values recomputed under the new model.

| Turn | Sampled Q alternatives | Selected | Actual p(catch) |
|---|---|---|---|
| 1 | 0.2243, 0.2260, 0.2243, 0.1671, 0.2082 | 1 | 1.0000 |
| 3 | 0.2443, 0.2325, 0.1994, 0.2494, 0.1212 | 3 | 0.5662 |
| 5 | 0.2242, 0.1847, 0.1847, 0.0806, 0.2251 | 4 | 0.6943 |
| 7 | 0.5561, 0.5624, 0.5703, 0.0457, 0.2846 | 2 | 1.0000 |
| 9 | 0.5728, 0.5840, 0.5844, 0.1956, 0.4697 | 2 | 1.0000 |
| 11 | 0.5661, 0.3655, 0.3655, 0.3460, 0.5661 | 0 | 1.0000 |
| 13 | 0.5661, 0.3640, 0.3640, 0.3460, 0.5661 | 0 | 1.0000 |
| 15 | 0.5661, 0.3611, 0.3611, 0.3460, 0.5661 | 0 | 1.0000 |
| 17 | 0.5599, 0.3552, 0.3552, 0.3460, 0.5661 | 4 | 0.8666 |
| 19 | 0.5529, 0.5581, 0.5581, 0.2994, 0.5667 | 4 | 0.9199 |
| 21 | 0.4786, 0.3198, 0.3198, 0.3460, 0.5213 | 4 | 0.7995 |

On turn 3 the model selected throw1 at Q=0.2494; holding had Q=0.2443. In the actual geometry its one-step abstract value was about 0.1274 (recorded regret 0.122), with only 0.5662 catch probability. It then repeatedly exchanged the disc, finally dropping on turn 21. This is representative averaging error, not a Bellman convergence failure. There are only two samples, and neither defender identity nor exact receiver separation is retained. Another failure is repeated stationary holds (turns 11–15), while the top zone aliases y=15/16 with the scoring endzone.

Repairs: 30 samples per state/action, an explicit endzone depth bin, collision-free sampled states and concrete play, and exact concrete one-step macro evaluation followed by abstract continuation values. Equal-value offense actions prefer advancing receivers. This policy refinement is deliberately distinguished from pure abstract strategy lookup. It does not turn the sampled average into a concrete max-min guarantee.

An intermediate near-goal-line N=30 run still scored 0/30 for every matchup (`outputs_dev/refined`). Splitting the endzone alone does not solve the tight horizon or restricted movement macros. Starting receivers at y=2 leaves exactly 15 offensive opportunities to travel 15 squares; any blocked or stationary move can make scoring impossible without a different receiver already farther ahead. Scripted short/backward passing additionally freezes each successive holder. These observations explain the failed scenario, not a theorem that no legal coach can score.

The calibrated experiment retains 30 alternating side turns, the throw formula and macro actions. It moves the offense to an explicitly labeled attacking formation y=12,13,14 and defenders 1–2 squares ahead, and limits Scripted passes to strictly forward targets. This is a new attacking-possession benchmark, not a result for the original own-goal-line scenario. `--start-depth 0` restores an own-goal-line scenario. A separate 100-seed Scripted-only calibration measured 33% scoring at depth 12; the N=30 results below use the fixed shared experimental seeds 1700–1729. Calibration is scenario selection, not independent evaluation evidence.

Original LLM recordings in `outputs/games.json` show repeated sideways/backward passes: seed 1700 versus Calculator made 13 throws with probabilities mostly 0.75–0.93 before dropping. Versus Scripted it attempted probabilities 0.63 and 0.54 before dropping. Repeated risk, not malformed output, explains those examples. The revised prompt explicitly says that hold is legal, receivers can move while holding, incompletions immediately lose, and repeated passes compound risk. It emphasizes endzone reachability and supplies collision-free legal IDs. No new LLM calls were made, so prompt improvement remains unvalidated.

The old identical abstraction gaps are expected arithmetic: all matchups share seeded starts, the initial prediction is against abstract optimal opposition (not conditioned on a named opponent), and all zero-win rows subtract the same zero. A matchup with a different empirical win rate has a different gap. These are descriptive gaps rather than calibrated opponent-specific predictions; changing opponents does not change V(s).

## Final calibrated N=30 results

| Offense | Defense | Wins | Win 95% CI | Turnover | Turnover 95% CI | Mistakes | Gap |
|---|---|---|---|---|---|---|---|
| Calculator | Calculator | 76.7% | 59.1%–88.2% | 23.3% | 11.8%–40.9% | 0.3% | -0.012 |
| Calculator | Scripted | 43.3% | 27.4%–60.8% | 56.7% | 39.2%–72.6% | 3.4% | +0.321 |
| Scripted | Calculator | 23.3% | 11.8%–40.9% | 36.7% | 21.9%–54.5% | 53.6% | +0.521 |
| Scripted | Scripted | 33.3% | 19.2%–51.2% | 66.7% | 48.8%–80.8% | 58.2% | +0.421 |

Build 96.76 s; solve/attractors 3.07 s; total pipeline including rendering 102.74 s. 60,752 states including terminals; 30 samples per state/action; exactly 30 finite-horizon Bellman backups. Positive region at horizon: all 30,375 states per side; almost-sure region: zero nonterminal states.

Pooled equally across the two defense coaches, Calculator scored 36/60 (60.0%, Wilson 47.4%–71.4%), Scripted 17/60 (28.3%, 18.5%–40.8%). This is a descriptive balanced-opposition comparison. Against Scripted defense alone the gain is only 43.3% versus 33.3%, with overlapping CIs; this run does not establish superiority for that single matchup. Calculator defense also transfers poorly: Calculator offense scores more against it than against Scripted defense. There is no claim that the abstract minimizer is optimal in the concrete game.

Outputs: `outputs_dev/calibrated/{games.csv,games.json,summary.json,solver.json,run.json}`, four `{win_rate,turnover_rate,mistake_rate,abstraction_gap}.{png,pdf}` figures, and `demo_{Calculator,Scripted}.mp4`. `extracted_throw.png` was extracted from the Calculator MP4 at 4 seconds and opened: visible curved scoring throw, p(catch)=0.852, caught label, circle/cross team markers, coach legend and score outcome. Final frames repeat for four additional frames at 2 fps (~2 seconds). Original own-goal-line and intermediate outputs remain separate.

Validation: 15 unittest cases pass, including start generation, collision handling, endzone boundary and a mocked named-JSON LLM reply/model ID. No Claude CLI was invoked. The latest named prompt/model metadata changes affect only LLM runs; measured non-LLM game mechanics are unchanged. Exact CLI-reported models will be written to `reported_model_ids` in future run.json files, if the CLI supplies them.
