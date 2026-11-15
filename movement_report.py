"""Identity-aligned movement audit of saved games (no LLM calls)."""
import json
from collections import defaultdict
from pathlib import Path
import ultimate as u

def counts(path):
    totals=defaultdict(lambda:[0,0])
    for game in json.loads(Path(path).read_text()):
        o,d=u.start_positions(game['seed'])
        for h in game['history']:
            side=h['side'];coach=game['offense'] if side==0 else game['defense']
            old,new=(o,h['o']) if side==0 else (d,h['d'])
            totals[coach,side][0]+=sum(a!=b for a,b in zip(old,new))
            totals[coach,side][1]+=1
            o=[p[:] for p in h['o']];d=[p[:] for p in h['d']]
            if h.get('throw_result')=='caught':
                r=o.index(h['receiver']);o[0],o[r]=o[r],o[0]
    return totals

if __name__=='__main__':
    before=counts('outputs_dev/v3/games.json');after=counts('outputs_dev/v4/games.json')
    text='Coach | Side | Before players/turn | After players/turn | Before turns | After turns\n---|---|---|---|---|---\n'
    for k in sorted(after):
        b,n=before[k];a,m=after[k]
        text+=f'{k[0]} | {"offense" if k[1]==0 else "defense"} | {b/n:.3f} | {a/m:.3f} | {n} | {m}\n'
    print(text)
    Path('outputs_dev/v4/MOVEMENT.md').write_text(text)
