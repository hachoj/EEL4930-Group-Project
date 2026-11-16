# UFA 2025 point calibration

Run `python3 data/analyze_points.py` offline. Source: owner-supplied 157-game UFA cache, `data/raw/events/*.json`; no network or simulator outputs used.

## Reconstruction and inferred meanings

All numeric meanings are inferred from fields and sequences, not independently verified official documentation. Type 1 starts a pulling/defensive point; 2 starts a receiving/offensive point. Types 7–10 are pull variants (only 7 has landing coordinates). 18 is a completion, 19 a goal completion; 20 a drop, 22 a throwaway (including opposing blocks), 23 a stall-like turnover, 24 another offensive turnover of unknown subtype. Defensive counterparts: 11 block/interception, 12 Callahan (turnover plus immediate defensive goal), 13 other opponent turnover, 14 rare opponent turnover of unknown subtype. Type 15 is opponent goal. 16/17 appear to be stoppage/yardage adjustment events; 3/5/25 lineup changes; none creates possession boundaries here. 28–33 terminate periods; point matching uses period ordinal and recorded start clock, never wall timestamps. Ignored events cannot add boundaries. No block is counted twice: point turnover totals use offensive 20/22/23/24 from both streams; 11–14 validate them.

Only points with matching starts, opposite initial roles, reciprocal turnover counts, exactly one 19/12 goal, correct possession parity and alternating offensive/gain sequences are retained. This is a conservative complete-point subset, not all league points; excluded points may differ systematically. Quarter-ending possessions are excluded, not treated as failures. Own offensive terminal events define possessions; Callahans count as zero-pass scoring possessions. A hold means the receiving team scores on its FIRST possession without any turnover, not eventual receiving-team point victory.

Coordinates are interpreted in yards in each team’s attack frame: own goal line y=20, attacking goal line y=100, end boundaries 0/120. Goal receiver coordinates above 100 support this convention. Depth from own goal line is y−20 (negative means own endzone). Pulls are recorded in the pulling team’s frame, so receiving depth is 100−pullY. Turnover locations are reported in the ORIGINAL point-receiver’s frame (not always the team gaining possession). First thrower y−20 is a pickup/start proxy; it can reflect a walk to the line, brick, penalty or missing event, rather than the raw landing spot. Post-turnover scoring bins use the gaining team’s first throw location, avoiding assumptions about pickup/brick relocations. Net distance gained is goal receiverY minus first throwerY, includes endzone yards and any unrecorded penalties; it is not summed pass distance.

95% intervals for proportions are Wilson intervals (independence approximation; within-game correlation can make them optimistic). Means use 1,000 game-cluster bootstrap resamples, seed 2025. Distribution rows give bin shares with Wilson intervals; percentile summaries are descriptive.

## Coverage

| Audit | Points |
|---|---:|
| candidate | 8,486 |
| accepted | 4,368 |
| unmatched | 3,699 |
| no unique goal (includes quarter endings) | 320 |
| turnover disagreement | 95 |
| role disagreement | 4 |

Accepted sample spans 157 games. Duplicate start-clock keys within a period are removed before matching; candidate count is the union of remaining stream keys. Missing or ambiguous point starts are not imputed.

## Point outcomes

| Metric | Count / denominator | Estimate (95% CI) |
|---|---|---|
| First-possession hold | 2,335 / 4,368 | 53.46% (51.98%–54.93%) |
| Turnovers per point | 3,588 / 4,368 | 0.82 (0.77–0.87) |
| Possessions per point | 7,956 / 4,368 | 1.82 (1.77–1.87) |

## Turnovers per point distribution

| Turnovers | Points | Share (95% CI) |
|---|---|---|
| 0 | 2335 | 53.46% (51.98%–54.93%) |
| 1 | 1120 | 25.64% (24.37%–26.96%) |
| 2 | 551 | 12.61% (11.66%–13.63%) |
| 3 | 198 | 4.53% (3.95%–5.19%) |
| 4 | 96 | 2.20% (1.80%–2.68%) |
| 5 | 39 | 0.89% (0.65%–1.22%) |
| 6 | 18 | 0.41% (0.26%–0.65%) |
| 7 | 6 | 0.14% (0.06%–0.30%) |
| 8 | 2 | 0.05% (0.01%–0.17%) |
| 9 | 3 | 0.07% (0.02%–0.20%) |

Possessions-per-point distribution is exactly the turnover distribution above shifted by +1 (1 through 10 possessions).

Offensive turnover labels in accepted points: drop: 527, throwaway / blocked throw: 2,991, stall-like: 20, unknown turnover: 50. Defensive counterparts: block/interception: 1,828, Callahan: 20, other opponent turnover: 1,690, unknown opponent turnover: 50. These counterpart counts overlap offensive labels and must not be added to them. The cache does not separate a caught interception from a knocked-down block.

All finite turnover endpoints are retained, including repeated thrower coordinates: unlike distance-fit analysis, zero displacement is not evidence sufficient to discard a possession boundary. 50 turnovers lack usable endpoints; no endpoint is imputed.

## Scoring possessions

| Start | Count | Completed passes incl. goal (95% CI) | Net yards gained: count; mean (95% CI) |
|---|---|---|---|
| All | 4368 | 8.30 (8.02–8.57) | 4,348; 71.75 (70.44–73.00) |
| Pull | 2335 | 9.75 (9.47–10.04) | 2,335; 85.25 (84.37–86.14) |
| Turnover | 2033 | 6.63 (6.34–6.94) | 2,013; 56.10 (54.52–57.52) |

Goals within 1–3 completed throws of the latest turnover: **645/4,368 = 14.77% (13.75%–15.85%)** of ALL goals. Among turnover-origin goals: 31.73% (29.74%–33.78%). Zero-pass Callahans are outside 1–3. Failed possessions between the initial pull and final turnover do not contribute passes to this measure.

## Pull landing depth

N=4,015; mean (95% CI) **0.21 (-0.57–1.06) yd**; p10 / median / p90: -14.78 / -4.81 / 23.31 yd.

## Pull landing depth bins

| Depth yards | Count | Share (95% CI) |
|---|---|---|
| [-inf, 0) | 2497 | 62.19% (60.68%–63.68%) |
| [0, 10) | 586 | 14.60% (13.54%–15.72%) |
| [10, 20) | 220 | 5.48% (4.82%–6.23%) |
| [20, 40) | 690 | 17.19% (16.05%–18.38%) |
| [40, 60) | 20 | 0.50% (0.32%–0.77%) |
| [60, 80) | 2 | 0.05% (0.01%–0.18%) |
| [80, inf) | 0 | 0.00% (0.00%–0.10%) |

## Pull pickup / first-throw depth

N=4,368; mean (95% CI) **1.72 (0.99–2.46) yd**; p10 / median / p90: -15.17 / -3.68 / 26.17 yd.

## Pull pickup / first-throw depth bins

| Depth yards | Count | Share (95% CI) |
|---|---|---|
| [-inf, 0) | 2555 | 58.49% (57.03%–59.95%) |
| [0, 10) | 643 | 14.72% (13.70%–15.80%) |
| [10, 20) | 254 | 5.82% (5.16%–6.55%) |
| [20, 40) | 829 | 18.98% (17.84%–20.17%) |
| [40, 60) | 73 | 1.67% (1.33%–2.10%) |
| [60, 80) | 4 | 0.09% (0.04%–0.24%) |
| [80, inf) | 10 | 0.23% (0.12%–0.42%) |

## Turnover depth from original receiving goal line

N=3,538; mean (95% CI) **43.82 (42.77–44.84) yd**; p10 / median / p90: -1.11 / 43.85 / 87.31 yd.

## Turnover depth from original receiving goal line bins

| Depth yards | Count | Share (95% CI) |
|---|---|---|
| [-inf, 0) | 371 | 10.49% (9.52%–11.54%) |
| [0, 10) | 265 | 7.49% (6.67%–8.40%) |
| [10, 20) | 359 | 10.15% (9.19%–11.19%) |
| [20, 40) | 656 | 18.54% (17.30%–19.86%) |
| [40, 60) | 606 | 17.13% (15.92%–18.41%) |
| [60, 80) | 582 | 16.45% (15.26%–17.71%) |
| [80, inf) | 699 | 19.76% (18.48%–21.10%) |

## Score rate after turnover by gaining team start position

| Own-goal-line depth yd | Possessions | Goals | Score rate (95% CI) |
|---|---|---|---|
| [-inf, 0) | 459 | 201 | 43.79% (39.32%–48.36%) |
| [0, 10) | 952 | 441 | 46.32% (43.18%–49.50%) |
| [10, 20) | 391 | 198 | 50.64% (45.70%–55.56%) |
| [20, 40) | 665 | 378 | 56.84% (53.05%–60.56%) |
| [40, 60) | 587 | 387 | 65.93% (62.00%–69.65%) |
| [60, 80) | 479 | 379 | 79.12% (75.26%–82.52%) |
| [80, inf) | 35 | 29 | 82.86% (67.32%–91.90%) |

Post-turnover possessions: 3,588, including 20 without a first-throw location (including Callahans); location bins omit these. All post-turnover score rate: 56.66% (55.03%–58.27%).

## Calibration targets

Use these as descriptive targets with the selection caveat above: first-possession hold **53.46%**; turnovers/point **0.82**; completed passes/scoring possession **8.30** (includes goal); pull pickup proxy mean **1.72 yd** from own goal line; goals within 1–3 throws after a turnover **14.77%**. Use the field-position table to assess short-field gifts. These are 7v7 professional observations; they do not establish that a 3v3 simulator must match them exactly. Do not calibrate landing and pickup as though they were the same variable.

Raw event-type counts: `{"1": 6687, "2": 6685, "3": 800, "5": 760, "7": 6183, "8": 455, "9": 36, "10": 7, "11": 3117, "12": 26, "13": 2807, "14": 67, "15": 6129, "16": 1675, "17": 2052, "18": 73246, "19": 6128, "20": 862, "22": 5043, "23": 25, "24": 67, "25": 640, "28": 314, "29": 314, "30": 314, "31": 304, "32": 26, "33": 11}`.
