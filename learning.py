"""Persistent CLI transport and descriptive sequential-game metrics."""
import collections, csv, json, subprocess, uuid
from pathlib import Path
PREAMBLE='You will coach many consecutive games against the same opponent; learn from results.'

class LearningSession:
    def __init__(self,model,session_id=None):
        self.model=model;self.session_id=str(uuid.UUID(session_id)) if session_id else str(uuid.uuid4())
        self.started=False;self.lessons=[];self.events=[]
        self.calls=self.failures=self.session_fallbacks=self.scripted_fallbacks=0
    def reset(self):
        old=self.session_id;self.session_id=str(uuid.uuid4());self.started=False;self.session_fallbacks+=1
        self.events.append(dict(kind='session_reset',previous=old,session_id=self.session_id))
    def request(self,prompt,parse=lambda x:x,kind='feedback'):
        # Retry once; then try this message on a fresh session seeded with lessons.
        for attempt in range(3):
            if attempt==2:self.reset()
            text=prompt if self.started else PREAMBLE+'\nLessons accumulated from earlier games:\n'+'\n'.join(self.lessons)+'\n'+prompt
            flag='--resume' if self.started else '--session-id';sid=self.session_id;self.calls+=1
            event=dict(kind=kind,session_id=sid,flag=flag,attempt=attempt+1);self.events.append(event)
            try:
                proc=subprocess.run(['claude','-p','--model',self.model,flag,sid,'--output-format','json',text],capture_output=True,text=True,timeout=120,check=True)
                envelope=json.loads(proc.stdout)
                if envelope.get('session_id'):self.session_id=str(uuid.UUID(envelope['session_id']))
                self.started=True;event['returned_session_id']=self.session_id
                event['model_ids']=list(envelope.get('modelUsage',{})) or ([envelope['model']] if envelope.get('model') else [])
                if envelope.get('is_error'):raise ValueError(str(envelope.get('result','CLI error')))
                result=parse(envelope['result']);event['ok']=True;return result
            except (subprocess.SubprocessError,OSError,ValueError,TypeError,KeyError,AttributeError,IndexError) as exc:
                self.failures+=1;event.update(ok=False,error=str(exc))
        self.reset() # Recovery failed; next message must start clean too.
        return None
    def snapshot(self):
        return dict(calls=self.calls,failures=self.failures,session_fallbacks=self.session_fallbacks,scripted_fallbacks=self.scripted_fallbacks,event_index=len(self.events),session_id=self.session_id)
    def since(self,before):
        events=self.events[before['event_index']:]
        return dict(model=self.model,initial_session_id=before['session_id'],final_session_id=self.session_id,session_ids=list(dict.fromkeys([before['session_id']]+[sid for e in events for sid in (e['session_id'],e.get('returned_session_id',e['session_id']))]+[self.session_id])),events=events,call_counts=dict(collections.Counter(e['kind'] for e in events if 'attempt' in e)),model_ids=list(dict.fromkeys(v for e in events for v in e.get('model_ids',[]))),**{k:getattr(self,k)-before[k] for k in ('calls','failures','session_fallbacks','scripted_fallbacks')})
    def point_feedback(self,teams,scorer,score,possessions):
        llm=teams.index('LLM');point=[]
        for p in reversed(possessions):
            if point and p['outcome']=='score':break
            point.append(p)
        turnovers=[p for p in reversed(point) if p['team']==llm and p['outcome']!='score']
        detail=', '.join(f"{p['outcome']} at row {p['turnover_spot'][1]}" for p in turnovers)
        name=self.model if scorer==llm else teams[scorer]
        return self.request(f'Point result: {name} scored after {len(turnovers)} of your turnovers'+(f' ({detail})' if detail else '')+f'. Score (team 0-team 1) {score[0]}-{score[1]}. Rows use the offense coordinates at that turnover. Reply OK.',kind='point_feedback')
    def game_feedback(self,metrics):
        def parse(text):
            if not isinstance(text,str):raise ValueError('lessons must be text')
            lines=[v.strip().lstrip('-* ').strip() for v in text.splitlines() if v.strip()]
            if not lines:raise ValueError('empty lessons')
            return lines[:5]
        lessons=self.request('Game summary: '+json.dumps(metrics)+'. Give up to 5 bullet lessons for the next game.',parse,'game_lessons')
        if lessons:self.lessons.extend(lessons)
        return lessons or []

def game_metrics(game):
    llm=game['teams'].index('LLM');rows={}
    for team in (0,1):
        poss=[p for p in game['possessions'] if p['team']==team]
        unfinished=int(bool(game['history']) and (not game['possessions'] or game['possessions'][-1]['end_turn']<game['turns']) and game['history'][-1]['team']==team)
        n=len(poss)+unfinished
        throws=[h for h in game['history'] if h['team']==team and h.get('receiver') is not None and h['side']==0]
        gains=[h['receiver'][1]-h['thrower'][1] for h in throws];counts=collections.Counter(p['outcome'] for p in poss if p['outcome']!='score')
        rows[team]=dict(team=team,coach=game['teams'][team],possessions=n,points=game['score'][team],points_per_possession=game['score'][team]/n if n else None,turnovers_by_type=dict(counts),turnovers_per_possession=sum(counts.values())/n if n else None,throws=len(throws),mean_rows_gained_per_throw=sum(gains)/len(gains) if gains else None,backward_throw_share=sum(v<0 for v in gains)/len(gains) if gains else None)
    opponent=1-llm
    return dict(score=game['score'],finished=game['finished'],llm=rows[llm],opponent=rows[opponent],calculator=rows[opponent] if game['teams'][opponent]=='Calculator' else None)

def write_learning_metrics(games,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for i,g in enumerate(games,1):
        m=g['metrics'];learn=g['learning'];a=m['llm'];b=m['opponent']
        rows.append(dict(game_index=i,seed=g['seed'],first=g['first'],score='-'.join(map(str,g['score'])),finished=g['finished'],model=g['model'],llm_points_per_possession=a['points_per_possession'],opponent_points_per_possession=b['points_per_possession'],calculator_points_per_possession=m['calculator']['points_per_possession'] if m['calculator'] else None,turnovers_per_possession=a['turnovers_per_possession'],mean_rows_gained_per_throw=a['mean_rows_gained_per_throw'],backward_throw_share=a['backward_throw_share'],wall_seconds=g['wall_seconds'],calls=learn['calls'],failures=learn['failures'],session_fallbacks=learn['session_fallbacks'],scripted_fallbacks=learn['scripted_fallbacks'],session_ids=learn['session_ids']))
    (out/'learning_metrics.json').write_text(json.dumps(rows,indent=2))
    with (out/'learning_metrics.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(2,2,figsize=(10,7));x=[r['game_index'] for r in rows]
    def line(ax,key,label):ax.plot(x,[float('nan') if r[key] is None else r[key] for r in rows],marker='o',label=label)
    line(axes[0,0],'llm_points_per_possession',games[0]['model']);line(axes[0,0],'opponent_points_per_possession',games[0]['teams'][1-games[0]['teams'].index('LLM')]);axes[0,0].legend();axes[0,0].set_ylabel('Points / possession')
    for ax,key,label in [(axes[0,1],'turnovers_per_possession','LLM turnovers / possession'),(axes[1,0],'mean_rows_gained_per_throw','LLM rows gained / throw'),(axes[1,1],'backward_throw_share','LLM backward throw share')]:line(ax,key,label);ax.set_ylabel(label)
    for ax in axes.flat:
        ax.set_xlabel('Sequential game');ax.set_xticks(x);ax.grid(alpha=.2)
        for r in rows:
            if r['session_fallbacks']:ax.axvline(r['game_index'],color='red',ls=':',alpha=.6)
    fig.suptitle('In-context learning (descriptive; red dotted lines mark session resets)');fig.tight_layout()
    for ext in ('png','pdf'):fig.savefig(out/f'learning_curve.{ext}',dpi=170)
    plt.close(fig)
