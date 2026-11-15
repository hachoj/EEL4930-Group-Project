"""Reproducible one-possession Ultimate benchmark. See README for model limits."""
import argparse, concurrent.futures, csv, hashlib, itertools, json, math, os, random, re, subprocess, time
from pathlib import Path
import numpy as np
OUT=Path('outputs_dev')
START_DEPTH=12
DELTAS=list(itertools.product((-1,0,1),repeat=2))
KEYS=list(itertools.product(range(15),range(15),range(15),range(3),range(3)))
INDEX={k:i for i,k in enumerate(KEYS)}
# Disc holder is canonical index zero; reordering after a catch preserves identity-free play.
def zone(p): return min(2,p[0]*3//10)+3*(p[1]//5 if p[1]<15 else 3 if p[1]<17 else 4)
def catch(o,d,r):
    a=np.array(o[0],float)-o[r]; dist=float(np.linalg.norm(a)); p=1/(1+math.exp((dist*5-60)/20))
    for q in d:
        b=np.array(q,float)-o[r]; n=float(np.linalg.norm(b)); cos=float(a@b)/(dist*n) if dist*n else 1.0
        p*=1-.6*max(0,1-n/3)*(.25+.75*(1+cos)/2)
    return p

def key(o,d):
    labels=[]
    for r in (1,2):
        a=np.array(o[0])-o[r]; q=min(d,key=lambda x:math.dist(x,o[r])); b=np.array(q)-o[r]
        labels.append(2 if np.linalg.norm(b)>=3 else (0 if a@b>=0 else 1))
    return tuple(map(zone,o))+tuple(labels)
def move(p,delta): return [max(0,min(9,p[0]+delta[0])),max(0,min(19,p[1]+delta[1]))]
def toward(p,q): return move(p,[int(np.sign(q[i]-p[i])) for i in (0,1)])
def unique(o,d): return len({tuple(p) for p in o+d})==6

def resolve(o,d,side,old_o,old_d):
    # Sequential reservations: stationary opponents and unprocessed teammates block a square.
    team=o if side==0 else d; old=old_o if side==0 else old_d
    occupied={tuple(p) for p in (d if side==0 else o)+old}
    for j in range(3):
        occupied.discard(tuple(old[j]))
        if tuple(team[j]) in occupied: team[j]=old[j][:]
        occupied.add(tuple(team[j]))
    return o,d

def start_positions(seed,depth=None):
    rng=random.Random(seed)
    b=START_DEPTH if depth is None else depth
    o=[[2,b],[5,b+1],[8,b+2]]
    d=[[p[0],p[1]+rng.choice((1,2))] for p in o]
    return o,d

def action(o,d,side,a):
    old_o=[list(x) for x in o]; old_d=[list(x) for x in d]
    o=[list(x) for x in o]; d=[list(x) for x in d]; r=0
    if side==0:
        # 0 stationary hold, 1 advance, 2 spread, 3/4 advance then throw.
        if a:
            for j in (1,2): o[j]=toward(o[j],([0 if j==1 else 9,19] if a==2 else [o[j][0],19]))
        r=a-2 if a>=3 else 0
    else:
        # 0 hold, 1 mark in front, 2 behind, 3 switch assignments.
        for j in range(3):
            if a:
                target=o[(j+1)%3] if a==3 else o[j]
                target=[target[0],target[1]+(1 if a==2 else -1)]
                d[j]=toward(d[j],target)
    o,d=resolve(o,d,side,old_o,old_d)
    return o,d,r

def outcomes(o,d,side,a):
    x,y,r=action(o,d,side,a)
    if not r:return [(1.,INDEX[key(x,y)])]
    p=catch(x,y,r)
    if x[r][1]>=17:return [(p,-1),(1-p,-2)]
    x[0],x[r]=x[r],x[0]
    return [(p,INDEX[key(x,y)]),(1-p,-2)]

def far_point(o,rng):
    while True:
        q=[rng.randrange(10),rng.randrange(20)]
        if all(math.dist(q,p)>=3 for p in o[1:]):return q

def representative(k,rng):
    # Rejection produces exactly the requested key, including correlated labels.
    for attempt in range(100000):
        o=[[rng.choice([x for x in range(10) if x*3//10==z%3]),rng.randrange(*((z//3*5,z//3*5+5) if z//3<3 else (15,17) if z//3==3 else (17,20)))] for z in k[:3]]
        d=[]
        for j,label in enumerate(k[3:],1):
            if label==2:d.append(far_point(o,rng))
            else:
                candidates=[move(o[j],v) for v in itertools.product(range(-2,3),repeat=2) if 0<math.hypot(*v)<3]
                rng.shuffle(candidates)
                d.append(next((q for q in candidates if ((np.array(o[0])-o[j])@(np.array(q)-o[j])>=0)==(label==0)),o[j]))
        d.append(far_point(o,rng))
        if unique(o,d) and key(o,d)==k:return o,d
    raise RuntimeError(f'Could not sample key {k}')

class Solver:
    def __init__(self,samples=30):
        start=time.monotonic(); n=len(KEYS); self.P=np.zeros((2,n,5,samples,2)); self.J=np.full((2,n,5,samples,2),n+1,dtype=np.int32)
        rng=random.Random(1201)
        for i,k in enumerate(KEYS):
            for s in range(samples):
                o,d=representative(k,rng)
                for side in (0,1):
                    for a in range(5 if side==0 else 4):
                        for b,(p,j) in enumerate(outcomes(o,d,side,a)):
                            self.P[side,i,a,s,b]=p; self.J[side,i,a,s,b]=n if j==-1 else n+1 if j==-2 else j
        build_seconds=time.monotonic()-start; solve_start=time.monotonic(); self.V=np.zeros((31,2,n+2)); self.V[:,:,n]=1
        self.policy=np.zeros((31,2,n),dtype=np.int8)
        for t in range(1,31):
            for side in (0,1):
                q=self.q_all(t,side)
                self.policy[t,side]=q.argmax(1) if side==0 else q.argmin(1)
                self.V[t,side,:n]=q.max(1) if side==0 else q.min(1)
        # Finite-horizon support attractors; no floating-point equality required.
        positive=np.zeros((31,2,n+2),bool); sure=positive.copy(); positive[:,:,n]=True; sure[:,:,n]=True
        for t in range(1,31):
            for side in (0,1):
                support=self.P[side]>0; ids=self.J[side]
                pos=(positive[t-1,1-side][ids]&support).any((2,3))
                certain=(sure[t-1,1-side][ids]|~support).all((2,3))
                count=5 if side==0 else 4
                positive[t,side,:n]=pos[:,:count].any(1) if side==0 else pos[:,:count].all(1)
                sure[t,side,:n]=certain[:,:count].any(1) if side==0 else certain[:,:count].all(1)
        self.info={'states_per_side':n,'states':2*n+2,'samples_per_state':samples,'build_seconds':build_seconds,'solve_seconds':time.monotonic()-solve_start,'seconds':time.monotonic()-start,'horizon':30,'positive_30':positive[30,:,:n].sum(axis=1).tolist(),'almost_sure_30':sure[30,:,:n].sum(axis=1).tolist(),'convergence':'exact 30 finite-horizon Bellman backups'}
        (OUT/'solver.json').write_text(json.dumps(self.info,indent=2)); print(self.info,flush=True)
    def q_all(self,t,side):
        q=(self.P[side]*self.V[t-1,1-side][self.J[side]]).sum(3).mean(2)
        if side:q[:,4]=np.inf
        return q
    def qs(self,o,d,side,t):
        i=INDEX[key(o,d)]
        q=(self.P[side,i]*self.V[t-1,1-side][self.J[side,i]]).sum(2).mean(1)
        if side:q[4]=np.inf
        return q

DIRECTION_NAMES=['SW','W','NW','S','stay','N','SE','E','NE']
MODEL_IDS=set()

def llm(o,d,side,t,model):
    labels=['B','C'] if side==0 else ['D1','D2','D3']
    players=o[1:] if side==0 else d
    options={}
    for j,(label,p) in enumerate(zip(labels,players)):
        opts=[]
        for direction,delta in zip(DIRECTION_NAMES,DELTAS):
            q=move(p,delta)
            if q in (d+[o[0]] if side==0 else o):continue
            item={'direction':direction,'position':q}
            if side==0:
                proposed=[v[:] for v in o];proposed[j+1]=q
                item['p_catch_if_thrown_here']=round(catch(proposed,d,j+1),4)
            opts.append(item)
        options[label]=opts
    field={'A_holder':o[0],'B':o[1],'C':o[2],**{f'D{j+1}':q for j,q in enumerate(d)}}
    proximity={label:{f'D{j+1}':round(math.dist(p,q),2) for j,q in enumerate(d)} for label,p in zip(['A','B','C'],o)}
    schema={'move_B':'N','move_C':'NE','action':'hold'} if side==0 else {'move_D1':'N','move_D2':'stay','move_D3':'SW'}
    prompt=json.dumps({'task':'Ultimate: maximize probability of an endzone catch as offense; minimize it as defense. Return only JSON with named fields, following the example schema.',
        'rules':'Field x=0..9, y=0..19. N increases y. Endzone y>=17. A holds disc and cannot move. Move receivers first, then hold or throw_B or throw_C. HOLD IS SAFE: receivers move without risking possession. A dropped throw immediately LOSES. Repeated sideways/backward throws multiply turnover risk; optimize scoring, not completion count. Defense moves all defenders. No two players may occupy one square; choose jointly compatible moves. Turns alternate and each side move consumes one remaining turn. A catch only wins if in the endzone.',
        'side':'offense' if side==0 else 'defense','turns_left':t,'field':field,'distances_to_defenders':proximity,
        'throw_distances':{label:round(math.dist(o[0],o[j]),2) for label,j in [('B',1),('C',2)]},
        'current_p_catch':{label:round(catch(o,d,j),4) for label,j in [('B',1),('C',2)]},
        'move_options':options,'answer_example':schema})
    digest=hashlib.sha256((model+prompt).encode()).hexdigest();cache=OUT/'cache';cache.mkdir(exist_ok=True);f=cache/(digest+'.json')
    if f.exists():
        saved=json.loads(f.read_text());MODEL_IDS.update(saved.get('models',[]));return saved['id']
    for attempt in range(2):
        proc=subprocess.run(['claude','-p','--model',model,'--output-format','json',prompt+(' Previous answer invalid. Choose legal named moves and return JSON only.' if attempt else '')],capture_output=True,text=True,timeout=120)
        if 'Not logged in' in proc.stdout+proc.stderr:raise RuntimeError('Claude CLI not authenticated: run claude /login')
        try:
            envelope=json.loads(proc.stdout)
            if 'modelUsage' in envelope:MODEL_IDS.update(envelope['modelUsage'])
            if isinstance(envelope.get('model'),str):MODEL_IDS.add(envelope['model'])
            answer=envelope.get('result',envelope)
            if isinstance(answer,str):answer=json.loads(re.search(r'\{[^{}]*\}',answer).group())
            digits=[];positions=[]
            for label,p in zip(labels,players):
                direction=answer['move_'+label];digit=DIRECTION_NAMES.index(direction)
                assert direction in [v['direction'] for v in options[label]]
                digits.append(digit);positions.append(move(p,DELTAS[digit]))
            assert unique([o[0]]+positions,d) if side==0 else unique(o,positions)
            code=0
            for digit in digits:code=code*9+digit
            a=code*3+['hold','throw_B','throw_C'].index(answer['action']) if side==0 else code
            f.write_text(json.dumps({'id':a,'models':sorted(MODEL_IDS)}));return a
        except (ValueError,AttributeError,KeyError,AssertionError,TypeError):pass
    return 120 if side==0 else 364

def choose(name,o,d,side,t,solver,model):
    qs=solver.qs(o,d,side,t)
    if name=='Calculator':
        # Concrete one-step refinement of the abstract value, over the same macros.
        values=[sum(p*(1. if j==-1 else 0. if j==-2 else solver.V[t-1,1-side,j]) for p,j in outcomes(o,d,side,a)) for a in range(5 if side==0 else 4)]
        a=(max(range(5),key=lambda a:(values[a],sum(p[1] for p in action(o,d,side,a)[0][1:]))) if side==0 else int(np.argmin(values))); x,y,r=action(o,d,side,a)
    elif name=='Scripted':
        a=1
        if side==0:
            x,y,_=action(o,d,side,1); targets=[r for r in (1,2) if x[r][1]>x[0][1]]
            r=max(targets,key=lambda r:catch(x,y,r)) if targets else 0
            a=r+2 if r and catch(x,y,r)>=.65 else 1
        x,y,r=action(o,d,side,a)
    else:
        a=llm(o,d,side,t,model); r=a%3 if side==0 else 0; code=a//3 if side==0 else a; digits=[]
        for _ in range(2 if side==0 else 3):digits.insert(0,code%9); code//=9
        x=[list(p) for p in o]; y=[list(p) for p in d]
        for j,v in enumerate(digits):
            if side==0:x[j+1]=move(o[j+1],DELTAS[v])
            else:y[j]=move(d[j],DELTAS[v])
    x,y=resolve(x,y,side,o,d)
    p=catch(x,y,r) if r else 1.; z=[p,-2]
    if r and x[r][1]>=17:value=p
    else:
        nxt=[p[:] for p in x]
        if r:nxt[0],nxt[r]=nxt[r],nxt[0]
        value=p*solver.V[t-1,1-side,INDEX[key(nxt,y)]]
    opt=float(max(qs) if side==0 else min(qs)); regret=max(0.,opt-value if side==0 else value-opt)
    return x,y,r,p,regret

def game(off,deff,seed,solver,model):
    rng=random.Random(seed); o,d=start_positions(seed)
    pred=float(solver.V[30,0,INDEX[key(o,d)]]); history=[]; outcome='timeout'; regrets=[]
    for turn in range(30):
        side=turn%2; x,y,r,p,regret=choose(off if side==0 else deff,o,d,side,30-turn,solver,model)
        alternatives=solver.qs(o,d,side,30-turn).tolist()[:5 if side==0 else 4]
        record={'abstract_alternatives':alternatives,'abstract_state':list(key(o,d)),'o':[v[:] for v in x],'d':[v[:] for v in y],'thrower':o[0],'receiver':x[r] if r else None,'p':p,'turn':turn+1,'side':side,'regret':regret}; history.append(record); regrets.append(regret)
        o,d=x,y
        if r:
            if rng.random()>p:history[-1]['throw_result']='dropped';outcome='turnover'; break
            history[-1]['throw_result']='caught'
            if o[r][1]>=17:outcome='score'; break
            o[0],o[r]=o[r],o[0]
    return {'offense':off,'defense':deff,'seed':seed,'outcome':outcome,'turns':len(history),'predicted':pred,'mistake_rate':float(np.mean(np.array(regrets)>.02)),'mean_regret':float(np.mean(regrets)),'history':history}

def wilson(k,n):
    z=1.96; mid=(k/n+z*z/(2*n))/(1+z*z/n); half=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n);return [mid-half,mid+half]
def summarize(games):
    rows=[]
    for off,deff in sorted(set((g['offense'],g['defense']) for g in games)):
        gs=[g for g in games if (g['offense'],g['defense'])==(off,deff)]; n=len(gs); wins=sum(g['outcome']=='score' for g in gs); turnovers=sum(g['outcome']=='turnover' for g in gs)
        score_turns=[g['turns'] for g in gs if g['outcome']=='score']; turn_ci=np.quantile(np.random.default_rng(12).choice(score_turns,(2000,len(score_turns)),replace=True).mean(1),[.025,.975]).tolist() if score_turns else None
        rates=[g['mistake_rate'] for g in gs]; boot=np.random.default_rng(11).choice(rates,(2000,n),replace=True).mean(1)
        rows.append(dict(offense=off,defense=deff,n=n,win_rate=wins/n,win_ci=wilson(wins,n),turnover_rate=turnovers/n,turnover_ci=wilson(turnovers,n),turns_to_score=float(np.mean([g['turns'] for g in gs if g['outcome']=='score'])) if wins else None,turns_to_score_ci=turn_ci,abstraction_gap_ci=[float(np.mean([g['predicted'] for g in gs]))-v for v in reversed(wilson(wins,n))],mistake_rate=float(np.mean(rates)),mistake_ci=np.quantile(boot,[.025,.975]).tolist(),abstraction_gap=float(np.mean([g['predicted'] for g in gs]))-wins/n))
    return rows

def render(games,rows):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    plt.rcParams.update({'font.family':'serif','font.size':11,'savefig.dpi':220})
    names=sorted(set(g['offense'] for g in games))
    for metric in ('win_rate','turnover_rate','mistake_rate','abstraction_gap'):
        a=np.array([[next(r[metric] for r in rows if r['offense']==o and r['defense']==d) for d in names] for o in names]); fig,ax=plt.subplots(figsize=(5,4)); im=ax.imshow(a,vmin=-1 if metric=='abstraction_gap' else 0,vmax=1,cmap='coolwarm' if metric=='abstraction_gap' else 'viridis'); ax.set(xticks=range(len(names)),yticks=range(len(names)),xticklabels=names,yticklabels=names,xlabel='Defense coach',ylabel='Offense coach',title=metric.replace('_',' ').title()); fig.colorbar(im,ax=ax)
        for i,j in itertools.product(range(len(names)),repeat=2):ax.text(j,i,f'{a[i,j]:.2f}',ha='center',va='center',color='white' if abs(a[i,j])<.5 else 'black')
        fig.tight_layout()
        for ext in ('png','pdf'):fig.savefig(OUT/f'{metric}.{ext}')
        plt.close(fig)
    for name in names:
        g=next(g for g in games if g['offense']==name); fig,ax=plt.subplots(figsize=(5,8))
        def frame(i):
            ax.clear(); h=g['history'][min(i,len(g['history'])-1)]; ax.set(xlim=(-.5,9.5),ylim=(-.5,19.5),aspect='equal'); ax.axhspan(16.5,19.5,color='lightgreen'); ax.scatter(*zip(*h['o']),s=150,c='royalblue',marker='o',edgecolor='navy',label=g['offense']+' offense');ax.scatter(*zip(*h['d']),s=150,c='tomato',marker='x',linewidths=2,label=g['defense']+' defense');ax.scatter(*h['thrower'],s=45,c='gold',edgecolor='black',zorder=5)
            if h['receiver']:
                ax.annotate('',xy=h['receiver'],xytext=h['thrower'],arrowprops={'arrowstyle':'->','connectionstyle':'arc3,rad=.2','color':'black'}); ax.text(.02,.02,f"p(catch)={h['p']:.3f} · {h.get('throw_result','')}",transform=ax.transAxes)
            ax.set_title(f"{g['offense']} offense vs {g['defense']} defense\nTurn {h['turn']} · {g['outcome'] if i>=len(g['history'])-1 else 'playing'}");ax.legend(loc='upper left');ax.set_xticks(range(10));ax.set_yticks(range(20));ax.grid(alpha=.2)
        anim=FuncAnimation(fig,frame,frames=len(g['history'])+4,interval=650);anim.save(OUT/f'demo_{name}.mp4',writer='ffmpeg',fps=2);frame(next((i for i,h in enumerate(g['history']) if h['receiver']),0));fig.savefig(OUT/f'demo_{name}_frame.png');plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=3);p.add_argument('--model',default='haiku');p.add_argument('--no-llm',action='store_true');p.add_argument('--samples',type=int,default=30);p.add_argument('--start-depth',type=int,choices=range(0,15),default=12);p.add_argument('--out',type=Path,default=Path('outputs_dev'));args=p.parse_args()
    global OUT, START_DEPTH
    START_DEPTH=args.start_depth
    OUT=args.out;OUT.mkdir(parents=True,exist_ok=True)
    if not args.no_llm:
        test=subprocess.run(['claude','-p','--model',args.model,'Return only {"ok":true}'],text=True,capture_output=True,timeout=120)
        if test.returncode:raise SystemExit('LLM preflight failed: '+test.stdout+test.stderr)
    start=time.monotonic();solver=Solver(args.samples);names=['Calculator','Scripted']+([] if args.no_llm else ['LLM']);jobs=list(itertools.product(names,names,range(args.n)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:games=list(pool.map(lambda j:game(j[0],j[1],1700+j[2],solver,args.model),jobs))
    (OUT/'games.json').write_text(json.dumps(games,indent=2));rows=summarize(games);(OUT/'summary.json').write_text(json.dumps(rows,indent=2))
    with (OUT/'games.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=[k for k in games[0] if k!='history']);w.writeheader();w.writerows({k:v for k,v in g.items() if k!='history'} for g in games)
    print(json.dumps(rows,indent=2),flush=True); print('Offense | Defense | N | Win | Win 95% CI | Turnover | Turnover 95% CI | Mistake | Gap',flush=True)
    for row in rows: print(' | '.join(str(row[k]) for k in ('offense','defense','n','win_rate','win_ci','turnover_rate','turnover_ci','mistake_rate','abstraction_gap')),flush=True)
    render(games,rows);(OUT/'run.json').write_text(json.dumps({'model':args.model,'llm_enabled':not args.no_llm,'n':args.n,'start_depth':START_DEPTH,'reported_model_ids':sorted(MODEL_IDS),'wall_seconds':time.monotonic()-start},indent=2))
if __name__=='__main__':main()
