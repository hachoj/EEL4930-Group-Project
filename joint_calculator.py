"""Joint-intent sampled game. Sparse transition matrices retain every sampled outcome."""
import itertools, json, pickle, random, time
import numpy as np
import force
from scipy.sparse import csr_matrix

INTENTS=['stay','SW','W','NW','S','N','SE','E','NE','get_open']
DIRECTIONS=np.array([[0,0],[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]])
OFF_ACTIONS=list(itertools.product(range(10),range(10),range(3)))
DEF_ACTIONS=list(itertools.product(range(3),repeat=3))

def zones(p):
    x,y=p[...,0],p[...,1]
    return np.where(x<3,0,np.where(x<7,1,2))+3*np.where(y<15,y//5,np.where(y<17,3,4))

def keys(o,d):
    z=zones(o);r=o[:,1:];v=d[:,None]-r[:,:,None]
    ds=(v*v).sum(-1);nearest=ds.argmin(-1)
    b=np.take_along_axis(v,nearest[:,:,None,None],axis=2)[:,:,0]
    labels=np.where(ds.min(-1)>=9,2,np.where(((o[:,0,None]-r)*b).sum(-1)>=0,0,1))
    return ((((z[:,0]*15+z[:,1])*15+z[:,2])*3+labels[:,0])*3+labels[:,1]).astype(np.int32)

def resolve_batch(o,d,side,proposed):
    old=o if side==0 else d;other=d if side==0 else o;x=proposed.copy()
    for j in range(3):
        obstacles=np.concatenate((other,x[:,:j],old[:,j+1:]),axis=1)
        hit=(x[:,j,None]==obstacles).all(-1).any(-1)
        x[hit,j]=old[hit,j]
    return (x,d) if side==0 else (o,x)

def proposals(o,d):
    """Best legal one-square realization of each receiver intent (before reservations)."""
    result=[]
    for j in (1,2):
        p=o[:,j];c=np.clip(p[:,None]+DIRECTIONS[None],(0,0),(9,19))
        occupied=np.concatenate((d,o[:,[0,3-j]]),axis=1)
        legal=~(c[:,:,None]==occupied[:,None]).all(-1).any(-1)
        moving=(c!=p[:,None]).any(-1)
        distance=np.sqrt(((c[:,:,None]-d[:,None])**2).sum(-1)).min(-1)
        choices=[]
        for intent in range(10):
            if intent==0:choices.append(p);continue
            if intent==9:score=distance+.15*(c[:,:,1]-p[:,None,1])
            else:
                delta=c-p[:,None];target=DIRECTIONS[intent]
                score=(delta*target).sum(-1)-.1*((delta-target)**2).sum(-1)
            # Non-stay intents always move when a vacant neighboring cell exists.
            score=np.where(legal&moving,score,-1e6)
            chosen=c[np.arange(len(o)),score.argmax(-1)]
            chosen=np.where((legal&moving).any(-1)[:,None],chosen,p)
            choices.append(chosen)
        result.append(choices)
    return result

def defense_proposals(o,d,marks):
    result=[]
    for j in range(3):
        mark=o[np.arange(len(o)),marks[:,j]]
        options=[]
        for mode in range(3):
            # Tight front toward thrower (holder is marked from downfield), behind,
            # or trail one square on the marker's current side of its mark.
            vector=np.sign(o[:,0]-mark).astype(int)
            holder=marks[:,j]==0;vector[holder]=[0,1]
            if mode==1:vector=-vector
            if mode==2:
                vector=np.sign(d[:,j]-mark).astype(int)
            target=np.clip(mark+vector,(0,0),(9,19))
            candidates=np.clip(d[:,j,None]+DIRECTIONS[None],(0,0),(9,19))
            obstacles=np.concatenate((o,np.delete(d,j,axis=1)),axis=1)
            legal=~(candidates[:,:,None]==obstacles[:,None]).all(-1).any(-1)
            moving=(candidates!=d[:,j,None]).any(-1)
            score=-((candidates-target[:,None])**2).sum(-1).astype(float)
            score=np.where(legal&moving,score,-1e6)
            picked=candidates[np.arange(len(o)),score.argmax(-1)]
            picked=np.where((legal&moving).any(-1)[:,None],picked,d[:,j])
            options.append(picked)
        result.append(options)
    return result

def realize(o,d,side,a,props):
    x=(o if side==0 else d).copy()
    intents=OFF_ACTIONS[a] if side==0 else DEF_ACTIONS[a]
    for j in range(2 if side==0 else 3):x[:,j+1 if side==0 else j]=props[j][intents[j]]
    x,y=resolve_batch(o,d,side,x)
    return x,y,intents[2] if side==0 else 0

def transitions(o,d,r,n,marks=None):
    if not r:return keys(o,d),np.ones(len(o))
    a=o[:,0]-o[:,r];dist=np.sqrt((a*a).sum(-1));b=d-o[:,r,None];norm=np.sqrt((b*b).sum(-1))
    denom=dist[:,None]*norm;cos=np.divide((a[:,None]*b).sum(-1),denom,out=np.ones_like(denom),where=denom!=0)
    p=1/(1+np.exp(-(4.15701518-.06417449*dist*5)))*np.prod(1-.6*np.maximum(0,1-norm/3)*(.25+.75*(1+cos)/2),axis=1)
    p*=np.where(force.is_break(o[:,0],o[:,r]),force.BREAK_MULTIPLIER,1.)
    if marks is None:
        perms=np.array(list(itertools.permutations(range(3))))
        costs=np.stack([np.linalg.norm(d-o[:,perm],axis=2).sum(1) for perm in perms],axis=1)
        marks=perms[costs.argmin(1)]
    x=o.copy();x[:,[0,r]]=x[:,[r,0]]
    remapped=np.where(marks==0,r,np.where(marks==r,0,marks))
    d=force.seal_batch(x,d,remapped)
    ids=keys(x,d);ids[o[:,r,1]>=17]=n
    return ids,p

class Solver:
    def __init__(self,samples=30,out=None):
        import ultimate as u
        start=time.monotonic();n=len(u.KEYS);rng=random.Random(1201)
        reps=[u.representative(k,rng) for k in u.KEYS for _ in range(samples)]
        o=np.array([v[0] for v in reps],dtype=np.int16);d=np.array([v[1] for v in reps],dtype=np.int16)
        del reps
        # Fixed mark identity is absent from the abstraction; sample nearest bijections.
        perms=np.array(list(itertools.permutations(range(3))))
        costs=np.stack([np.linalg.norm(d-o[:,p],axis=2).sum(1) for p in perms],axis=1)
        marks=perms[costs.argmin(1)];row=np.repeat(np.arange(n),samples)
        self.matrices=[[],[]]
        print('Representative sampling seconds',time.monotonic()-start,flush=True)
        for side in (0,1):
            props=proposals(o,d) if side==0 else defense_proposals(o,d,marks)
            for a in range(300 if side==0 else 27):
                x,y,r=realize(o,d,side,a,props);ids,p=transitions(x,y,r,n,marks)
                if r:
                    mat=csr_matrix((np.concatenate((p,1-p))/samples,(np.tile(row,2),np.concatenate((ids,np.full(len(ids),n+1))))),shape=(n,n+2))
                else:mat=csr_matrix((p/samples,(row,ids)),shape=(n,n+2))
                mat.eliminate_zeros();self.matrices[side].append(mat)
                if a%30==0:print('Built side/action',side,a,'seconds',time.monotonic()-start,flush=True)
        build=time.monotonic()-start;solve=time.monotonic()
        self.V=np.zeros((31,2,n+2));self.V[:,:,n]=1
        self.policy=np.zeros((31,2,n),dtype=np.int16)
        positive=np.zeros_like(self.V,dtype=bool);sure=positive.copy();positive[:,:,n]=True;sure[:,:,n]=True
        for t in range(1,31):
            for side in (0,1):
                q=self.q_all(t,side);self.policy[t,side]=q.argmax(1) if side==0 else q.argmin(1)
                self.V[t,side,:n]=q.max(1) if side==0 else q.min(1)
                pos=[];certain=[]
                for mat in self.matrices[side]:
                    # Positive weights: any successor positive / all successors sure.
                    pos.append(mat@positive[t-1,1-side].astype(float)>0)
                    certain.append(mat@(~sure[t-1,1-side]).astype(float)==0)
                positive[t,side,:n]=np.any(pos,axis=0) if side==0 else np.all(pos,axis=0)
                sure[t,side,:n]=np.any(certain,axis=0) if side==0 else np.all(certain,axis=0)
        self.info=dict(states=2*n+2,states_per_side=n,actions_offense=300,actions_defense=27,samples_per_state=samples,build_seconds=build,solve_seconds=time.monotonic()-solve,horizon=30,positive_30=positive[30,:,:n].sum(1).tolist(),almost_sure_30=sure[30,:,:n].sum(1).tolist(),convergence='exact 30 finite-horizon Bellman backups of sampled joint-intent game')
        out=u.OUT if out is None else out
        (out/'solver.json').write_text(json.dumps(self.info,indent=2));print(self.info,flush=True)
        with (out/'solver.pkl').open('wb') as f:pickle.dump(self,f)
    def q_all(self,t,side):return np.stack([m@self.V[t-1,1-side] for m in self.matrices[side]],axis=1)
    def qs(self,o,d,side,t):
        import ultimate as u
        i=u.INDEX[u.key(o,d)]
        return np.array([m[i]@self.V[t-1,1-side] for m in self.matrices[side]]).reshape(-1)
    def concrete(self,o,d,side,t,marks):
        oo=np.array(o)[None];dd=np.array(d)[None]
        props=proposals(oo,dd) if side==0 else defense_proposals(oo,dd,np.array(marks)[None])
        intents=np.array(OFF_ACTIONS if side==0 else DEF_ACTIONS)
        count=len(intents);oo=np.repeat(oo,count,axis=0);dd=np.repeat(dd,count,axis=0)
        proposed=(oo if side==0 else dd).copy()
        for j in range(2 if side==0 else 3):
            proposed[:,j+1 if side==0 else j]=np.array(props[j])[:,0][intents[:,j]]
        x,y=resolve_batch(oo,dd,side,proposed)
        receivers=intents[:,2] if side==0 else np.zeros(count,dtype=int)
        values=np.zeros(count)
        for r in range(3 if side==0 else 1):
            mask=receivers==r
            ids,p=transitions(x[mask],y[mask],r,len(self.V[0,0])-2,np.repeat(np.array(marks)[None],mask.sum(),axis=0))
            values[mask]=p*self.V[t-1,1-side,ids]
        candidates=[(xx.tolist(),yy.tolist(),int(r)) for xx,yy,r in zip(x,y,receivers)]
        if side==0:
            # Exact value first; progress and movement only break true ties.
            a=max(range(len(values)),key=lambda a:(values[a],sum(p[1] for p in candidates[a][0][1:]),sum(p!=q for p,q in zip(o,candidates[a][0]))))
        else:a=int(np.argmin(values))
        return candidates[a]
