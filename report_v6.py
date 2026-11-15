"""Summarize the committed force sensitivity and isolated v6 artifacts."""
import json
from pathlib import Path
out=Path('outputs_dev/v6')
cal=json.loads((out/'calibration.json').read_text())
lines=['# UFA curve and force-flick validation','',
'The measured baseline is sigmoid(4.15701518 − 0.06417449 d_yards), from 84,099 filtered attempts in 157 UFA 2025 games. One grid square remains five yards. Real-defense completion rates are multiplied by an additional modeled receiver-pressure layer. Event semantics and endpoint quality caveats are in data/THROWS.md.','',
'## Calibration (Scripted self-play, 500 shared seeds per setting)','',
'Multiplier | Throws | Break attempts | Break frequency | Break completion (95% Wilson CI) | Mean modeled break p',
'---|---:|---:|---:|---|---:']
for r in cal:
    ci=r['completion_ci']
    completion=f"{r['completion']:.1%} [{ci[0]:.1%}, {ci[1]:.1%}]" if ci else 'No attempts'
    lines.append(f"{r['m']:.1f} | {r['throws']} | {r['breaks']} | {r['frequency']:.1%} | {completion} | "+(f"{r['mean_break_p']:.3f}" if ci else '—'))
lines+=['','No grid setting meets both 15% frequency and ≥95% completion. Select **m=1.0**, the closest completion rate among settings with attempts; its frequency remains 28.8%. Smaller multipliers lower success, and the threshold policy drops break attempts entirely at m≤0.7. The existing receiver-pressure factors and throw distances already put selected break probabilities well below 95%; a multiplier ≤1 cannot increase any fixed throw’s success. The grid demonstrates policy selection cannot rescue these targets here. This is a design choice, not a UFA-derived break effect. Intervals describe realized catch randomness under this seeded benchmark, not uncertainty over realistic tactics.','',
'## N=30 per matchup','',
'Offense | Defense | Wins | 95% Wilson CI | Turnovers',
'---|---|---:|---|---:']
rows=json.loads((out/'summary.json').read_text())
for r in rows:
    lines.append(f"{r['offense']} | {r['defense']} | {r['win_rate']:.1%} | {r['win_ci'][0]:.1%}–{r['win_ci'][1]:.1%} | {r['turnover_rate']:.1%}")
lines+=['','## Solver and verification','','```json',json.dumps(json.loads((out/'solver.json').read_text()),indent=2),'```','',
'29 tests pass, including seal collision/boundary handling, break-angle classification and multiplier application, plus scalar/vector transition parity. The successful-catch transition swaps holder identity and fixed marks before sealing the new marker. All 300 offense / 27 defense actions use the same penalty and seal. Representatives describe ordinary states between catches; the seal is applied to successful successors, not arbitrarily to every sampled state. Fixed mark identity and exact seal positions remain absent from the abstract key, a documented modeling limitation.','',
'Opened and visually checked actual MP4 extraction sealed_marker.png at 0.375 s: turn 1 shows D1 ringed immediately adjacent on the negative-x side of A, with readable synchronized concrete/abstract panels. Full pipeline wall time: 213.84 seconds.','',
'LLM prompt explains negative-x force and includes adjusted per-option probabilities. No Claude CLI calls were made. Replay rings show the holder marker and arcs label BREAK/OPEN. MP4 format remains H.264/yuv420p with faststart.','',
'Artifacts: outputs_dev/v6/{games.json,games.csv,summary.json,calibration.json,solver.json,run.json,RESULTS.md,calculator_view.png,demo_Calculator.mp4,demo_Scripted.mp4,sealed_marker.png}. Protected outputs and Haiku directories were untouched.','',
'Reproduce: uv run python calibrate_force.py; uv run python ultimate.py --n 30 --no-llm --samples 30 --break-multiplier 1 --out outputs_dev/v6; uv run python report_v6.py.']
text='\n'.join(lines)+'\n'
Path('VALIDATION_V6.md').write_text(text)
(out/'RESULTS.md').write_text(text)
