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
        if h['side']==1:
            if h.get('action_names',{}).get('modes'):
                h['_modes']=[h['action_names']['modes'][f'D{k+1}'] for k in range(3)];h['_switch']=bool(h['action_names'].get('switch'))
            else:h['_modes'],h['_switch']=recover(h,prev)
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
    pulls={p['start_turn']:p for p in g.get('pulls',[])}
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
        pull=pulls.get(h['turn'])
        setup=[]
        if pull:
            ids=[[0,1,2],[0,1,2]]
            for frame in pull['frames']:
                setup.append(dict(h,players={(team,k):point(p) for team,key in ((t,'o'),(1-t,'d')) for k,p in enumerate(frame[key])},absolute_o=[point(p) for p in frame['o']],absolute_d=[point(p) for p in frame['d']],phase=frame['phase'],landing=point(pull['landing']),thrower=point(pull['landing']),receiver=None,_modes=[],_switch=False,goal=False,direction=-1 if rotated else 1,point=len(result)+1))
            for frame in setup:
                frame.pop('throw_result',None);frame.pop('turnover_spot',None)
                frame['score']=previous['score'][:] if previous else [0,0]
            pick=pull['pickup_player'];ids[t][0],ids[t][pick]=ids[t][pick],ids[t][0]
        row=dict(h);row['players']={}
        for team,key in ((t,'o'),(1-t,'d')):
            for k,p in enumerate(h[key]):row['players'][(team,ids[team][k])]=point(p)
        row['absolute_o']=[point(p) for p in h['o']];row['absolute_d']=[point(p) for p in h['d']]
        for key in ('thrower','receiver','turnover_spot'):
            if h.get(key) is not None:row[key]=point(h[key])
        row['direction']=-1 if rotated else 1
        row['point']=1+sum(p['outcome']=='score' and p['end_turn']<h['turn'] for p in g['possessions'])
        row['goal']=h.get('throw_result')=='caught' and h['receiver'][1]>=17
        for frame in setup:frame['point']=row['point']
        if setup:row['setup']=setup
        result.append(row);previous=h
    return result


def broadcast_schedule(rows,highlights,max_seconds=150,points=None):
    """Select complete points only; routine actions use eased 3x motion.

    Explicit point lists are authoritative (an undersized budget raises).
    Automatic selection prefers a clean hold, turnover break, and final point;
    remove whole points if needed. Never remove turns within a selected point.
    """
    groups={p:[h for h in rows if h['point']==p] for p in sorted({h['point'] for h in rows})}
    complete=[p for p,rs in groups.items() if rs[-1]['goal']]
    if points is not None:
        if not set(points)<=set(complete):raise ValueError('points must name completed points')
        selected=sorted(set(points))
    elif highlights is None:selected=list(groups)
    else:
        clean=next((p for p in complete if not any(h.get('throw_result') in ('drop','interception') for h in groups[p])),None)
        breaker=next((p for p in complete if groups[p][-1]['team']!=groups[p][0]['team']),None)
        selected=sorted({p for p in (clean,breaker,complete[-1] if complete else None) if p is not None})
        for p in complete:
            if len(selected)>=3:break
            if p not in selected:selected.append(p)
        selected.sort()
    def build(chosen):
        schedule=[('title',None,None,60)];last=0
        for point in chosen:
            rs=groups[point];h=rs[0];prior=next((r for r in reversed(rows) if r['point']<point),None)
            card=dict(h,score=prior['score'] if prior else [0,0])
            card['card_text']=f'Point {point}'
            skipped=[p for p in complete if last<p<point]
            if skipped:
                wins=[sum(groups[p][-1]['team']==t for p in skipped) for t in (0,1)]
                card['skipped']=(skipped[0],skipped[-1],wins)
            schedule.append(('point_card',card,None,45));last=point
            if h.get('setup'):
                setup=h['setup'];schedule.append(('pull',setup[0],None,30))
                for before,after in zip(setup,setup[1:]):schedule.append(('run',after,before,21))
                schedule.append(('set',setup[-1],None,30));prev=setup[-1]
            else:
                schedule.extend([('pull',h,None,30),('set',h,None,30)]);prev=None
            for h in rs:
                event=h['goal'] or h.get('throw_result') in ('drop','interception')
                long=h.get('receiver') is not None and np.linalg.norm(np.array(h['receiver'])-h['thrower'])*5>15
                fast=highlights is not None and not event and not long
                count=30 if h.get('receiver') else 21
                schedule.append(('fast' if fast else 'play',h,prev,round(count/3) if fast else count))
                if event:schedule.append(('hold',h,None,45))
                if h['goal']:schedule.append(('replay',h,prev,30))
                prev=h
        schedule.append(('final',rows[-1],None,60));return schedule
    schedule=build(selected)
    if highlights is not None:
        while sum(n for *_,n in schedule)>max_seconds*30 and len(selected)>1 and points is None:
            selected.pop(0);schedule=build(selected)
        if sum(n for *_,n in schedule)>max_seconds*30:raise ValueError('max-seconds too small for selected whole points')
    return schedule


def generated_audio(schedule,rate=44100):
    """Deterministic, modest mono effects: vibrato whistles, crowd, disc air."""
    rng=np.random.default_rng(731);audio=np.zeros(round(sum(n for _,_,_,n in schedule)*rate/30),dtype=np.float32)
    cursor=0
    def add(start,duration,kind,gain):
        t=np.arange(round(duration*rate))/rate
        if kind=='whistle':
            phase=2*np.pi*3000*t+5*np.sin(2*np.pi*24*t)
            signal=np.sin(phase)*(.65+.35*np.sin(2*np.pi*35*t))
        else:
            noise=rng.standard_normal(len(t));smooth=np.convolve(noise,np.ones(23)/23,mode='same')
            signal=smooth if kind=='crowd' else np.convolve(noise,np.ones(7)/7,mode='same')
            signal/=max(np.std(signal),1e-6)
        signal=signal*np.sin(np.pi*t/duration)**2*gain
        at=round(start*rate);end=min(len(audio),at+len(signal));audio[at:end]+=signal[:end-at]
    for kind,h,prev,n in schedule:
        if kind=='set':add(cursor/30,.6,'whistle',.12)
        if kind=='hold':add(cursor/30,1.5 if h['goal'] else .6,'crowd' if h['goal'] else 'whistle',.10 if h['goal'] else .055)
        if kind=='play' and h.get('receiver') and np.linalg.norm(np.array(h['receiver'])-h['thrower'])>=6:add(cursor/30,.8,'whoosh',.035)
        cursor+=n
    peak=max(abs(audio).max(),1e-8)
    audio*=min(1,.65/peak)
    return audio


def video(g,out,n,max_seconds=150,no_audio=False,points=None):
    """Render broadcast frames with Pillow and stream directly to H.264."""
    from PIL import Image, ImageDraw, ImageFont
    import subprocess, math
    rows=absolute_records(g);schedule=broadcast_schedule(rows,n,max_seconds,points)
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
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(out)]
    import tempfile, wave
    audio_file=None
    if not no_audio:
        audio_file=tempfile.NamedTemporaryFile(suffix='.wav',dir=out.parent)
        samples=generated_audio(schedule)
        with wave.open(audio_file.name,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(44100);wav.writeframes((samples*32767).astype('<i2').tobytes())
        idx=cmd.index('-c:v');cmd[idx:idx]=['-i',audio_file.name,'-c:a','aac','-b:a','128k']
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    def arc(a,b,t):
        a=np.array(xy(a));b=np.array(xy(b));v=b-a
        control=(a+b)/2+np.array([v[1],-v[0]])*.20
        return (1-t)**2*a+2*(1-t)*t*control+t*t*b
    try:
        for kind,h,prev,count in schedule:
            for k in range(count):
                t=1.0 if kind in ('hold','set') else (.5+.5*(k+1)/count if kind=='replay' else (k+1)/count);s=t*t*(3-2*t);im=base.copy();d=ImageDraw.Draw(im)
                if kind=='point_card':
                    d.rectangle((0,0,W,H),fill=bg)
                    text(d,(960,350),h['card_text'],80,fill=gold)
                    text(d,(960,500),f"{g['teams'][0]} {h['score'][0]}   –   {h['score'][1]} {g['teams'][1]}",46)
                    if h.get('skipped'):
                        lo,hi,wins=h['skipped']
                        text(d,(960,660),f"Points {lo}–{hi}: {g['teams'][0]} {wins[0]}, {g['teams'][1]} {wins[1]}",32)
                elif kind in ('title','final'):
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
                        text(d,(960,930),'POACH / DOUBLE / SWITCH = defensive plays',24,fill='#a9bdc9')
                else:
                    active=h['team'];direction=h['direction'];is_turn=h.get('throw_result') in ('drop','interception')
                    # Score bug and permanent camera; only the attack arrow reverses.
                    for team,x in ((0,160),(1,1000)):
                        d.rounded_rectangle((x,60,x+760,155),radius=12,fill=COLORS[team]);text(d,(x+290,106),g['teams'][team],36);text(d,(x+670,106),str(h['score'][team]),56)
                    receiving=1-active if is_turn and kind in ('play','hold') and t>.75 else active
                    attack=-direction if receiving!=active else direction
                    text(d,(960,205),f"POINT {h['point']}    |    {g['teams'][receiving]} BALL   {'→' if attack>0 else '←'}",32)
                    players=h['players']
                    if kind=='pull' and not h.get('phase'):
                        # New receiving offense attacks direction; pull travels from opposite goal line.
                        players={}
                        for team in (0,1):
                            end=(2 if direction>0 else 17) if team==active else (17 if direction>0 else 2)
                            for j in range(3):players[(team,j)]=[2+j*2.5,end]
                    elif prev and not prev['goal']:
                        players={key:(np.array(prev['players'][key])*(1-s)+np.array(p)*s) for key,p in players.items()}
                    if kind not in ('pull','run','set'):
                        for j,m in enumerate(h['marks']):
                            a=xy(h['absolute_d'][j]);b=xy(h['absolute_o'][m]);v=np.array(b)-a
                            for z in np.arange(0,1,.10):d.line((tuple(np.array(a)+z*v),tuple(np.array(a)+min(z+.045,1)*v)),fill='#8aa99b',width=2)
                        a=xy(h['absolute_d'][h['marks'].index(0)]);d.ellipse((a[0]-28,a[1]-28,a[0]+28,a[1]+28),outline=gold,width=3)
                    for (team,j),p in players.items():
                        x,y=xy(p);d.ellipse((x-22,y-22,x+22,y+22),fill=COLORS[team],outline=white,width=3);text(d,(x,y),'ABC'[j],24)
                    if kind=='pull':
                        a=[4.5,17 if direction>0 else 2];b=h.get('landing',[4.5,2 if direction>0 else 17]);disc=arc(a,b,t)
                        text(d,(960,950),f"PULL  •  {g['teams'][1-active]} → {g['teams'][active]}",32,fill=gold)
                    else:
                        a=h['thrower'];b=h.get('receiver');disc=np.array(xy(a))
                        if b:
                            pts=[tuple(arc(a,b,z)) for z in np.linspace(0,1,35)];d.line(pts,fill='#d9bc64',width=3)
                            flight=t;landing=h.get('turnover_spot',b) if h.get('throw_result')=='interception' else b;disc=arc(a,landing,flight)
                            for lag in (.06,.12,.18):
                                p=arc(a,landing,max(0,flight-lag));r=max(2,6-lag*20);d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill='#bdc9bd')
                            text(d,(960,950),f"CATCH CHANCE {h['p']:.0%}   •   {h.get('throw_result','').upper()}",28)
                        if kind=='run':text(d,(960,950),'COVER RUN' if h.get('phase')=='rundown' else 'DISC PICKUP',28,fill=gold)
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
                    if kind=='fast':
                        d.rounded_rectangle((1480,910,1750,972),radius=10,fill=bg)
                        d.polygon([(1510,925),(1510,955),(1534,940)],fill=gold)
                        d.polygon([(1542,925),(1542,955),(1566,940)],fill=gold)
                        text(d,(1630,940),'3x',32,fill=gold)
                proc.stdin.write(im.tobytes())
                snap=('interception_hold_start' if k==0 else 'interception_hold_end' if k==30 else None) if kind=='hold' and h.get('throw_result')=='interception' else kind if kind in ('title','pull','run','final') else 'goal_replay' if kind=='replay' and h['goal'] else 'turnover' if kind=='play' and is_turn and t>.8 else None
                if kind=='fast':snap='fast_forward'
                if kind=='point_card' and h['point']>rows[0]['point']:snap='between_points'
                if kind in ('play','fast') and h['point']==rows[0]['point'] and h.get('receiver') and 7<=h['receiver'][1]<=12 and t>.65:snap='midfield'
                if kind=='run' and h.get('phase')=='rundown' and t>.5:snap='rundown'
                if snap and snap not in snapshots and (kind not in ('pull','replay') or t>.5):
                    snapshots[snap]={'frame':frame_index,'seconds':frame_index/30}
                frame_index+=1
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('ffmpeg encoding failed')
        if audio_file:audio_file.close()
    except BaseException:
        proc.kill();proc.wait();raise
    # These are actual decoded MP4 frames, not source drawings.
    for name,entry in snapshots.items():
        path=out.with_name(out.stem+'_'+name+'.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(entry['seconds']),'-i',str(out),'-frames:v','1',str(path)],check=True)
        entry['path']=str(path)
    info={'seconds':frame_index/30,'frames':frame_index,'resolution':'1920x1080','fps':30,'audio':not no_audio,'snapshots':snapshots}
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('histories',nargs='+',type=Path);p.add_argument('--points',type=int,nargs='+',help='Whole point numbers to render in highlights');p.add_argument('--game-index',type=int,default=0);p.add_argument('--highlights',type=int,metavar='N');p.add_argument('--out',type=Path,default=Path('outputs_dev/v7/media'));p.add_argument('--figures',action='store_true');p.add_argument('--video',action='store_true');p.add_argument('--no-audio',action='store_true');p.add_argument('--max-seconds',type=float,default=150);p.add_argument('--model',choices=['haiku','opus'],help='Model used by legacy LLM histories (which omit model metadata)');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    games=[g for path in a.histories for g in json.loads(path.read_text())]
    for g in games:
        if 'LLM' in g['teams']:
            model=g.get('model') or a.model
            if not model:p.error('LLM history omits model; supply the run model with --model haiku|opus')
            g['teams']=[model.title() if t=='LLM' else t for t in g['teams']]
    if a.figures:figures(games,a.out)
    if a.points is not None and a.highlights is None:a.highlights=3
    if a.video or not a.figures:
        g=games[a.game_index];name='_vs_'.join(g['teams'])+f'_game{a.game_index}'+('_highlights' if a.highlights is not None else '')
        print(json.dumps(video(g,a.out/(name+'.mp4'),a.highlights,a.max_seconds,a.no_audio,a.points),indent=2))
if __name__=='__main__':main()
