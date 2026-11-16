# Full prompts from a saved game state

Source: Calculator_vs_Scripted_games.json, game 0, first history row (post-move, pre-throw). Same concrete state evaluated for either decision side; score 0–0, counter 0. No CLI called.

## Offense

```text
Ultimate Frisbee: you coach OFFENSE.
Maximize your team's point differential; turnovers give the opponent the disc at that spot.
You control team 0. Score (team 0, team 1): [0, 0]; target 10.
Field: x=0..9, y=0..19; each square is 5 yards. Offense attacks +y (N); a catch in rows 17..19 scores.
A holds the disc at [2, 0], 17 rows from the scoring endzone; A cannot move.
B is at [4, 2]; C is at [8, 1]. Letters are current roles; the catcher becomes A.
Hold counter 0 of 0..2: offensive turn 1 since gaining the disc; throw required on turn 3. Hold is legal.
Turns alternate: offense moves both receivers, then holds or throws; defense moves all defenders on its own turn.
Moves are at most one square including diagonals. Blocked moves stay; collisions resolve B then C, or D1 then D2 then D3.
After catches the marker seals the holder's left. Listed probabilities include break multiplier 1.0.
Defenders near the throwing segment add interception risk, beyond receiver pressure. Failure risks below are unconditional and sum with catch to 1.
Drops/incompletions give the opponent the disc at the receiver; interceptions give it at the intercepting defender. Coordinates then rotate 180 degrees.
On an offensive turnover, the current defense becomes offense and attacks -y in these coordinates: a turnover at row y leaves the new offense y-2 rows from its scoring endzone (zero if y<=2).
D1 at [1, 0] marks A; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 0 rows from its scoring endzone.
D2 at [5, 2] marks B; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 0 rows from its scoring endzone.
D3 at [8, 4] marks C; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 2 rows from its scoring endzone.
Receiver options: stay, SW, W, NW, S, N, SE, E, NE, get_open (most separation with slight +y preference). Direction names are intents: each chooses the closest legal neighboring move; use the listed resulting square.
Base table: the OTHER receiver chooses stay. Each row is intent -> resulting square | catch / drop / interception probabilities | turnover consequence.
B stay -> [4, 2] | 0.824095 / 0.037347 / 0.138559 | drop gives them disc 0 rows from their endzone
B SW -> [3, 1] | 0.795575 / 0.024051 / 0.180374 | drop gives them disc 0 rows from their endzone
B W -> [3, 2] | 0.850675 / 0.031083 / 0.118242 | drop gives them disc 0 rows from their endzone
B NW -> [3, 3] | 0.859299 / 0.041395 / 0.099306 | drop gives them disc 1 rows from their endzone
B S -> [4, 1] | 0.886179 / 0.031083 / 0.082738 | drop gives them disc 0 rows from their endzone
B N -> [4, 3] | 0.738177 / 0.047422 / 0.214401 | drop gives them disc 1 rows from their endzone
B SE -> [5, 1] | 0.764425 / 0.041395 / 0.194181 | drop gives them disc 0 rows from their endzone
B E -> [5, 1] | 0.764425 / 0.041395 / 0.194181 | drop gives them disc 0 rows from their endzone
B NE -> [5, 3] | 0.587623 / 0.057559 / 0.354819 | drop gives them disc 1 rows from their endzone
B get_open -> [3, 3] | 0.859299 / 0.041395 / 0.099306 | drop gives them disc 1 rows from their endzone
C stay -> [8, 1] | 0.899982 / 0.099282 / 0.000735 | drop gives them disc 0 rows from their endzone
C SW -> [7, 0] | 0.899413 / 0.072248 / 0.028339 | drop gives them disc 0 rows from their endzone
C W -> [7, 1] | 0.791299 / 0.074407 / 0.134293 | drop gives them disc 0 rows from their endzone
C NW -> [7, 2] | 0.679924 / 0.080983 / 0.239093 | drop gives them disc 0 rows from their endzone
C S -> [8, 0] | 0.903067 / 0.096933 / 0.000000 | drop gives them disc 0 rows from their endzone
C N -> [8, 2] | 0.785349 / 0.106439 / 0.108212 | drop gives them disc 0 rows from their endzone
C SE -> [9, 0] | 0.871121 / 0.128879 / 0.000000 | drop gives them disc 0 rows from their endzone
C E -> [9, 1] | 0.868539 / 0.131461 / 0.000000 | drop gives them disc 0 rows from their endzone
C NE -> [9, 2] | 0.757068 / 0.139311 / 0.103621 | drop gives them disc 0 rows from their endzone
C get_open -> [9, 0] | 0.871121 / 0.128879 / 0.000000 | drop gives them disc 0 rows from their endzone
Joint corrections below override base rows when both receivers choose moves that collide; all unlisted joint choices have exactly the base outcomes (other-receiver movement has no other effect on throw probability).
No joint corrections for this state.
Hold: move receivers with no immediate throw risk, keep disc at A, increment counter; defense acts next. A catch resets the counter. 2 hold(s) remain before a forced throw.
Choose move_B and move_C from the named intents; action is throw_B, throw_C, or hold.
Return only named-field JSON, for example: {"move_B": "N", "move_C": "get_open", "action": "throw_B"}
```

## Defense

```text
Ultimate Frisbee: you coach DEFENSE.
Maximize your team's point differential; turnovers give the opponent the disc at that spot.
You control team 1. Score (team 0, team 1): [0, 0]; target 10.
Field: x=0..9, y=0..19; each square is 5 yards. Offense attacks +y (N); a catch in rows 17..19 scores.
A holds the disc at [2, 0], 17 rows from the scoring endzone; A cannot move.
B is at [4, 2]; C is at [8, 1]. Letters are current roles; the catcher becomes A.
Hold counter 0 of 0..2: offensive turn 1 since gaining the disc; throw required on turn 3. Hold is legal.
Turns alternate: offense moves both receivers, then holds or throws; defense moves all defenders on its own turn.
Moves are at most one square including diagonals. Blocked moves stay; collisions resolve B then C, or D1 then D2 then D3.
After catches the marker seals the holder's left. Listed probabilities include break multiplier 1.0.
Defenders near the throwing segment add interception risk, beyond receiver pressure. Failure risks below are unconditional and sum with catch to 1.
Drops/incompletions give the opponent the disc at the receiver; interceptions give it at the intercepting defender. Coordinates then rotate 180 degrees.
On an offensive turnover, the current defense becomes offense and attacks -y in these coordinates: a turnover at row y leaves the new offense y-2 rows from its scoring endzone (zero if y<=2).
D1 at [1, 0] marks A; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 0 rows from its scoring endzone.
D2 at [5, 2] marks B; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 0 rows from its scoring endzone.
D3 at [8, 4] marks C; last chosen mode: unknown (initial setup or no recorded action). If this defender intercepts here, the current defense gains the disc 2 rows from its scoring endzone.
Per-defender proposed destinations (other defenders assumed to stay; joint collisions may cause a stay):
D1 tight_front -> [2, 1]: move toward thrower side of own mark; give up rear space.
D1 tight_behind -> [2, 1]: move behind own mark; give up front space.
D1 trail -> [0, 0]: follow current side of own mark; give up opposite side.
D1 poach_lane -> [1, 0]: leave own mark for midpoint of mark-to-holder lane; give up tight coverage.
D1 poach_deep -> [2, 1]: leave own mark to guard deep space in front of endzone; give up short coverage.
D1 double_B -> [2, 1]: leave own mark to double B; give up own assignment.
D1 double_C -> [2, 1]: leave own mark to double C; give up own assignment.
D1 switch_D2 -> [2, 1]: swap marks with D2, then tight_front on B; give up current assignment; partner must choose switch_D1.
D1 switch_D3 -> [2, 1]: swap marks with D3, then tight_front on C; give up current assignment; partner must choose switch_D1.
D2 tight_front -> [4, 1]: move toward thrower side of own mark; give up rear space.
D2 tight_behind -> [5, 3]: move behind own mark; give up front space.
D2 trail -> [5, 1]: follow current side of own mark; give up opposite side.
D2 poach_lane -> [4, 1]: leave own mark for midpoint of mark-to-holder lane; give up tight coverage.
D2 poach_deep -> [4, 3]: leave own mark to guard deep space in front of endzone; give up short coverage.
D2 double_B -> [4, 1]: leave own mark to double B; give up own assignment.
D2 double_C -> [6, 1]: leave own mark to double C; give up own assignment.
D2 switch_D1 -> [4, 1]: swap marks with D1, then tight_front on A; give up current assignment; partner must choose switch_D2.
D2 switch_D3 -> [6, 1]: swap marks with D3, then tight_front on C; give up current assignment; partner must choose switch_D2.
D3 tight_front -> [7, 3]: move toward thrower side of own mark; give up rear space.
D3 tight_behind -> [9, 3]: move behind own mark; give up front space.
D3 trail -> [8, 3]: follow current side of own mark; give up opposite side.
D3 poach_lane -> [7, 3]: leave own mark for midpoint of mark-to-holder lane; give up tight coverage.
D3 poach_deep -> [8, 5]: leave own mark to guard deep space in front of endzone; give up short coverage.
D3 double_B -> [7, 3]: leave own mark to double B; give up own assignment.
D3 double_C -> [8, 3]: leave own mark to double C; give up own assignment.
D3 switch_D1 -> [7, 3]: swap marks with D1, then tight_front on A; give up current assignment; partner must choose switch_D3.
D3 switch_D2 -> [7, 3]: swap marks with D2, then tight_front on B; give up current assignment; partner must choose switch_D3.
Switch choices must be reciprocal; one reciprocal pair maximum. Other defenders can choose any listed mode.
Return only named-field JSON, for example: {"D1": "tight_front", "D2": "poach_lane", "D3": "tight_behind"}
```
