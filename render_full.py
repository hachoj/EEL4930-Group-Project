"""Full-game media from saved v7 histories. No coach calls or solver mutation."""
import argparse, collections, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import replay

COLORS=['#247de0','#e45a43']

def recover(h,prev):
    """Recover deterministic baseline actions; LLM intentions are unavailable.

    Calculator selects the first minimum. Identical positions and marks have
    identical value, so the first matching action recovers its tie break.
    """
    import full_game as f
    import joint_calculator as j
    import ultimate as u
    o=[p[:] for p in prev['o']];d=[p[:] for p in prev['d']];marks=prev['marks'][:]
    if prev.get('throw_result')=='caught':
        r=o.index(prev['receiver']);o[0],o[r]=o[r],o[0];marks=[r if z==0 else 0 if z==r else z for z in marks];d=u.force.seal(o,d,marks)
    if h['coach']=='Scripted':
        modes=[]
        for m in h['marks']:
            if m==0 and min(np.linalg.norm(np.array(o[0])-p) for p in o[1:])<4:mode=5+int(np.linalg.norm(np.array(o[0])-o[2])<np.linalg.norm(np.array(o[0])-o[1]))
            elif np.linalg.norm(np.array(o[m])-o[0])>7:mode=4 if o[m][1]>=14 else 3
            else:mode=0
            modes.append(f.MODES[mode])
        return modes,marks!=h['marks']
    if h['coach']!='Calculator':return ['unknown']*3,marks!=h['marks']
    n=len(f.DEF_ACTIONS);oo=np.repeat(np.array(o)[None],n,0);dd=np.repeat(np.array(d)[None],n,0);proposed=dd.copy();mm=np.repeat(np.array(marks)[None],n,0)
    for pair in [None,(0,1),(0,2),(1,2)]:
        ids=np.array([i for i,(p,m) in enumerate(f.DEF_ACTIONS) if p==pair]);m=np.array([f.DEF_ACTIONS[i][1] for i in ids]);rem=f.remap_marks(np.array(marks)[None],pair);props=f.defense_props(np.array(o)[None],np.array(d)[None],rem);mm[ids]=rem
        for k in range(3):proposed[ids,k]=np.array(props[k])[:,0][m[:,k]]
    xx,yy=j.resolve_batch(oo,dd,1,proposed)
    matches=np.flatnonzero((yy==h['d']).all((1,2)) & (mm==h['marks']).all(1))
    if not len(matches):raise ValueError('Cannot reconstruct defense at turn '+str(h['turn']))
    pair,modes=f.DEF_ACTIONS[matches[0]]
    return [f.MODES[m] for m in modes],pair is not None

def records(g):
    prev=None
    for raw in g['history']:
        h=dict(raw);h['_switch']=False;h['_modes']=[]
        if h['side']==1:h['_modes'],h['_switch']=recover(h,prev)
        yield h,prev
        prev=h

def draw(ax,g,h,prev=None,alpha=1):
    # Reuse v1 artwork, then recolor jerseys to persistent team identities.
    comparable=prev if prev and prev['team']==h['team'] else None
    if comparable and comparable.get('throw_result')=='caught':
        comparable=dict(comparable);comparable['o']=[p[:] for p in comparable['o']];r=comparable['o'].index(comparable['receiver']);comparable['o'][0],comparable['o'][r]=comparable['o'][r],comparable['o'][0]
    replay.pitch(ax,h,{'offense':g['teams'][h['team']],'defense':g['teams'][1-h['team']]},comparable,alpha)
    # pitch's first two PathCollections are the two jersey teams; third is ring.
    from matplotlib.collections import PathCollection
    jerseys=[c for c in ax.collections if isinstance(c,PathCollection)]
    jerseys[0].set_facecolor(COLORS[h['team']]);jerseys[1].set_facecolor(COLORS[1-h['team']])
    for k,mode in enumerate(h['_modes']):
        if mode.startswith(('poach','double')) or h['_switch']:
            pos=h['d'][k];label='SWITCH' if h['_switch'] else mode.upper().replace('_',' ')
            ax.text(pos[1],pos[0]-.65,label,color='white',fontsize=7,ha='center',bbox=dict(facecolor='#142d26',alpha=.9),zorder=12)
    result=h.get('throw_result');score=result=='caught' and h['receiver'][1]>=17
    banner=f"TURNOVER — {g['teams'][1-h['team']]} ball" if result in ('drop','interception') else f"POINT — {g['teams'][h['team']]}" if score else None
    if result=='interception':ax.text(.5,.92,'INTERCEPTED',transform=ax.transAxes,color='#ffe569',weight='bold',ha='center',bbox=dict(facecolor='#142d26'),zorder=15)
    if banner:ax.text(.5,.02,banner,transform=ax.transAxes,color='white',weight='bold',fontsize=14,ha='center',bbox=dict(facecolor='#142d26',alpha=.95),zorder=15)
    possession=1+sum(p['end_turn']<h['turn'] for p in g['possessions'])
    ax.set_title(f"{g['teams'][0]} (BLUE) {h['score'][0]} : {h['score'][1]} {g['teams'][1]} (RED)\nPossession {possession} · Turn {h['turn']} · {g['teams'][h['team']]} attacks → (+y)\nCoordinates rotate 180° after possession changes; colors stay fixed",fontsize=11,pad=15)
    ax.text(.01,-.07,'Baseline tactics reconstructed from deterministic action tie breaks; LLM tactics unavailable.',transform=ax.transAxes,fontsize=8)

def video(g,out,n):
    rows=list(records(g))
    if n is not None:
        spans=[p for p in g['possessions'] if p['turns']<=n]
        rows=[(h,pr) for h,pr in rows if any(p['start_turn']<=h['turn']<=p['end_turn'] for p in spans)]
    if not rows:raise ValueError('No qualifying possessions')
    fps=12;steps=6 if n is None else max(1,min(6,int(84*fps/len(rows))))
    if n is not None and len(rows)>84*fps:raise ValueError('Lower highlight turn threshold for video under 90 seconds')
    fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=100);fig.set_facecolor('#e7eee7');fig.subplots_adjust(top=.78,bottom=.12,left=.04,right=.98)
    snapshots={};writer=FFMpegWriter(fps=fps,codec='libx264',extra_args=['-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1'])
    with writer.saving(fig,str(out),100):
        for h,prev in rows:
            for k in range(steps):draw(ax,g,h,prev,(k+1)/steps);writer.grab_frame()
            for kind,condition in [('turnover',h.get('throw_result') in ('drop','interception')),('tactics',any(m.startswith(('poach','double')) for m in h['_modes']))]:
                if condition and kind not in snapshots:
                    snapshots[kind]=(len(snapshots),h['turn']);fig.savefig(out.with_name(out.stem+'_'+kind+'.png'))
    plt.close(fig);return {'selected_turns':len(rows),'seconds':len(rows)*steps/fps,'snapshots':snapshots}

def figures(games,out):
    coaches=sorted({c for g in games for c in g['teams']});stats={c:collections.Counter() for c in coaches};matchups=collections.defaultdict(collections.Counter)
    for g in games:
        matchups[' vs '.join(g['teams'])][tuple(g['score'])]+=1
        for p in g['possessions']:stats[g['teams'][p['team']]].update({'possessions':1,p['outcome']:1})
        for h,_ in records(g):
            if h['side']==1:
                c=stats[g['teams'][1-h['team']]]
                for m in h['_modes']:c[m.split('_')[0]]+=1
                c['switch']+=int(h['_switch'])
    def save(fig,name):
        fig.tight_layout()
        for ext in ('png','pdf'):fig.savefig(out/(name+'.'+ext),dpi=170)
        plt.close(fig)
    fig,axs=plt.subplots(len(matchups),1,figsize=(11,3.4*len(matchups)),squeeze=False)
    for ax,(name,dist) in zip(axs[:,0],matchups.items()):
        keys=sorted(dist);ax.bar(range(len(keys)),[dist[k] for k in keys]);ax.set(xticks=range(len(keys)),xticklabels=[f'{a}–{b}' for a,b in keys],title=name,ylabel='Games',xlabel='Final score (team 0–team 1)')
    save(fig,'final_scores')
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(coaches,[stats[c]['score']/max(1,stats[c]['possessions']) for c in coaches]);ax.set(ylabel='Points per possession',ylim=(0,1),title='Pooled supplied games');save(fig,'points_per_possession')
    fig,ax=plt.subplots(figsize=(8,4));bottom=np.zeros(len(coaches))
    for key in ('drop','interception'):
        vals=np.array([stats[c][key] for c in coaches]);ax.bar(coaches,vals,bottom=bottom,label=key);bottom+=vals
    ax.set(ylabel='Offensive turnovers committed');ax.legend();save(fig,'turnovers')
    fig,ax=plt.subplots(figsize=(9,5));bottom=np.zeros(len(coaches))
    for key in ('tight','trail','poach','double','unknown'):
        vals=np.array([stats[c][key]/max(1,sum(stats[c][m] for m in ('tight','trail','poach','double','unknown'))) for c in coaches]);ax.bar(coaches,vals,bottom=bottom,label=key);bottom+=vals
    ax.set(ylabel='Share of defender observations',title='Reconstructed defensive positioning choices\nSwitch assignment changes: '+', '.join(f'{c} {stats[c]["switch"]}' for c in coaches));ax.legend();save(fig,'defensive_modes')
    (out/'figure_stats.json').write_text(json.dumps(stats,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('histories',nargs='+',type=Path);p.add_argument('--game-index',type=int,default=0);p.add_argument('--highlights',type=int,metavar='N');p.add_argument('--out',type=Path,default=Path('outputs_dev/v7/media'));p.add_argument('--figures',action='store_true');p.add_argument('--video',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    games=[g for path in a.histories for g in json.loads(path.read_text())]
    if a.figures:figures(games,a.out)
    if a.video or not a.figures:
        g=games[a.game_index];name='_vs_'.join(g['teams'])+f'_game{a.game_index}'+('_highlights' if a.highlights is not None else '')
        print(json.dumps(video(g,a.out/(name+'.mp4'),a.highlights),indent=2))
if __name__=='__main__':main()
