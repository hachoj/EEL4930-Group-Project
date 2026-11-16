"""Force-flick geometry. Multiplier is a design assumption."""
import numpy as np
BREAK_MULTIPLIER=1.0
def is_break(a,b):
    v=np.asarray(b)-np.asarray(a)
    return (v[...,0]<0)&(-v[...,0]>np.sin(np.deg2rad(15))*np.linalg.norm(v,axis=-1))
def seal_batch(o,d,marks):
    d=d.copy(); marker=np.argmax(marks==0,axis=1)
    grid=np.array([(x,y) for x in range(10) for y in range(20)])
    codes=o[:,0,0]*20+o[:,0,1]
    order_rows=np.argsort(codes)
    groups=np.split(order_rows,np.where(np.diff(codes[order_rows]))[0]+1)
    for pending in groups:
        if not len(pending):continue
        holder=o[pending[0],0];target=holder+[-1,0]
        order=np.lexsort((grid[:,1],grid[:,0],((grid-holder)**2).sum(1),((grid-target)**2).sum(1)))
        for q in grid[order]:
            hit=(d[pending]==q).all(-1);hit[np.arange(len(pending)),marker[pending]]=False
            legal=~((o[pending]==q).all(-1).any(1)|hit.any(1))
            chosen=pending[legal];d[chosen,marker[chosen]]=q;pending=pending[~legal]
            if not len(pending):break
    return d
def seal(o,d,marks):return seal_batch(np.array(o)[None],np.array(d)[None],np.array(marks)[None])[0].tolist()
