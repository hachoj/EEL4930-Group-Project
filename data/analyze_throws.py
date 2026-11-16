"""Offline 2025 UFA analysis; run with uv run python data/analyze_throws.py."""
import csv,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
rows=[]; keys=set(); counts={}
for f in sorted((root/'raw/events').glob('*.json')):
 for side in ('homeEvents','awayEvents'):
  for i,e in enumerate(json.loads(f.read_text())['data'][side]):
   keys.update(e);t=e['type'];counts[t]=counts.get(t,0)+1
   if t not in (18,19,20,22):continue
   end='turnover' if t==22 else 'receiver'
   try:x,y,rx,ry=[float(e[k]) for k in ('throwerX','throwerY',end+'X',end+'Y')]
   except (KeyError,TypeError,ValueError):continue
   if not all(math.isfinite(v) for v in (x,y,rx,ry)):continue
   dx,dy=rx-x,ry-y
   rows.append(dict(game=f.stem,side=side,event=i,type=t,thrower_x=x,thrower_y=y,receiver_x=rx,receiver_y=ry,completed=int(t in (18,19)),distance=math.hypot(dx,dy),dx=dx,dy=dy))
with (root/'throws_2025.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raw_n=len(rows); excluded=sum(r['distance']<1 for r in rows)
rows=[r for r in rows if r['distance']>=1]
y=np.array([r['completed'] for r in rows]);d=np.array([r['distance'] for r in rows]);dx=np.array([r['dx'] for r in rows]);dy=np.array([r['dy'] for r in rows]);g=np.array([r['game'] for r in rows])
X=np.column_stack([np.ones(len(d)),d/20]);b=np.zeros(2)
for _ in range(50):
 p=1/(1+np.exp(-np.clip(X@b,-40,40)));step=np.linalg.solve(X.T@((p*(1-p))[:,None]*X),X.T@(y-p));b+=step
 if max(abs(step))<1e-10:break
b[1]/=20
bins=[0,5,10,15,20,30,40,60,120,math.inf];groups=[(f'{a}–{z} yd',(d>=a)&(d<z)) for a,z in zip(bins,bins[1:])]
def ci(k,n):
 p=k/n;z=1.96;c=(p+z*z/(2*n))/(1+z*z/n);h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n);return c-h,c+h
def table(gs):
 lines=['| Group | Attempts | Completed | Rate (95% Wilson CI) |','|---|---:|---:|---|']
 for label,m in gs:
  n=int(m.sum());k=int(y[m].sum())
  if n:
   lo,hi=ci(k,n);lines.append(f'| {label} | {n:,} | {k:,} | {k/n:.2%} ({lo:.2%}–{hi:.2%}) |')
 return '\n'.join(lines)
cross=(abs(dx)>abs(dy))&np.array([r['thrower_x']*r['receiver_x']<0 for r in rows]);same=(abs(dx)>abs(dy))&~cross
strata=[(m,m&cross,m&same) for _,m in groups if (m&cross).sum()>=20 and (m&same).sum()>=20]
def ratio(w):
 den=sum(w[m].sum() for m,a,c in strata)
 pc=sum(w[m].sum()*np.average(y[a],weights=w[a]) for m,a,c in strata)/den
 ps=sum(w[m].sum()*np.average(y[c],weights=w[c]) for m,a,c in strata)/den
 return pc,ps,pc/ps
pc,ps,rr=ratio(np.ones(len(y)));rng=np.random.default_rng(2025);ug=np.unique(g);boot=[]
for _ in range(500):
 sample=rng.choice(ug,len(ug));freq={v:int((sample==v).sum()) for v in ug};boot.append(ratio(np.array([freq[v] for v in g]))[2])
lo,hi=np.quantile(boot,[.025,.975])
fig,ax=plt.subplots(figsize=(8,5))
for label,m in groups:
 if m.sum():
  n=m.sum();p=y[m].mean();a,z=ci(y[m].sum(),n);ax.errorbar(d[m].mean(),p,yerr=[[p-a],[z-p]],fmt='o',color='navy',capsize=3)
z=np.linspace(0,110,300);ax.plot(z,1/(1+np.exp(-(b[0]+b[1]*z))),label='Logistic fit');ax.set(xlabel='Straight-line distance (yards)',ylabel='Completion probability',ylim=(0,1.02),xlim=(0,110));ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(root/'completion_distance.png',dpi=220)
report=f'''# UFA 2025 throws

{len(rows):,} coordinate-complete attempts from {len(ug)} games, {int(y.sum()):,} completions ({y.mean():.2%}). Extracted throw table: `throws_2025.csv`; raw owner-supplied cache: 15 MB, excluded via data/.gitignore.

## Semantics and quality

Quality filter: the extracted CSV retains all {raw_n:,} attempts; all statistics and the fit below exclude {excluded:,} throws with distance <1 yard. Many turnover records repeat the thrower coordinates (748 exact-zero type 22, 91 exact-zero type 20; also 221 zero completions). These plausibly indicate unrecorded endpoints, not real zero-yard throws. The 1-yard threshold is an explicit sensitivity/quality decision, not an API missingness label. Counts and estimates are conditional on recorded distance ≥1 yard; missing endpoints may be outcome-dependent.

The official API documentation https://www.docs.ufastats.com/ returned a JavaScript-only shell. Numeric meanings are therefore **inferred from fields and event sequences**, not confirmed documentation: 18 completed pass; 19 goal pass; 20 drop; 22 throwaway. Types 18/19 count completed; 20/22 incomplete. Drop vs throwaway naming needs independent verification but both count identically in this analysis. Type 11/12 defender-only block/Callahan records have no throw endpoints and are not counted again; offensive turnover counterparts are represented by type 22. Type 23 appears to be a stall (identical endpoints), excluded; 24 lacks destination, excluded. No endpoint imputation. Event counts: {json.dumps(counts,sort_keys=True)}.

Both streams represent their own offensive throws. Coordinates are interpreted as yards, x across field, y increasing toward attack (goal locations provide a check). Incomplete type 22 uses turnoverX/Y, which is a turnover endpoint, not necessarily the intended receiver location. This introduces distance measurement error. Distance is Euclidean, not flight path. Rates already include real defense: applying additional defender penalties may double-count pressure.

## Distance completion

{table(groups)}

Bernoulli maximum-likelihood fit using all attempts, d in yards:

`p_UFA(d) = 1 / (1 + exp(-({b[0]:.8f} + ({b[1]:.8f}) * d)))`

Descriptive one-variable fit; no causal or out-of-range guarantees. Wilson intervals assume independent throws and may be optimistic due to clustering. Grid squares-to-yards is a separate simulator design choice.

![Completion curve; dots have 95% Wilson intervals](completion_distance.png)

## Direction

Forward dy>2 yards, lateral |dy|≤2, backward dy<−2; threshold is an explicit analysis choice.

{table([('Forward',dy>2),('Lateral',abs(dy)<=2),('Backward / dump',dy< -2)])}

## Break-side geometry proxy

No force, break, marker orientation, release type or defender-position field occurs in the cached schema. Keys: {', '.join(sorted(keys))}. True break/open throws cannot be identified.

A weak, explicitly geometric proxy compares lateral-dominant throws (|dx|>|dy|) crossing field center (thrower_x × receiver_x < 0), against lateral-dominant throws staying on the same side. Cross-center can be open and same-side can break; these are **not labeled break/open statistics**.

{table([('Cross-center proxy',cross),('Same-side comparison',same)])}

Direct standardization to pooled distance-bin weights, restricted to bins with ≥20 in both groups: cross-center {pc:.2%}, same-side {ps:.2%}, ratio **{rr:.4f}**; game-cluster bootstrap 95% interval **[{lo:.4f}, {hi:.4f}]**, 500 resamples, seed 2025. Controls binned distance only; selection, players, wind and defense remain confounded.

**Recommended evidence-based break multiplier: 1.00.** No nontrivial force-side penalty is identifiable from these fields. If required for game design, choose a clearly assumed sensitivity parameter such as 0.9 or 0.8 and report sensitivity; do not call it a UFA estimate. The proxy ratio is a diagnostic, not a calibrated force penalty.

## Reproduce

Owner fetched the unauthenticated endpoints below. Note `date=2025`, not `years=2025`.

```sh
mkdir -p data/raw/events
curl --fail 'https://www.backend.ufastats.com/api/v1/games?date=2025' -o data/raw/games_2025.json
# Repeat for each gameID (157 cached games):
curl --fail "https://www.backend.ufastats.com/api/v1/gameEvents?gameID=$gameID" -o "data/raw/events/$gameID.json"
uv run python data/analyze_throws.py
```

Analysis uses existing numpy/matplotlib dependencies; no network calls. Event semantics remain inferred until documentation can be independently read.
'''
(root/'THROWS.md').write_text(report)
print(report[:230]);print('fit',b,'proxy',pc,ps,rr,lo,hi)
