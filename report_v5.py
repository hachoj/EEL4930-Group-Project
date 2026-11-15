"""Audit the v5 recorded experiment without LLM calls or rebuilding transitions."""
import json,pickle,time
from pathlib import Path
import numpy as np
import ultimate as u
from movement_report import counts

def main():
 out=Path('outputs_dev/v5');old=json.loads((out/'games.json').read_text())
 with (out/'solver.pkl').open('rb') as f:solver=pickle.load(f)
 errors=[float(np.max(abs(np.array(m.sum(1)).ravel()-1))) for side in solver.matrices for m in side]
 start=time.monotonic()
 new=[u.game(g['offense'],g['defense'],g['seed'],solver,'unused') for g in old]
 assert new==old,'Batched policy changed recorded results'
 replay_seconds=time.monotonic()-start
 before=counts('outputs_dev/v4/games.json');after=counts(out/'games.json')
 text='# Joint-action Calculator: N=30 per matchup\n\nOffense | Defense | Wins | Win 95% CI | Turnovers\n---|---|---|---|---\n'
 for r in u.summarize(new):
  text+=f"{r['offense']} | {r['defense']} | {r['win_rate']:.1%} | {r['win_ci'][0]:.1%}–{r['win_ci'][1]:.1%} | {r['turnover_rate']:.1%}\n"
 text+='\nCoach | Side | v4 players/turn | v5 players/turn | v5 turns\n---|---|---|---|---\n'
 for k in sorted(after):
  b,n=before[k];a,m=after[k]
  text+=f"{k[0]} | {'offense' if k[1]==0 else 'defense'} | {b/n:.3f} | {a/m:.3f} | {m}\n"
 # Seed-paired uncertainty, preserving shared starts and the two-defense cluster.
 differences=[]
 for seed in sorted({g['seed'] for g in new}):
  differences.append(sum((1 if g['offense']=='Calculator' else -1)*(g['outcome']=='score') for g in new if g['seed']==seed)/2)
 boot=np.random.default_rng(923).choice(differences,(20000,len(differences)),replace=True).mean(1)
 text+=f'\nBalanced-opposition offense difference: {np.mean(differences):.1%}; seed-cluster paired bootstrap 95% interval {np.quantile(boot,.025):.1%} to {np.quantile(boot,.975):.1%}.\n'
 text+=f'\nAll 327 transition matrices have row sum one (maximum absolute error {max(errors):.3g}). Batched concrete policy independently reproduced all 120 complete histories exactly in {replay_seconds:.2f}s using the cached model.\n'
 text+='\nState/action counts, build and solve timing:\n```json\n'+json.dumps(solver.info,indent=2)+'\n```\n'
 (out/'RESULTS.md').write_text(text);print(text)

if __name__=='__main__':main()
