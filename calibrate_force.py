"""Seeded Scripted self-play sensitivity; no solver or LLM calls."""
import json
from pathlib import Path
import numpy as np
import ultimate as u
import force
class Diagnostic:
    V=np.zeros((31,2,len(u.KEYS)+2))
    def qs(self,*args):return np.zeros(1)
def main():
    out=Path('outputs_dev/v6');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for m in (1.,.9,.8,.7,.6,.5,.4):
        force.BREAK_MULTIPLIER=m
        games=[u.game('Scripted','Scripted',1700+i,Diagnostic(),'unused') for i in range(500)]
        throws=[h for g in games for h in g['history'] if h['receiver']]
        breaks=[h for h in throws if h['break_throw']]
        k=sum(h['throw_result']=='caught' for h in breaks)
        row=dict(m=m,games=500,throws=len(throws),breaks=len(breaks),frequency=len(breaks)/len(throws),completion=k/len(breaks) if breaks else None,completion_ci=u.wilson(k,len(breaks)) if breaks else None,mean_break_p=float(np.mean([h['p'] for h in breaks])) if breaks else None)
        rows.append(row);print(row,flush=True)
    (out/'calibration.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':main()
