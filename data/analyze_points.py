"""Offline point calibration. python3 data/analyze_points.py; writes POINTS.md only."""
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TURN = {20, 22, 23, 24}
GAIN = {11, 12, 13, 14}

def split(events):
    out = {}; period = 0; key = None; duplicates = set()
    for e in events:
        t = e['type']
        if t in (28, 29, 30, 31, 32, 33):
            period += 1; key = None
        elif t in (1, 2):
            key = (period, e.get('time'))
            if key in out: duplicates.add(key)
            out[key] = [e]
        elif key is not None:
            out[key].append(e)
    return {k:v for k,v in out.items() if k not in duplicates}

def number(e, key):
    try:
        v = float(e[key]); return v if math.isfinite(v) else None
    except (KeyError, ValueError, TypeError): return None

def wilson(k, n):
    if not n: return 'NA'
    p=k/n; z=1.96; c=(p+z*z/(2*n))/(1+z*z/n)
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return f'{p:.2%} ({c-h:.2%}–{c+h:.2%})'

def mean_ci(rows):
    if not rows: return 'NA'
    groups=collections.defaultdict(list)
    for g,v in rows: groups[g].append(v)
    stats=[(sum(v),len(v)) for v in groups.values()]; rng=random.Random(2025); bs=[]
    for _ in range(1000):
        sample=rng.choices(stats,k=len(stats));bs.append(sum(s for s,n in sample)/sum(n for s,n in sample))
    bs.sort(); return f'{sum(v for g,v in rows)/len(rows):.2f} ({bs[24]:.2f}–{bs[974]:.2f})'

points=[]; possessions=[]; pulls=[]; pickups=[]; turnovers=[]; quality=collections.Counter(); types=collections.Counter(); accepted_types=collections.Counter()
for f in sorted((ROOT/'raw/events').glob('*.json')):
    d=json.loads(f.read_text())['data']; streams=[split(d[s]) for s in ('homeEvents','awayEvents')]
    for s in ('homeEvents','awayEvents'): types.update(e['type'] for e in d[s])
    for key in sorted(streams[0].keys() | streams[1].keys()):
        quality['candidate']+=1
        if any(key not in s for s in streams): quality['unmatched']+=1;continue
        pair=[s[key] for s in streams]
        if sorted(es[0]['type'] for es in pair)!=[1,2]:quality['role disagreement']+=1;continue
        ts=[sum(e['type'] in TURN for e in es) for es in pair]
        gains=[sum(e['type'] in GAIN for e in es) for es in pair]
        goals=[sum(e['type'] in (19,12) for e in es) for es in pair]
        if ts!=gains[::-1]:quality['turnover disagreement']+=1;continue
        if sum(goals)!=1:quality['no unique goal (includes quarter endings)']+=1;continue
        receiver=next(i for i,es in enumerate(pair) if es[0]['type']==2)
        scorer=goals.index(1); nt=sum(ts)
        if scorer != (receiver if nt%2==0 else 1-receiver):quality['parity disagreement']+=1;continue
        # Validate alternating own offensive terminals / defensive gains in each stream.
        valid=True
        for i,es in enumerate(pair):
            own=(i==receiver)
            for e in es[1:]:
                t=e['type']
                if t in (18,19,20,22,23,24):
                    if not own:valid=False
                    if t in TURN:own=False
                elif t in GAIN:
                    if own:valid=False
                    own=True
        if not valid:quality['sequence disagreement']+=1;continue
        accepted_types.update(e['type'] for es in pair for e in es)
        quality['accepted']+=1; points.append((f.stem,nt,int(nt==0 and scorer==receiver)))
        for e in pair[1-receiver]:
            if e['type']==7 and number(e,'pullY') is not None:
                pulls.append((f.stem,100-number(e,'pullY')))
        for i,es in enumerate(pair):
            origin='pull' if i==receiver else None; passes=[]; first=None
            for e in es[1:]:
                t=e['type']
                if t in GAIN:
                    origin='turnover'; passes=[]; first=None
                    if t==12:
                        possessions.append(dict(game=f.stem,origin=origin,goal=True,n=0,start=None,gain=None))
                        origin=None
                elif t in (18,19,20,22,23,24):
                    if first is None:
                        first=number(e,'throwerY')
                        if first is not None and origin=='pull':pickups.append((f.stem,first-20))
                    if t in (18,19):passes.append(e)
                    if t in TURN or t==19:
                        end=number(e,'receiverY') if t==19 else None
                        possessions.append(dict(game=f.stem,origin=origin,goal=t==19,n=len(passes),start=None if first is None else first-20,gain=None if end is None or first is None else end-first))
                        if t in TURN:
                            y=number(e,'receiverY' if t==20 else 'turnoverY')
                            if y is not None:turnovers.append((f.stem,(y-20) if i==receiver else (100-y),t))
                        origin=None; passes=[];first=None

lines=['# UFA 2025 point calibration','', 'Run `python3 data/analyze_points.py` offline. Source: owner-supplied 157-game UFA cache, `data/raw/events/*.json`; no network or simulator outputs used.', '', '## Reconstruction and inferred meanings', '',
'All numeric meanings are inferred from fields and sequences, not independently verified official documentation. Type 1 starts a pulling/defensive point; 2 starts a receiving/offensive point. Types 7–10 are pull variants (only 7 has landing coordinates). 18 is a completion, 19 a goal completion; 20 a drop, 22 a throwaway (including opposing blocks), 23 a stall-like turnover, 24 another offensive turnover of unknown subtype. Defensive counterparts: 11 block/interception, 12 Callahan (turnover plus immediate defensive goal), 13 other opponent turnover, 14 rare opponent turnover of unknown subtype. Type 15 is opponent goal. 16/17 appear to be stoppage/yardage adjustment events; 3/5/25 lineup changes; none creates possession boundaries here. 28–33 terminate periods; point matching uses period ordinal and recorded start clock, never wall timestamps. Ignored events cannot add boundaries. No block is counted twice: point turnover totals use offensive 20/22/23/24 from both streams; 11–14 validate them.', '',
'Only points with matching starts, opposite initial roles, reciprocal turnover counts, exactly one 19/12 goal, correct possession parity and alternating offensive/gain sequences are retained. This is a conservative complete-point subset, not all league points; excluded points may differ systematically. Quarter-ending possessions are excluded, not treated as failures. Own offensive terminal events define possessions; Callahans count as zero-pass scoring possessions. A hold means the receiving team scores on its FIRST possession without any turnover, not eventual receiving-team point victory.', '',
'Coordinates are interpreted in yards in each team’s attack frame: own goal line y=20, attacking goal line y=100, end boundaries 0/120. Goal receiver coordinates above 100 support this convention. Depth from own goal line is y−20 (negative means own endzone). Pulls are recorded in the pulling team’s frame, so receiving depth is 100−pullY. Turnover locations are reported in the ORIGINAL point-receiver’s frame (not always the team gaining possession). First thrower y−20 is a pickup/start proxy; it can reflect a walk to the line, brick, penalty or missing event, rather than the raw landing spot. Post-turnover scoring bins use the gaining team’s first throw location, avoiding assumptions about pickup/brick relocations. Net distance gained is goal receiverY minus first throwerY, includes endzone yards and any unrecorded penalties; it is not summed pass distance.', '',
'95% intervals for proportions are Wilson intervals (independence approximation; within-game correlation can make them optimistic). Means use 1,000 game-cluster bootstrap resamples, seed 2025. Distribution rows give bin shares with Wilson intervals; percentile summaries are descriptive.', '', '## Coverage', '', '| Audit | Points |','|---|---:|']
lines += [f'| {k} | {v:,} |' for k,v in quality.items()]
def table(title,headers,rows):
    lines.extend(['',f'## {title}','','| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|'])
    lines.extend('| '+' | '.join(map(str,r))+' |' for r in rows)
lines += ['', f'Accepted sample spans {len(set(g for g,t,h in points))} games. Duplicate start-clock keys within a period are removed before matching; candidate count is the union of remaining stream keys. Missing or ambiguous point starts are not imputed.']
n=len(points);held=sum(p[2] for p in points)
table('Point outcomes',['Metric','Count / denominator','Estimate (95% CI)'],[
('First-possession hold',f'{held:,} / {n:,}',wilson(held,n)),('Turnovers per point',f'{sum(p[1] for p in points):,} / {n:,}',mean_ci([(g,t) for g,t,h in points])),('Possessions per point',f'{sum(p[1]+1 for p in points):,} / {n:,}',mean_ci([(g,t+1) for g,t,h in points]))])
table('Turnovers per point distribution',['Turnovers','Points','Share (95% CI)'],[(str(t),sum(p[1]==t for p in points),wilson(sum(p[1]==t for p in points),n)) for t in sorted(set(p[1] for p in points))])
lines += ['', 'Possessions-per-point distribution is exactly the turnover distribution above shifted by +1 (1 through 10 possessions).', '', 'Offensive turnover labels in accepted points: '+', '.join(f'{name}: {accepted_types[t]:,}' for t,name in [(20,'drop'),(22,'throwaway / blocked throw'),(23,'stall-like'),(24,'unknown turnover')])+'. Defensive counterparts: '+', '.join(f'{name}: {accepted_types[t]:,}' for t,name in [(11,'block/interception'),(12,'Callahan'),(13,'other opponent turnover'),(14,'unknown opponent turnover')])+'. These counterpart counts overlap offensive labels and must not be added to them. The cache does not separate a caught interception from a knocked-down block.', '', 'All finite turnover endpoints are retained, including repeated thrower coordinates: unlike distance-fit analysis, zero displacement is not evidence sufficient to discard a possession boundary. '+str(sum(t for g,t,h in points)-len(turnovers))+' turnovers lack usable endpoints; no endpoint is imputed.']
goals=[p for p in possessions if p['goal']];quick=sum(p['origin']=='turnover' and 1<=p['n']<=3 for p in goals)
table('Scoring possessions',['Start','Count','Completed passes incl. goal (95% CI)','Net yards gained: count; mean (95% CI)'],[(label,len(ps),mean_ci([(p['game'],p['n']) for p in ps]),f"{sum(p['gain'] is not None for p in ps):,}; "+mean_ci([(p['game'],p['gain']) for p in ps if p['gain'] is not None])) for label,ps in [('All',goals),('Pull',[p for p in goals if p['origin']=='pull']),('Turnover',[p for p in goals if p['origin']=='turnover'])]])
lines+=['',f'Goals within 1–3 completed throws of the latest turnover: **{quick:,}/{len(goals):,} = {wilson(quick,len(goals))}** of ALL goals. Among turnover-origin goals: '+wilson(quick,sum(p['origin']=='turnover' for p in goals))+'. Zero-pass Callahans are outside 1–3. Failed possessions between the initial pull and final turnover do not contribute passes to this measure.']
for title,rows in [('Pull landing depth',pulls),('Pull pickup / first-throw depth',pickups),('Turnover depth from original receiving goal line',[(g,y) for g,y,t in turnovers])]:
    vals=sorted(v for g,v in rows)
    lines+=['',f'## {title}', '',f'N={len(vals):,}; mean (95% CI) **{mean_ci(rows)} yd**; p10 / median / p90: '+ ' / '.join(f'{vals[round(q*(len(vals)-1))]:.2f}' for q in (.1,.5,.9))+' yd.']
    bins=[(-math.inf,0),(0,10),(10,20),(20,40),(40,60),(60,80),(80,math.inf)]
    table(title+' bins',['Depth yards','Count','Share (95% CI)'],[(f'[{a}, {b})',sum(a<=v<b for v in vals),wilson(sum(a<=v<b for v in vals),len(vals))) for a,b in bins])
post=[p for p in possessions if p['origin']=='turnover']; located=[p for p in post if p['start'] is not None]
table('Score rate after turnover by gaining team start position',['Own-goal-line depth yd','Possessions','Goals','Score rate (95% CI)'],[(f'[{a}, {b})',len(ps),sum(p['goal'] for p in ps),wilson(sum(p['goal'] for p in ps),len(ps))) for a,b in bins for ps in [[p for p in located if a<=p['start']<b]]])
lines+=['',f'Post-turnover possessions: {len(post):,}, including {len(post)-len(located):,} without a first-throw location (including Callahans); location bins omit these. All post-turnover score rate: {wilson(sum(p["goal"] for p in post),len(post))}.', '', '## Calibration targets', '',f'Use these as descriptive targets with the selection caveat above: first-possession hold **{held/n:.2%}**; turnovers/point **{sum(p[1] for p in points)/n:.2f}**; completed passes/scoring possession **{sum(p["n"] for p in goals)/len(goals):.2f}** (includes goal); pull pickup proxy mean **{sum(v for g,v in pickups)/len(pickups):.2f} yd** from own goal line; goals within 1–3 throws after a turnover **{quick/len(goals):.2%}**. Use the field-position table to assess short-field gifts. These are 7v7 professional observations; they do not establish that a 3v3 simulator must match them exactly. Do not calibrate landing and pickup as though they were the same variable.', '', 'Raw event-type counts: `'+json.dumps(dict(sorted(types.items())))+'`.']
(ROOT/'POINTS.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[-5:]));print(dict(quality))
assert len(goals)==len(points)
assert len(possessions)==sum(t+1 for g,t,h in points)
