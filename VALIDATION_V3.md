# Fixed-mark validation

18 tests pass. No Claude calls. Marks are a minimum-total-distance bijection at the start, fixed to player identity for the possession. The holder remains marked; catch canonicalization remaps indices without switching identities. All four Calculator defense macros now follow their own mark (tight front, tight behind, loose front, lateral front). Scripted uses tight front. LLM receives assignments and a man-to-man instruction.

The abstraction still omits defender identities and assignments; sampled representatives receive a nearest bijection. Thus fixed-mark history is not Markov in the compressed model, and concrete one-step refinement remains necessary. No formal concrete guarantee is claimed.

| Offense | Defense | Win | 95% CI | Turnover |
|---|---|---|---|---|
| Calculator | Calculator | 66.7% | 48.8%–80.8% | 33.3% |
| Calculator | Scripted | 43.3% | 27.4%–60.8% | 56.7% |
| Scripted | Calculator | 0.0% | 0.0%–11.4% | 36.7% |
| Scripted | Scripted | 0.0% | 0.0%–11.4% | 36.7% |

Mean defender-to-fixed-mark distance (squares), pooled across all recorded moves and both offensive opponents. Before uses the previous N=30 calibrated recordings, reconstructed identity marks; after uses this run. Changes in game lengths/outcomes also affect this descriptive comparison.

| Defense | Before | After |
|---|---|---|
| Calculator | 1.340 | 1.012 |
| Scripted | 1.265 | 1.074 |

60,752 abstract states; 30 samples/state/action; build 109.31s, solve 3.25s; complete run including two split-screen videos 140.38s.

Replays: landscape pitch, fixed-mark dashed links (--hide-marks disables), jersey labels, interpolated movement, throw probability/result, 2s final hold. H.264 yuv420p, faststart and metadata stripping. calculator_view.png/pdf uses the actual 3×5 abstraction rather than a misleading 3×4: the earlier endzone-alias repair added the fifth depth bin. Coverage is nearest-defender status as used by the solver, not necessarily the assigned mark. Player positions are replaced by zone centers in the abstract panel.

Opened and inspected calculator_view.png plus actual extracted_throw.png (turn 23, p=0.718 caught) and extracted_motion.png. Visible pitch, jerseys, fixed-mark links and synchronized abstract panel checked. Both MP4s decoded successfully; moov precedes mdat. The 140.38s run timing covers the initial render; final figure/layout rerender was separate. Scripted now stalls against fixed marking (0/30 each); no recalibration was applied to mask this.
