"""Cached non-LLM pressure sweep against observed UFA point targets."""
import argparse,json
from pathlib import Path
import numpy as np
import full_game as f
TARGETS=dict(completion_percent=94.09,hold_rate=.535,turnovers_per_point=.82,completed_passes_per_scoring_possession=8.3,pull_completed_passes_per_scoring_possession=9.75,goals_within_1_3_throws_of_turnover=.148,pull_pickup_depth_yards=1.7)

def metrics(games):
    points=[]
    for g in games:
        point=[]
        for p in g['possessions']:
            point.append(p)
            if p['outcome']=='score':points.append(point);point=[]
    scoring=[p[-1] for p in points]
    return dict(pull_completed_passes_per_scoring_possession=float(np.mean([p[-1]['completed'] for p in points if len(p)==1])) if any(len(p)==1 for p in points) else 0,pull_pickup_depth_yards=float(np.mean([(p['landing'][1]-2.5)*5 for g in games for p in g['pulls']])),games=len(games),points=len(points),completion_percent=100*sum(g['completed'] for g in games)/max(1,sum(g['throws'] for g in games)),turnovers_per_point=sum(len(p)-1 for p in points)/max(1,len(points)),hold_rate=sum(len(p)==1 for p in points)/max(1,len(points)),completed_passes_per_scoring_possession=float(np.mean([p['completed'] for p in scoring])) if scoring else 0,goals_within_1_3_throws_of_turnover=sum(len(p)>1 and 1<=p[-1]['throws']<=3 for p in points)/max(1,len(points)),safety_cap_triggers=sum(g['safety_cap_triggered'] for g in games))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pressures',type=float,nargs='+',default=[.1,.2,.35,.5]);p.add_argument('--n',type=int,default=20);p.add_argument('--target',type=int,default=10);p.add_argument('--samples',type=int,default=4);p.add_argument('--seed',type=int,default=8100);p.add_argument('--out',type=Path,default=Path('outputs_dev/v9/calibration'));a=p.parse_args()
    if min(a.n,a.target,a.samples)<1 or not a.pressures or any(not 0<=v<=1 for v in a.pressures):p.error('positive counts and pressure values in [0,1] required')
    a.out.mkdir(parents=True,exist_ok=True);rows=[]
    for pressure in a.pressures:
        cache=a.out/f'pressure_{pressure:g}';cache.mkdir(exist_ok=True)
        path=cache/'solver.pkl'
        if path.exists():
            solver=f.load_solver(path)
            if solver.pressure!=pressure or solver.info['samples_per_state']!=a.samples or solver.pull_config!=(2,3,3,3):raise ValueError('cache configuration mismatch')
        else:solver=f.Solver(samples=a.samples,pressure=pressure,out=cache)
        solver.matrices=None  # Concrete decisions use V only; release sparse build storage.
        for coach in ('Calculator','Scripted'):
            games=[f.game(coach,coach,a.seed+i,solver if coach=='Calculator' else None,target=a.target,first=i%2,pressure=pressure) for i in range(a.n)]
            (cache/f'{coach}_vs_{coach}_games.json').write_text(json.dumps(games))
            rows.append(dict(pressure=pressure,coach=coach,**metrics(games)))
        del solver
        (a.out/'calibration.json').write_text(json.dumps(dict(config={**vars(a),'out':str(a.out)},rows=rows),indent=2))
    write_reports(rows,a.out)

def write_reports(rows,out):
    primary=[r for r in rows if r['coach']=='Calculator' and not r['safety_cap_triggers']]
    def loss(r):return sum(((r[k]-TARGETS[k])/TARGETS[k])**2 for k in ('hold_rate','turnovers_per_point','completion_percent','completed_passes_per_scoring_possession','goals_within_1_3_throws_of_turnover'))
    chosen=min(primary,key=loss) if primary else None
    selection=dict(pressure=chosen['pressure'] if chosen else None,criterion='Equal squared relative errors on five self-play metrics: hold, turnovers/point, completion, passes/goal, and short-turnover goals. Scripted is secondary validation.',targets=TARGETS,observed=chosen)
    (out/'selection.json').write_text(json.dumps(selection,indent=2))
    columns=list(rows[0]);table=' | '.join(columns)+'\n'+' | '.join(['---']*len(columns))+'\n'
    table+='\n'.join(' | '.join(f'{r[k]:.4f}' if isinstance(r[k],float) else str(r[k]) for k in columns) for r in rows)+'\n'
    table+='\nTargets (each sweep metric compared below):\n\nMetric | Target | Selected self-play | Difference\n--- | ---: | ---: | ---:\n'
    if chosen:
        for key,target in TARGETS.items():table+=f'{key} | {target:.4f} | {chosen[key]:.4f} | {chosen[key]-target:+.4f}\n'
    table+='\nAll grid comparisons:\n\nPressure | Coach | Metric | Observed | Target | Difference\n--- | --- | --- | ---: | ---: | ---:\n'
    for r in rows:
        for key,target in TARGETS.items():table+=f'{r["pressure"]} | {r["coach"]} | {key} | {r[key]:.4f} | {target:.4f} | {r[key]-target:+.4f}\n'
    table+=f'\nSelected pressure: {selection["pressure"]}. {selection["criterion"]}\n'
    table+='\nCalculator build/solve timings (seconds):\n\nPressure | Samples/state | Build | Solve | Residual\n--- | ---: | ---: | ---: | ---:\n'
    for pressure in sorted({r['pressure'] for r in rows}):
        info=json.loads((out/f'pressure_{pressure:g}'/'solver.json').read_text())
        table+=f"{pressure:g} | {info['samples_per_state']} | {info['build_seconds']:.2f} | {info['solve_seconds']:.2f} | {info['residual']:.3g}\n"
    (out/'calibration.md').write_text(table);print(table)
if __name__=='__main__':main()
