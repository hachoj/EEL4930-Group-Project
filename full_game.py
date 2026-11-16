"""v7 full games; v1 remains available through ultimate.py --single-possession."""
import argparse, collections, concurrent.futures, hashlib, itertools, json, math, os, pickle, random, re, subprocess, time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
import ultimate as u
import joint_calculator as j

PRESSURE=1.0

MODES=['tight_front','tight_behind','trail','poach_lane','poach_deep','double_B','double_C']
# Independent ordinary tactics, plus reciprocal switches with independent positioning.
DEF_ACTIONS=[(None,m) for m in itertools.product(range(7),repeat=3)]+[(pair,m) for pair in itertools.combinations(range(3),2) for m in itertools.product(range(7),repeat=3)]

def remap_marks(marks,pair):
    m=np.array(marks).copy()
    if pair is not None:m[:,list(pair)]=m[:,list(pair[::-1])]
    return m

def defense_props(o,d,marks):
    props=j.defense_proposals(o,d,marks)
    for i in range(3):
        man=o[np.arange(len(o)),marks[:,i]]
        receiver=o[:,1:][np.arange(len(o)),np.linalg.norm(o[:,1:]-o[:,0,None],axis=2).argmin(1)]
        targets=[(man+o[:,0])/2,np.column_stack((man[:,0],np.maximum(16,man[:,1]))),o[:,1]+np.array([0,-1]),o[:,2]+np.array([0,-1])]
        for target in targets:
            c=np.clip(d[:,i,None]+j.DIRECTIONS,(0,0),(9,19))
            obstacles=np.concatenate((o,np.delete(d,i,axis=1)),axis=1)
            legal=~(c[:,:,None]==obstacles[:,None]).all(-1).any(-1)
            score=-((c-target[:,None])**2).sum(-1)
            score=np.where(legal,score,-1e9)
            props[i].append(c[np.arange(len(o)),score.argmax(1)])
    return props

def defense_candidates(o,d,marks):
    base=defense_props(o,d,marks); switched={}
    for pair in itertools.combinations(range(3),2):switched[pair]=defense_props(o,d,remap_marks(marks,pair))
    for pair,modes in DEF_ACTIONS:
        props=base if pair is None else switched[pair]
        proposed=np.stack([props[i][mode] for i,mode in enumerate(modes)],axis=1)
        x,y=j.resolve_batch(o,d,1,proposed)
        yield x,y,remap_marks(marks,pair)

def throw_model(o,d,r,pressure=None):
    """Return completion and unconditional failure masses [drop,D1,D2,D3]."""
    pressure=PRESSURE if pressure is None else pressure
    if not 0<=pressure<=1:raise ValueError("pressure must be in [0,1]")
    a=o[:,r]-o[:,0];length=np.linalg.norm(a,axis=1)
    b=d-o[:,r,None];norm=np.linalg.norm(b,axis=2)
    den=length[:,None]*norm
    cos=np.divide((-a[:,None]*b).sum(-1),den,out=np.ones_like(den),where=den!=0)
    receiver=1-np.prod(1-.6*pressure*np.maximum(0,1-norm/3)*(.25+.75*(1+cos)/2),axis=1)
    v=d-o[:,0,None];den2=(a*a).sum(1)
    projection=np.divide((v*a[:,None]).sum(-1),den2[:,None],out=np.zeros_like(norm),where=den2[:,None]!=0)
    closest=o[:,0,None]+np.clip(projection,0,1)[:,:,None]*a[:,None]
    lane=.06*pressure*np.maximum(0,1-np.linalg.norm(d-closest,axis=2)/1.5)*((projection>.1)&(projection<.98))
    base=1/(1+np.exp(-(4.15701518-.06417449*length*5)))
    base*=np.where(u.force.is_break(o[:,0],o[:,r]),u.force.BREAK_MULTIPLIER,1.)
    p=base*(1-receiver)*np.prod(1-lane,axis=1)
    # Sequential disjoint hazards; receiver-pressure failures count as blocks at nearest D.
    masses=np.zeros((len(o),4));masses[:,0]=1-base
    near=norm.argmin(1);masses[np.arange(len(o)),near+1]=base*receiver
    survival=base*(1-receiver)
    for k in range(3):masses[:,k+1]+=survival*lane[:,k];survival*=1-lane[:,k]
    return p,masses

def mirror(p):return [9-int(p[0]),19-int(p[1])]

def flip(o,d,spot,interceptor=None):
    """Rotate 180 degrees, swap teams, pick up at spot without overlapping anyone."""
    new=[mirror(p) for p in d];other=[mirror(p) for p in o];target=mirror(spot)
    holder=min(range(3),key=lambda i:math.dist(new[i],target)) if interceptor is None else interceptor
    new[0],new[holder]=new[holder],new[0]
    new[0]=target
    occupied={tuple(p) for p in new}
    for i,p in enumerate(other):
        if tuple(p) in occupied:
            vacant=([x,y] for x in range(10) for y in range(20) if (x,y) not in occupied and [x,y] not in other[i+1:])
            other[i]=min(vacant,key=lambda q:(math.dist(q,p),q))
        occupied.add(tuple(other[i]))
    return new,other,u.assign_marks(new,other)

def formation(spot):
    # Only used to project transfer endpoints in the sampled model, never teleport in play.
    o=[list(spot)]
    cells=[[x,y] for x in range(10) for y in range(20)]
    for offset in ((-2,2),(2,3)):
        target=np.clip(np.array(spot)+offset,(0,0),(9,19))
        o.append(min((p for p in cells if p not in o),key=lambda p:math.dist(p,target)))
    d=[]
    for p in o:d.append(min((q for q in cells if q not in o+d),key=lambda q:math.dist(q,[p[0],min(19,p[1]+1)])))
    return o,u.force.seal(o,d,u.assign_marks(o,d))

def pull_setup(rng,depth_min=2,depth_max=3,run_turns=3):
    """Scripted setup, not coach decisions. Frames preserve lineup identities.

    Receiver walks to sampled landing; teammates wait during pickup. Then both
    teams run legal one-square steps for run_turns. Holder remains stationary.
    """
    if not 0<=depth_min<=depth_max<=16 or run_turns<0:raise ValueError('invalid pull configuration')
    o=[[2,2],[5,2],[8,2]];d=[[2,17],[5,17],[8,17]]
    depth=rng.choices([2,3],weights=[.6,.4])[0] if (depth_min,depth_max)==(2,3) else rng.randint(depth_min,depth_max)
    landing=[rng.randrange(10),depth]
    pick=min(range(3),key=lambda k:math.dist(o[k],landing))
    frames=[dict(phase='flight',o=[q[:] for q in o],d=[q[:] for q in d])]
    def step(targets,side):
        nonlocal o,d
        team=o if side==0 else d;other=d if side==0 else o
        proposed=[];occupied={tuple(q) for q in team+other}
        for k,q in enumerate(team):
            occupied.remove(tuple(q))
            cells=[u.move(q,delta) for delta in u.DELTAS]
            dest=min((v for v in cells if tuple(v) not in occupied),key=lambda v:(math.dist(v,targets[k]),v))
            proposed.append(dest);occupied.add(tuple(dest))
        x,y=u.resolve(proposed,d,0,o,d) if side==0 else u.resolve(o,proposed,1,o,d)
        o,d=x,y
    while o[pick]!=landing:
        targets=[q[:] for q in o];targets[pick]=landing
        step(targets,0)
        frames.append(dict(phase='pickup',o=[q[:] for q in o],d=[q[:] for q in d]))
        if len(frames)>30:raise RuntimeError('pull pickup blocked')
    for _ in range(run_turns):
        targets=[([max(0,min(9,landing[0]+(-3 if k<pick else 3))),min(16,landing[1]+3)] if k!=pick else landing) for k in range(3)]
        step(targets,0);step(o,1)
        frames.append(dict(phase='rundown',o=[q[:] for q in o],d=[q[:] for q in d]))
    o[0],o[pick]=o[pick],o[0]
    return o,d,u.assign_marks(o,d),dict(landing=landing,pickup_player=pick,frames=frames)

ZONE_CENTERS=[[x,y] for y in (2,7,12,16,18) for x in (1,4,8)]
RESTART=np.array([u.INDEX[u.key(*formation(p))] for p in ZONE_CENTERS])
GOAL_START=u.INDEX[u.key(*u.start_positions(0,0))]

def failure_zones(o,d,r):
    spots=np.concatenate((o[:,r,None],d),axis=1)
    return j.zones(np.array([9,19])-spots)

class Solver:
    def __init__(self,samples=8,max_hold=3,gamma=.97,tol=1e-7,out=Path('outputs_dev/v8'),pressure=1.,pull_min=2,pull_max=3,pull_run_turns=3):
        self.pressure=pressure
        self.pull_config=(pull_min,pull_max,pull_run_turns)
        starts=[pull_setup(random.Random(9500+i),*self.pull_config) for i in range(128)]
        self.goal_starts=np.array([u.INDEX[u.key(o,d)] for o,d,_,_ in starts])
        start=time.monotonic();self.max_hold=max_hold;self.gamma=gamma;n=len(u.KEYS);self.n=n
        rng=random.Random(1201);reps=[u.representative(k,rng) for k in u.KEYS for _ in range(samples)]
        o=np.array([r[0] for r in reps],dtype=np.int16);d=np.array([r[1] for r in reps],dtype=np.int16);del reps
        marks=np.array([u.assign_marks(x.tolist(),y.tolist()) for x,y in zip(o,d)])
        rows=np.repeat(np.arange(n),samples);self.matrices=[[],[]]
        props=j.proposals(o,d)
        for side in (0,1):
            candidates=(j.realize(o,d,0,a,props)+(marks,) for a in range(300)) if side==0 else ((x,y,0,m) for x,y,m in defense_candidates(o,d,marks))
            for a,(x,y,r,m) in enumerate(candidates):
                ids,_=j.transitions(x,y,r,n,m)
                if r:
                    p,fail=throw_model(x,y,r,pressure);fz=failure_zones(x,y,r)
                    # score column n; opponent restarts n+1..n+15.
                    cols=np.concatenate((ids,*[n+1+fz[:,i] for i in range(4)]))
                    weights=np.concatenate((p,*[fail[:,i] for i in range(4)]))/samples
                    mat=csr_matrix((weights,(np.tile(rows,5),cols)),shape=(n,n+16))
                else:mat=csr_matrix((np.ones(len(rows))/samples,(rows,ids)),shape=(n,n+16))
                mat.eliminate_zeros();self.matrices[side].append(mat)
                if a%50==0:print('build',side,a,round(time.monotonic()-start,2),flush=True)
        build=time.monotonic()-start
        self.V=np.zeros((max_hold,2,n));solve=time.monotonic();residual=float('inf')
        for iteration in range(2000):
            nxt=self.backup(self.V);residual=float(np.max(abs(nxt-self.V)));self.V=nxt
            if iteration%20==0:print('solve',iteration,'residual',residual,'seconds',round(time.monotonic()-solve,2),flush=True)
            if residual<tol:break
        if residual>=tol:raise RuntimeError(f'fixed point failed: {residual}')
        self.info=dict(pressure=pressure,pull_config=self.pull_config,states=2*n*max_hold,states_per_side=n*max_hold,base_states=n,actions_offense=300,actions_defense=len(DEF_ACTIONS),samples_per_state=samples,max_hold=max_hold,gamma=gamma,build_seconds=build,solve_seconds=time.monotonic()-solve,iterations=iteration+1,residual=residual,error_bound=residual/(1-gamma),convergence='discounted max/min Bellman contraction; hold counter explicit')
        print(json.dumps(self.info),flush=True)
        out.mkdir(parents=True,exist_ok=True);(out/'solver.json').write_text(json.dumps(self.info,indent=2))
        with (out/'solver.pkl').open('wb') as f:pickle.dump(self,f)
    def tail(self,v):return np.r_[1-self.gamma*np.mean(v[0,0,getattr(self,'goal_starts',np.array([GOAL_START]))]),-self.gamma*v[0,0,RESTART]]
    def backup(self,v):
        nxt=np.empty_like(v);tail=self.tail(v)
        for c in range(self.max_hold):
            for side in (0,1):
                best=np.full(self.n,-np.inf if side==0 else np.inf)
                vectors={r:np.r_[self.gamma*v[0 if r else min(c+1,self.max_hold-1) if side==0 else c,1-side],tail] for r in (0,1)}
                for a,mat in enumerate(self.matrices[side]):
                    r=j.OFF_ACTIONS[a][2] if side==0 else 0
                    if side==0 and not r and c==self.max_hold-1:continue
                    q=mat@vectors[int(bool(r))]
                    best=np.maximum(best,q) if side==0 else np.minimum(best,q)
                nxt[c,side]=best
        return nxt
    def evaluate(self,x,y,r,marks,c,side):
        ids,_=j.transitions(x,y,r,self.n,marks)
        if not r:return self.gamma*self.V[c+1 if side==0 else c,1-side,ids]
        p,fail=throw_model(x,y,r,getattr(self,'pressure',1.));fz=failure_zones(x,y,r)
        success=np.where(ids==self.n,self.tail(self.V)[0],self.gamma*self.V[0,1-side,np.minimum(ids,self.n-1)])
        return p*success+(fail*(-self.gamma*self.V[0,0,RESTART[fz]])).sum(1)
    def concrete(self,o,d,side,c,marks):
        oo=np.array(o)[None];dd=np.array(d)[None];mm=np.array(marks)[None]
        candidates=[];values=[]
        if side==0:
            props=j.proposals(oo,dd)
            count=300;xx=np.repeat(oo,count,0);yy=np.repeat(dd,count,0);ms=np.repeat(mm,count,0)
            intents=np.array(j.OFF_ACTIONS);proposed=xx.copy()
            for k in range(2):proposed[:,k+1]=np.array(props[k])[:,0][intents[:,k]]
            xx,yy=j.resolve_batch(xx,yy,0,proposed);vs=np.full(count,-np.inf)
            for r in range(3):
                mask=intents[:,2]==r
                if r==0 and c==self.max_hold-1:continue
                vs[mask]=self.evaluate(xx[mask],yy[mask],r,ms[mask],c,side)
            a=max(range(count),key=lambda a:(vs[a],sum(xx[a,1:,1]),np.count_nonzero((xx[a]!=oo[0]).any(1))))
            self.last_action=dict(action=['hold','throw_B','throw_C'][int(intents[a,2])],intents={'B':j.INTENTS[intents[a,0]],'C':j.INTENTS[intents[a,1]]})
            return xx[a].tolist(),yy[a].tolist(),int(intents[a,2]),marks[:]
        # Batch all joint defenses for a single concrete state.
        count=len(DEF_ACTIONS);xx=np.repeat(oo,count,0);dd=np.repeat(dd,count,0);ms=np.repeat(mm,count,0);proposed=dd.copy()
        for pair in [None,*itertools.combinations(range(3),2)]:
            indices=np.array([i for i,(p,m) in enumerate(DEF_ACTIONS) if p==pair]);modes=np.array([DEF_ACTIONS[i][1] for i in indices])
            remapped=remap_marks(mm,pair);props=defense_props(oo,dd[:1],remapped) if pair is None else defense_props(oo,dd[:1],remapped)
            ms[indices]=remapped
            for k in range(3):proposed[indices,k]=np.array(props[k])[:,0][modes[:,k]]
        xx,yy=j.resolve_batch(xx,dd,1,proposed)
        a=int(self.evaluate(xx,yy,0,ms,c,side).argmin())
        pair,modes=DEF_ACTIONS[a]
        self.last_action=dict(modes={f'D{k+1}':MODES[v] for k,v in enumerate(modes)},switch=list(pair) if pair else None)
        return xx[a].tolist(),yy[a].tolist(),0,ms[a].tolist()

def scripted(o,d,side,c,max_hold,marks,action_info=None):
    if side==0:
        x,y,_=u.scripted_cut(o,d);targets=[r for r in (1,2) if x[r][1]>x[0][1]]
        probs={r:float(throw_model(np.array(x)[None],np.array(y)[None],r)[0][0]) for r in (1,2)}
        r=max(targets,key=probs.get) if targets else 0
        if c==max_hold-1:r=max((1,2),key=probs.get)
        elif not r or probs[r]<.65:r=0
        if action_info is not None:
            action_info.update(action=['hold','throw_B','throw_C'][r],intents={'B':'scripted_cut','C':'scripted_cut'})
        return x,y,r,marks[:]
    pair=None
    # Crossing assignments: accept nearest bijection only for a close pair that improves cost.
    nearest=u.assign_marks(o,d)
    differences=[k for k in range(3) if nearest[k]!=marks[k]]
    if len(differences)==2 and math.dist(o[marks[differences[0]]],o[marks[differences[1]]])<=4:pair=tuple(differences)
    mm=remap_marks(np.array(marks)[None],pair);props=defense_props(np.array(o)[None],np.array(d)[None],mm)
    modes=[]
    for k,m in enumerate(mm[0]):
        if m==0 and min(math.dist(o[0],p) for p in o[1:])<4:mode=5+int(math.dist(o[0],o[2])<math.dist(o[0],o[1]))
        elif math.dist(o[m],o[0])>7:mode=4 if o[m][1]>=14 else 3
        else:mode=0
        modes.append(mode)
    proposed=np.array([[props[k][mode][0] for k,mode in enumerate(modes)]])
    x,y=j.resolve_batch(np.array(o)[None],np.array(d)[None],1,proposed)
    if action_info is not None:action_info.update(modes={f'D{k+1}':MODES[v] for k,v in enumerate(modes)},switch=list(pair) if pair else None)
    return x[0].tolist(),y[0].tolist(),0,mm[0].tolist()

def offense_menu(o,d):
    """Exact post-resolution joint outcomes; base rows assume other receiver stays."""
    oo=np.array(o)[None];dd=np.array(d)[None];props=j.proposals(oo,dd)
    menu={label:{name:props[k][i][0].tolist() for i,name in enumerate(j.INTENTS)} for k,label in enumerate(('B','C'))}
    outcomes={}
    for b,ci in itertools.product(j.INTENTS,repeat=2):
        proposed=np.array([[o[0],menu['B'][b],menu['C'][ci]]])
        x,y=j.resolve_batch(oo,dd,0,proposed)
        outcomes[b,ci]=dict(o=x[0].tolist(),throws={})
        for r,label in enumerate(('B','C'),1):
            p,fail=throw_model(x,y,r)
            outcomes[b,ci]['throws'][label]=dict(p_catch=float(p[0]),drop=float(fail[0,0]),interception=float(fail[0,1:].sum()))
    return menu,outcomes

def defense_menu(o,d,marks):
    oo=np.array(o)[None];dd=np.array(d)[None];mm=np.array(marks)[None]
    props=defense_props(oo,dd,mm)
    menu={f'D{k+1}':{name:props[k][i][0].tolist() for i,name in enumerate(MODES)} for k in range(3)}
    for pair in itertools.combinations(range(3),2):
        ps=j.defense_proposals(oo,dd,remap_marks(mm,pair))
        for k in pair:menu[f'D{k+1}'][f'switch_D{pair[1]+1 if k==pair[0] else pair[0]+1}']=ps[k][0][0].tolist()
    return menu

def render_llm_prompt(o,d,side,c,max_hold,marks,score=None,target=10,defense_info=None,team=None):
    """Readable decision information computed with the concrete game's functions."""
    lines=[f'Ultimate Frisbee: you coach {"OFFENSE" if side==0 else "DEFENSE"}.',
        "Maximize your team's point differential; turnovers give the opponent the disc at that spot.",
        f'You control team {team if team is not None else chr(63)}. Score (team 0, team 1): {score if score is not None else [0,0]}; target {target}.',
        'Field: x=0..9, y=0..19; each square is 5 yards. Offense attacks +y (N); a catch in rows 17..19 scores.',
        f'A holds the disc at {o[0]}, {max(0,17-o[0][1])} rows from the scoring endzone; A cannot move.',
        f'B is at {o[1]}; C is at {o[2]}. Letters are current roles; the catcher becomes A.',
        f'Hold counter {c} of 0..{max_hold-1}: offensive turn {c+1} since gaining the disc; throw required on turn {max_hold}. '+('FORCED THROW: hold is illegal.' if c==max_hold-1 else 'Hold is legal.'),
        'Turns alternate: offense moves both receivers, then holds or throws; defense moves all defenders on its own turn.',
        'Moves are at most one square including diagonals. Blocked moves stay; collisions resolve B then C, or D1 then D2 then D3.',
        f'After catches the marker seals the holder\'s left. Listed probabilities include break multiplier {u.force.BREAK_MULTIPLIER}.',
        'Defenders near the throwing segment add interception risk, beyond receiver pressure. Failure risks below are unconditional and sum with catch to 1.',
        'Drops/incompletions give the opponent the disc at the receiver; interceptions give it at the intercepting defender. Coordinates then rotate 180 degrees.',
        'On an offensive turnover, the current defense becomes offense and attacks -y in these coordinates: a turnover at row y leaves the new offense y-2 rows from its scoring endzone (zero if y<=2).']
    for k in range(3):
        label=f'D{k+1}';mode=(defense_info or {}).get('modes',{}).get(label,'unknown (initial setup or no recorded action)')
        lines.append(f'{label} at {d[k]} marks {"ABC"[marks[k]]}; last chosen mode: {mode}. If this defender intercepts here, the current defense gains the disc {max(0,d[k][1]-2)} rows from its scoring endzone.')
    if side==0:
        menu,outcomes=offense_menu(o,d)
        lines+=['Receiver options: stay, SW, W, NW, S, N, SE, E, NE, get_open (most separation with slight +y preference). Direction names are intents: each chooses the closest legal neighboring move; use the listed resulting square.',
            'Base table: the OTHER receiver chooses stay. Each row is intent -> resulting square | catch / drop / interception probabilities | turnover consequence.']
        def row(label,intent,result):
            r='ABC'.index(label);q=result['o'][r];v=result['throws'][label]
            return f'{label} {intent} -> {q} | {v["p_catch"]:.6f} / {v["drop"]:.6f} / {v["interception"]:.6f} | drop gives them disc {max(0,q[1]-2)} rows from their endzone'+(' | catch SCORES' if q[1]>=17 else '')
        for label in ('B','C'):
            for intent in j.INTENTS:lines.append(row(label,intent,outcomes[(intent,'stay') if label=='B' else ('stay',intent)]))
        lines.append('Joint corrections below override base rows when both receivers choose moves that collide; all unlisted joint choices have exactly the base outcomes (other-receiver movement has no other effect on throw probability).')
        corrections=0
        for (b,ci),result in outcomes.items():
            for label,r,base in [('B',1,outcomes[b,'stay']),('C',2,outcomes['stay',ci])]:
                if result['o'][r]!=base['o'][r]:
                    lines.append(f'Joint move_B={b}, move_C={ci}: '+row(label,b if label=='B' else ci,result));corrections+=1
        if not corrections:lines.append('No joint corrections for this state.')
        lines.append('Hold: move receivers with no immediate throw risk, keep disc at A, increment counter; defense acts next. A catch resets the counter. '+('ILLEGAL now.' if c==max_hold-1 else f'{max_hold-1-c} hold(s) remain before a forced throw.'))
        example={'move_B':'N','move_C':'get_open','action':'throw_B'}
        lines.append('Choose move_B and move_C from the named intents; action is throw_B, throw_C'+(', or hold.' if c<max_hold-1 else '.'))
    else:
        menu=defense_menu(o,d,marks)
        descriptions=dict(tight_front='move toward thrower side of own mark; give up rear space',tight_behind='move behind own mark; give up front space',trail='follow current side of own mark; give up opposite side',poach_lane='leave own mark for midpoint of mark-to-holder lane; give up tight coverage',poach_deep='leave own mark to guard deep space in front of endzone; give up short coverage',double_B='leave own mark to double B; give up own assignment',double_C='leave own mark to double C; give up own assignment')
        lines.append('Per-defender proposed destinations (other defenders assumed to stay; joint collisions may cause a stay):')
        for k in range(3):
            for mode,q in menu[f'D{k+1}'].items():
                explanation=descriptions.get(mode)
                if explanation is None:
                    partner=int(mode[-1])-1
                    explanation=f'swap marks with D{partner+1}, then tight_front on {"ABC"[marks[partner]]}; give up current assignment; partner must choose switch_D{k+1}'
                lines.append(f'D{k+1} {mode} -> {q}: {explanation}.')
        lines.append('Switch choices must be reciprocal; one reciprocal pair maximum. Other defenders can choose any listed mode.')
        example={'D1':'tight_front','D2':'poach_lane','D3':'tight_behind'}
    lines.append('Return only named-field JSON, for example: '+json.dumps(example))
    return '\n'.join(lines),menu

def llm(o,d,side,c,max_hold,marks,model,out,score=None,target=10,action_info=None,defense_info=None,team=None):
    prompt,menu=render_llm_prompt(o,d,side,c,max_hold,marks,score,target,defense_info,team)
    cache=out/'cache';cache.mkdir(parents=True,exist_ok=True);f=cache/(hashlib.sha256((model+prompt).encode()).hexdigest()+'.json')
    calls=0
    for attempt in range(2):
        try:
            if f.exists():answer=json.loads(f.read_text())
            else:
                calls+=1;proc=subprocess.run(['claude','-p','--model',model,'--output-format','json',prompt],capture_output=True,text=True,timeout=120,check=True)
                envelope=json.loads(proc.stdout);answer=envelope.get('result',envelope)
                if isinstance(answer,str):answer=json.loads(re.search(r'\{[^{}]*\}',answer).group())
            if side==0:
                x=[o[0][:]]+[menu[label][answer['move_'+label]] for label in ('B','C')];y=[p[:] for p in d];m=marks[:]
                r=['hold','throw_B','throw_C'].index(answer['action'])
                if not r and c==max_hold-1:raise ValueError('forced throw')
            else:
                y=[menu[f'D{k+1}'][answer[f'D{k+1}']] for k in range(3)];x=[p[:] for p in o];m=marks[:];r=0
                for k in range(3):
                    token=answer[f'D{k+1}']
                    if token.startswith('switch_D'):
                        partner=int(token[-1])-1
                        if partner==k or answer[f'D{partner+1}']!=f'switch_D{k+1}':raise ValueError('nonreciprocal switch')
                        m[k]=marks[partner]
            if action_info is not None:
                if side==0:action_info.update(action=answer['action'],intents={label:answer['move_'+label] for label in ('B','C')})
                else:
                    pairs=[(k,int(answer[f'D{k+1}'][-1])-1) for k in range(3) if answer[f'D{k+1}'].startswith('switch_D')]
                    action_info.update(modes={f'D{k+1}':answer[f'D{k+1}'] for k in range(3)},switch=list(pairs[0]) if pairs else None)
            x,y=u.resolve(x,y,side,o,d);tmp=f.with_suffix(f'.{os.getpid()}.tmp');tmp.write_text(json.dumps(answer));tmp.replace(f);return x,y,r,m,calls
        except (ValueError,KeyError,TypeError,AttributeError):
            if f.exists():f.unlink()
    return (*scripted(o,d,side,c,max_hold,marks,action_info),calls)

def game(team0,team1,seed,solver,max_hold=3,target=10,safety_cap=20000,model='haiku',out=Path('outputs_dev/v8'),first=0,pressure=1.,pull_min=2,pull_max=3,pull_run_turns=3):
    global PRESSURE
    PRESSURE=pressure
    if not 0<=pressure<=1:raise ValueError('pressure must be in [0,1]')
    if solver is not None and hasattr(solver,'pressure') and solver.pressure!=pressure:raise ValueError('solver pressure mismatch')
    if solver is not None and hasattr(solver,'pull_config') and solver.pull_config!=(pull_min,pull_max,pull_run_turns):raise ValueError('solver pull configuration mismatch')
    rng=random.Random(seed);teams=[team0,team1];active=first
    o,d,marks,pull=pull_setup(rng,pull_min,pull_max,pull_run_turns)
    pulls=[dict(pull,team=active,start_turn=1)]
    scores=[0,0];history=[];possessions=[];c=0;side=0;beg=0;throws=0;caught=0;calls=0;pos_throws=0;pos_caught=0;start_spot=o[0][:]
    defense_info=None
    for turn in range(safety_cap):
        action_info={}
        coach=teams[active if side==0 else 1-active]
        if coach=='Calculator':
            x,y,r,m=solver.concrete(o,d,side,c,marks);action_info.update(getattr(solver,'last_action',{}))
        elif coach=='Scripted':x,y,r,m=scripted(o,d,side,c,max_hold,marks,action_info)
        else:
            x,y,r,m,ncalls=llm(o,d,side,c,max_hold,marks,model,out,scores,target,action_info,defense_info,active if side==0 else 1-active);calls+=ncalls
        if side==0 and c==max_hold-1 and not r:raise RuntimeError('illegal forced hold')
        if side==1:defense_info=action_info.copy()
        rec=dict(action_names=action_info,turn=turn+1,side=side,team=active,coach=coach,hold_counter=c,o=x,d=y,marks=m,thrower=o[0],receiver=x[r] if r else None)
        o,d,marks=x,y,m;event=None;spot=None;interceptor=None
        if r:
            throws+=1;pos_throws+=1;p,fail=throw_model(np.array(o)[None],np.array(d)[None],r);p=float(p[0]);rec['p']=p
            if rng.random()<p:
                caught+=1;pos_caught+=1;rec['throw_result']='caught';c=0
                if o[r][1]>=17:scores[active]+=1;event='score'
                else:
                    o=[q[:] for q in o];o[0],o[r]=o[r],o[0];marks=[r if z==0 else 0 if z==r else z for z in marks];d=u.force.seal(o,d,marks)
            else:
                k=rng.choices(range(4),weights=fail[0],k=1)[0];event='interception' if k else 'drop';interceptor=k-1 if k else None
                spot=d[interceptor][:] if k else o[r][:];rec['throw_result']=event;rec['turnover_spot']=spot
        elif side==0:c+=1
        rec['score']=scores[:];history.append(rec)
        if event:
            possessions.append(dict(team=active,start_turn=beg+1,end_turn=turn+1,turns=turn+1-beg,outcome=event,score=scores[:],turnover_spot=spot,start_spot=start_spot,throws=pos_throws,completed=pos_caught));beg=turn+1
            if max(scores)>=target:break
            if event=='score':
                o,d,marks,pull=pull_setup(rng,pull_min,pull_max,pull_run_turns)
                pulls.append(dict(pull,team=1-active,start_turn=turn+2))
            else:o,d,marks=flip(o,d,spot,interceptor)
            defense_info=None
            active=1-active;side=0;c=0;pos_throws=0;pos_caught=0;start_spot=o[0][:]
        else:side=1-side
    return dict(model=model,pressure=pressure,pull_config=[pull_min,pull_max,pull_run_turns],pulls=pulls,teams=teams,seed=seed,first=first,score=scores,finished=max(scores)>=target,safety_cap_triggered=max(scores)<target,turns=len(history),throws=throws,completed=caught,llm_calls=calls,llm_decisions=sum(h['coach']=='LLM' for h in history),possessions=possessions,history=history)

class LocalUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        if module in ('__main__','__mp_main__') and name=='Solver':return Solver
        return super().find_class(module,name)

def load_solver(path):
    with open(path,'rb') as stream:return LocalUnpickler(stream).load()

_WORKER=None
_ARGS=None
def init_worker(path,args):
    global _WORKER,_ARGS
    _ARGS=args
    if 'Calculator' in (args.team0,args.team1):
        _WORKER=load_solver(path)
def worker(i):
    a=_ARGS;return game(a.team0,a.team1,a.seed+i,_WORKER,a.max_hold,a.target,a.safety_cap,a.model,a.out,i%2,a.pressure,a.pull_min,a.pull_max,a.pull_run_turns)

def summarize(games):
    dist=collections.Counter(f'{g["score"][0]}-{g["score"][1]}' for g in games)
    poss=[p for g in games for p in g['possessions']]
    return dict(n=len(games),final_scores=dict(sorted(dist.items())),wins_team0=sum(g['score'][0]>g['score'][1] for g in games),points_per_possession=[sum(p['outcome']=='score' for p in poss if p['team']==t)/max(1,sum(p['team']==t for p in poss)) for t in (0,1)],completion_rate=sum(g['completed'] for g in games)/max(1,sum(g['throws'] for g in games)),throws=sum(g['throws'] for g in games),mean_turns=float(np.mean([g['turns'] for g in games])),mean_coach_decisions=float(np.mean([g['turns']/2 for g in games])),safety_cap_triggers=sum(g['safety_cap_triggered'] for g in games),possessions=len(poss))

def main():
    p=argparse.ArgumentParser();p.add_argument('--pressure',type=float,default=1.);p.add_argument('--pull-min',type=int,default=2);p.add_argument('--pull-max',type=int,default=3);p.add_argument('--pull-run-turns',type=int,default=3);p.add_argument('--team0',choices=['Calculator','Scripted','LLM'],default='Calculator');p.add_argument('--team1',choices=['Calculator','Scripted','LLM'],default='Scripted');p.add_argument('--n',type=int,default=20);p.add_argument('--jobs',type=int,default=2);p.add_argument('--samples',type=int,default=8);p.add_argument('--max-hold',type=int,default=3);p.add_argument('--target',type=int,default=10);p.add_argument('--safety-cap',type=int,default=20000);p.add_argument('--model',choices=['haiku','opus'],default='haiku');p.add_argument('--out',type=Path,default=Path('outputs_dev/v8'));p.add_argument('--seed',type=int,default=1700);p.add_argument('--rebuild',action='store_true');a=p.parse_args()
    if min(a.max_hold,a.target,a.n,a.jobs,a.samples)<1:p.error('positive counts required')
    if not 0<=a.pressure<=1:p.error('pressure must be in [0,1]')
    a.out.mkdir(parents=True,exist_ok=True);cache=a.out/'solver.pkl';start=time.monotonic()
    if 'Calculator' in (a.team0,a.team1):
        if a.rebuild or not cache.exists():Solver(a.samples,a.max_hold,out=a.out,pressure=a.pressure,pull_min=a.pull_min,pull_max=a.pull_max,pull_run_turns=a.pull_run_turns)
        else:
            s=load_solver(cache)
            if getattr(s,'pressure',None)!=a.pressure or getattr(s,'pull_config',None)!=(a.pull_min,a.pull_max,a.pull_run_turns) or s.max_hold!=a.max_hold or s.info['samples_per_state']!=a.samples:raise ValueError('cache configuration mismatch; use --rebuild')
    with concurrent.futures.ProcessPoolExecutor(a.jobs,initializer=init_worker,initargs=(cache,a)) as pool:games=list(pool.map(worker,range(a.n)))
    prefix=f'{a.team0}_vs_{a.team1}';(a.out/f'{prefix}_games.json').write_text(json.dumps(games));summary=summarize(games);summary['wall_seconds']=time.monotonic()-start
    (a.out/f'{prefix}_run.json').write_text(json.dumps({**vars(a),'out':str(a.out),'wall_seconds':summary['wall_seconds']},indent=2))
    (a.out/f'{prefix}_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
