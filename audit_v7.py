"""Audit trusted local v7 caches/histories; does not invoke any LLM."""
import json
from pathlib import Path
import numpy as np
import full_game as f
import ultimate as u

def main():
    out=Path('outputs_dev/v7');s=f.load_solver(out/'solver.pkl')
    audit={'solver':s.info,'max_row_mass_error':max(float(abs(np.asarray(m.sum(1)).ravel()-1).max()) for side in s.matrices for m in side),'bellman_residual':float(abs(s.backup(s.V)-s.V).max())}
    allgames=[]
    for pairing in ('Calculator_vs_Scripted','Calculator_vs_Calculator'):
        gs=json.loads((out/f'{pairing}_games.json').read_text());allgames+=gs
        assert len(gs)==20
        for g in gs:
            assert g['finished'] and max(g['score'])==10 and not g['safety_cap_triggered']
            assert g['llm_calls']==0
            for k,h in enumerate(g['history']):
                assert u.unique(h['o'],h['d'])
                assert sorted(h['marks'])==[0,1,2]
                if h['side']==0 and h['hold_counter']==s.max_hold-1:assert h['receiver'] is not None
                if k and g['history'][k-1].get('turnover_spot') is not None:assert h['thrower']==f.mirror(g['history'][k-1]['turnover_spot'])
            assert all(p['outcome'] in ('score','drop','interception') for p in g['possessions'])
            assert sum(p['throws'] for p in g['possessions'])==g['throws']
            assert sum(p['completed'] for p in g['possessions'])==g['completed']
        for saved in gs[:2]:
            reproduced=f.game(*saved['teams'],saved['seed'],s,first=saved['first'])
            assert reproduced==saved
        result=f.summarize(gs)
        result['serial_parallel_histories_reproduced']=2
        result['team0_decisions']=[sum((h['team'] if h['side']==0 else 1-h['team'])==0 for h in g['history']) for g in gs]
        result['haiku_calls_estimate_mean']=float(np.mean(result['team0_decisions']))
        result['haiku_calls_estimate_range']=[min(result['team0_decisions']),max(result['team0_decisions'])]
        result['outcomes']=dict(__import__('collections').Counter(p['outcome'] for g in gs for p in g['possessions']))
        audit[pairing]=result
    audit['pooled_completion_rate']=sum(g['completed'] for g in allgames)/sum(g['throws'] for g in allgames)
    audit['audited_games']=len(allgames)
    (out/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
