"""Full-game media from saved v7 histories. No coach calls or solver mutation."""
import argparse, collections, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

# This block replaces only the video presentation; statistics above are retained.
def absolute_records(g):
    """Stable team/player identities in one fixed, two-endzone stadium.

    Engine frames are post-action, before catch canonicalization / transfer.
    Rotate on turnovers; after scores the receiver attacks the scorer's
    previous direction (teams switch ends). Carry identities through holder
    swaps. Pickups may teleport the nearest defender to a dropped disc; seal
    and collision displacement are engine exceptions, not camera movements.
    """
    result=[]; ids=[[0,1,2],[0,1,2]]; rotated=False; previous=None
    for h,_ in records(g):
        t=h['team']
        if previous:
            pt=previous['team']
            if t!=pt:
                if previous.get('throw_result') in ('drop','interception'):
                    rotated=not rotated
                    spot=previous['turnover_spot']
                    pick=min(range(3),key=lambda k:np.linalg.norm(np.array(previous['d'][k])-spot))
                    ids[t][0],ids[t][pick]=ids[t][pick],ids[t][0]
                else:ids=[[0,1,2],[0,1,2]]
            elif previous.get('throw_result')=='caught':
                r=previous['o'].index(previous['receiver'])
                ids[t][0],ids[t][r]=ids[t][r],ids[t][0]
        def point(p):return [9-p[0],19-p[1]] if rotated else list(p)
        row=dict(h);row['players']={}
        for team,key in ((t,'o'),(1-t,'d')):
            for k,p in enumerate(h[key]):row['players'][(team,ids[team][k])]=point(p)
        row['absolute_o']=[point(p) for p in h['o']];row['absolute_d']=[point(p) for p in h['d']]
        for key in ('thrower','receiver','turnover_spot'):
            if h.get(key) is not None:row[key]=point(h[key])
        row['direction']=-1 if rotated else 1
        row['point']=1+sum(p['outcome']=='score' and p['end_turn']<h['turn'] for p in g['possessions'])
        row['goal']=h.get('throw_result')=='caught' and h['receiver'][1]>=17
        result.append(row);previous=h
    return result


def broadcast_schedule(rows,highlights):
    """All scoring/turnover finishes, all pulls; routine play elided in highlights."""
    schedule=[('title',None,None,60)]
    ends=[i for i,h in enumerate(rows) if h['goal'] or h.get('throw_result') in ('drop','interception')]
    if highlights is None:selected=set(range(len(rows)))
    else:
        # N is the maximum approach window, not an exclusion of long possessions.
        selected=set()
        for i in ends:
            start=max(0,i-min(highlights,4)+1)
            selected.update(range(start,i+1))
    pulls=1+sum(h['goal'] for h in rows[:-1])
    # Budget replays + pulls first, then distribute the remaining frames.
    replay_count=sum(h['goal'] or h.get('throw_result')=='interception' for h in rows)
    fixed=120+pulls*24+replay_count*18
    steps=12 if highlights is None else max(2,min(10,(2580-fixed)//max(1,len(selected))))
    if highlights is not None and fixed+len(selected)*steps>2670:
        selected=set(ends);steps=max(1,(2670-fixed)//len(selected))
    for i,h in enumerate(rows):
        prev=rows[i-1] if i else None
        if i==0 or prev['goal']:schedule.append(('pull',h,prev,24 if highlights is not None else 45))
        if i not in selected:continue
        schedule.append(('play',h,prev,steps))
        if h['goal'] or h.get('throw_result')=='interception':schedule.append(('replay',h,prev,18 if highlights is not None else 42))
    schedule.append(('final',rows[-1],None,60));return schedule


def video(g,out,n):
    """Render broadcast frames with Pillow and stream directly to H.264."""
    from PIL import Image, ImageDraw, ImageFont
    import subprocess, math
    rows=absolute_records(g);schedule=broadcast_schedule(rows,n)
    W,H=1920,1080;bg='#0b1927';white='#f2f6fa';gold='#ffe17d'
    font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
    if not Path(font_path).exists():font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    fonts={size:ImageFont.truetype(font_path,size) for size in (20,24,28,32,36,46,56,80)}
    def xy(p):return (160+(p[1]+.5)*80,900-(p[0]+.5)*64)
    def text(d,pos,s,size=28,fill=white,anchor='mm'):d.text(pos,s,font=fonts[size],fill=fill,anchor=anchor)
    base=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(base)
    for y in range(20):d.rectangle((160+y*80,260,240+y*80,900),fill=('#246146' if y%2 else '#28694c'))
    for lo,hi in ((160,400),(1520,1760)):
        d.rectangle((lo,260,hi,900),fill='#1b493e');text(d,((lo+hi)/2,570),'ENDZONE',28,fill='#719689')
    d.rectangle((160,260,1760,900),outline=white,width=3)
    for x in (400,1520):d.line((x,260,x,900),fill=white,width=3)
    for x in range(480,1520,80):d.line((x,263,x,278),fill='#afc4b9',width=2);d.line((x,882,x,897),fill='#afc4b9',width=2)
    text(d,(960,1000),'ULTIMATE  /  FULL GAME BROADCAST',24,fill='#829bac')
    snapshots={};frame_index=0
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    def arc(a,b,t):
        a=np.array(xy(a));b=np.array(xy(b));v=b-a
        control=(a+b)/2+np.array([v[1],-v[0]])*.20
        return (1-t)**2*a+2*(1-t)*t*control+t*t*b
    try:
        for kind,h,prev,count in schedule:
            for k in range(count):
                t=(k+1)/count;s=t*t*(3-2*t);im=base.copy();d=ImageDraw.Draw(im)
                if kind in ('title','final'):
                    d.rectangle((0,0,W,H),fill=bg)
                    text(d,(960,230),'ULTIMATE',80);text(d,(960,335),'FULL GAME BROADCAST',32,fill=gold)
                    for team,x in ((0,570),(1,1350)):
                        d.rounded_rectangle((x-290,425,x+290,630),radius=22,fill=COLORS[team]);text(d,(x,485),g['teams'][team],46)
                        text(d,(x,570),str(g['score'][team]) if kind=='final' else ('BLUE' if team==0 else 'RED'),56 if kind=='final' else 28)
                    text(d,(960,525),'VS',36)
                    text(d,(960,720),'FINAL SCORE' if kind=='final' else f"Game to {max(g['score'])}",46)
                    if kind=='title':
                        text(d,(960,830),'Lettered jerseys = players    •    White disc + trail = possession',28)
                        text(d,(960,880),'Dashed lines = marks    •    Gold ring = force seal',28)
                        text(d,(960,930),'POACH / DOUBLE / SWITCH = reconstructed defensive plays',24,fill='#a9bdc9')
                else:
                    active=h['team'];direction=h['direction'];is_turn=h.get('throw_result') in ('drop','interception')
                    # Score bug and permanent camera; only the attack arrow reverses.
                    for team,x in ((0,160),(1,1000)):
                        d.rounded_rectangle((x,60,x+760,155),radius=12,fill=COLORS[team]);text(d,(x+290,106),g['teams'][team],36);text(d,(x+670,106),str(h['score'][team]),56)
                    receiving=1-active if is_turn and kind=='play' and t>.75 else active
                    attack=-direction if receiving!=active else direction
                    text(d,(960,205),f"POINT {h['point']}    |    {g['teams'][receiving]} BALL   {'→' if attack>0 else '←'}",32)
                    players=h['players']
                    if kind=='pull':
                        # New receiving offense attacks direction; pull travels from opposite goal line.
                        players={}
                        for team in (0,1):
                            end=(2 if direction>0 else 17) if team==active else (17 if direction>0 else 2)
                            for j in range(3):players[(team,j)]=[2+j*2.5,end]
                    elif prev and not prev['goal']:
                        players={key:(np.array(prev['players'][key])*(1-s)+np.array(p)*s) for key,p in players.items()}
                    if kind!='pull':
                        for j,m in enumerate(h['marks']):
                            a=xy(h['absolute_d'][j]);b=xy(h['absolute_o'][m]);v=np.array(b)-a
                            for z in np.arange(0,1,.10):d.line((tuple(np.array(a)+z*v),tuple(np.array(a)+min(z+.045,1)*v)),fill='#8aa99b',width=2)
                        a=xy(h['absolute_d'][h['marks'].index(0)]);d.ellipse((a[0]-28,a[1]-28,a[0]+28,a[1]+28),outline=gold,width=3)
                    for (team,j),p in players.items():
                        x,y=xy(p);d.ellipse((x-22,y-22,x+22,y+22),fill=COLORS[team],outline=white,width=3);text(d,(x,y),'ABC'[j],24)
                    if kind=='pull':
                        a=[4.5,17 if direction>0 else 2];b=[4.5,2 if direction>0 else 17];disc=arc(a,b,t)
                        text(d,(960,950),f"PULL  •  {g['teams'][1-active]} → {g['teams'][active]}",32,fill=gold)
                    else:
                        a=h['thrower'];b=h.get('receiver');disc=np.array(xy(a))
                        if b:
                            pts=[tuple(arc(a,b,z)) for z in np.linspace(0,1,35)];d.line(pts,fill='#d9bc64',width=3)
                            flight=min(1,t*1.2);landing=h.get('turnover_spot',b) if h.get('throw_result')=='interception' else b;disc=arc(a,landing,flight)
                            for lag in (.06,.12,.18):
                                p=arc(a,landing,max(0,flight-lag));r=max(2,6-lag*20);d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill='#bdc9bd')
                            text(d,(960,950),f"CATCH CHANCE {h['p']:.0%}   •   {h.get('throw_result','').upper()}",28)
                        for j,mode in enumerate(h['_modes']):
                            if mode.startswith(('poach','double')) or h['_switch']:
                                x,y=xy(h['absolute_d'][j]);label='SWITCH' if h['_switch'] else mode.split('_')[0].upper()
                                box=d.textbbox((0,0),label,font=fonts[20]);w=box[2]+16
                                d.rounded_rectangle((x-w/2,y-60,x+w/2,y-30),radius=5,fill=bg);text(d,(x,y-45),label,20)
                    x,y=disc;d.ellipse((x-9,y-5,x+9,y+5),fill=white,outline=gold,width=2)
                    banner=None
                    if kind=='replay':banner='GOAL' if h['goal'] else 'INTERCEPTED'
                    elif is_turn and t>.65:banner=f"TURNOVER  •  {g['teams'][1-active]} BALL  {'←' if direction>0 else '→'}"
                    elif h['goal'] and t>.65:banner='GOAL'
                    if banner:
                        d.rounded_rectangle((430,305,1490,375),radius=10,fill=bg);text(d,(960,340),banner,36,fill=gold)
                        if kind=='replay':text(d,(1680,238),'SLOW REPLAY',20,fill=gold)
                proc.stdin.write(im.tobytes())
                snap=kind if kind in ('title','pull','final') else 'goal_replay' if kind=='replay' and h['goal'] else 'turnover' if kind=='play' and is_turn and t>.8 else None
                if snap and snap not in snapshots and (kind not in ('pull','replay') or t>.5):
                    snapshots[snap]={'frame':frame_index,'seconds':frame_index/30}
                frame_index+=1
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('ffmpeg encoding failed')
    except BaseException:
        proc.kill();proc.wait();raise
    # These are actual decoded MP4 frames, not source drawings.
    for name,entry in snapshots.items():
        path=out.with_name(out.stem+'_'+name+'.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(entry['seconds']),'-i',str(out),'-frames:v','1',str(path)],check=True)
        entry['path']=str(path)
    info={'seconds':frame_index/30,'frames':frame_index,'resolution':'1920x1080','fps':30,'snapshots':snapshots}
    out.with_suffix('.json').write_text(json.dumps(info,indent=2));return info

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
