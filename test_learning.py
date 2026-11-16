import contextlib, io, json, subprocess, tempfile, unittest, uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import full_game as f
from learning import LearningSession, game_metrics

def cli(args,**kwargs):
    prompt=args[-1]
    if 'Point result:' in prompt:answer='OK'
    elif 'Game summary:' in prompt:answer='- Advance safely.\n- Watch the lane.'
    elif 'you coach OFFENSE' in prompt:answer=json.dumps(dict(move_B='N',move_C='N',action='throw_C'))
    else:answer=json.dumps(dict(D1='tight_front',D2='poach_lane',D3='double_C'))
    flag='--resume' if '--resume' in args else '--session-id'
    return SimpleNamespace(stdout=json.dumps(dict(result=answer,session_id=args[args.index(flag)+1])))

class FakeCalculator:
    def concrete(self,o,d,side,c,marks):return f.scripted(o,d,side,c,3,marks)

class LearningTests(unittest.TestCase):
    def test_start_resume_returned_identity_and_preamble(self):
        sid=str(uuid.uuid4());returned=str(uuid.uuid4());session=LearningSession('opus',sid)
        with patch('subprocess.run',return_value=SimpleNamespace(stdout=json.dumps(dict(result='OK',session_id=returned)))) as call:
            session.request('first');session.request('second')
        first,second=[c.args[0] for c in call.call_args_list]
        self.assertIn('--session-id',first);self.assertEqual(first[first.index('--session-id')+1],sid)
        self.assertIn('--resume',second);self.assertEqual(second[second.index('--resume')+1],returned)
        self.assertIn('learn from results',first[-1]);self.assertEqual(second[-1],'second')
    def test_cache_bypassed_and_scripted_fallback_counted(self):
        o,d,marks,_=f.pull_setup(__import__('random').Random(1));session=LearningSession('haiku')
        with tempfile.TemporaryDirectory() as td,patch('subprocess.run',side_effect=cli) as call:
            for _ in range(2):f.llm(o,d,0,0,3,marks,'haiku',Path(td),session=session)
            self.assertEqual(call.call_count,2);self.assertFalse((Path(td)/'cache').exists())
        with tempfile.TemporaryDirectory() as td,patch('subprocess.run',side_effect=subprocess.TimeoutExpired('claude',120)):
            info={};f.llm(o,d,0,0,3,marks,'haiku',Path(td),action_info=info,session=session)
        self.assertEqual(session.scripted_fallbacks,1);self.assertEqual(session.failures,3)
        self.assertEqual(session.session_fallbacks,2);self.assertIn('action',info)
    def test_failure_retry_fresh_session_with_lessons(self):
        s=LearningSession('opus');s.lessons=['Keep advancing.'];before=s.session_id
        results=[subprocess.CalledProcessError(1,'claude'),SimpleNamespace(stdout=json.dumps(dict(is_error=True,result='context exceeded'))),SimpleNamespace(stdout=json.dumps(dict(result='OK')))]
        with patch('subprocess.run',side_effect=results) as call:self.assertEqual(s.request('decision'),'OK')
        self.assertEqual(s.calls,3);self.assertEqual(s.failures,2);self.assertEqual(s.session_fallbacks,1);self.assertNotEqual(before,s.session_id)
        self.assertIn('Keep advancing.',call.call_args.args[0][-1]);self.assertIn('--session-id',call.call_args.args[0])
    def test_point_feedback_only_current_point(self):
        s=LearningSession('opus');poss=[dict(team=0,outcome='drop',turnover_spot=[1,12]),dict(team=1,outcome='score'),dict(team=0,outcome='interception',turnover_spot=[2,6]),dict(team=1,outcome='score')]
        with patch('subprocess.run',side_effect=cli) as call:s.point_feedback(['LLM','Calculator'],1,[0,2],poss)
        prompt=call.call_args.args[0][-1];self.assertIn('1 of your turnovers',prompt);self.assertIn('interception at row 6',prompt);self.assertNotIn('drop at row 12',prompt)
    def test_mocked_three_game_runner_metrics_and_figures(self):
        with tempfile.TemporaryDirectory() as td:
            games,calls=self.run_three(Path(td))
            self.assertEqual([g['first'] for g in games],[0,1,0]);self.assertEqual([g['seed'] for g in games],[1700,1701,1702])
            self.assertTrue(all(g['finished'] for g in games));self.assertFalse((Path(td)/'cache').exists())
            self.assertEqual(calls[0].args[0][4],'--session-id')
            sid=calls[0].args[0][5]
            for c in calls[1:]:self.assertEqual(c.args[0][4:6],['--resume',sid])
            for g in games:
                events=g['learning']['events'];kinds=[e['kind'] for e in events]
                self.assertEqual(kinds.count('point_feedback'),sum(g['score']));self.assertEqual(kinds[-1],'game_lessons')
                self.assertEqual(kinds.count('decision'),g['llm_decisions']);self.assertEqual(g['llm_calls'],len(events));self.assertEqual(len(g['lessons']),2)
                for index,e in enumerate(events):
                    if e['kind']=='point_feedback':self.assertTrue(index==0 or events[index-1]['kind']=='decision')
                self.assertIsNotNone(g['metrics']['calculator']);self.assertEqual(g['learning']['failures'],0)
            for name in ('learning_metrics.json','learning_metrics.csv','learning_curve.png','learning_curve.pdf'):self.assertGreater((Path(td)/name).stat().st_size,100)
            rows=json.loads((Path(td)/'learning_metrics.json').read_text());self.assertEqual(len(rows),3)
            self.assertEqual(rows[0]['llm_points_per_possession'],games[0]['score'][0]/games[0]['metrics']['llm']['possessions'])
    @staticmethod
    def run_three(out):
        args=['full_game.py','--team0','LLM','--team1','Calculator','--learn','--n','3','--target','2','--model','opus','--pressure','.1','--samples','4','--out',str(out)]
        with patch('sys.argv',args),patch('subprocess.run',side_effect=cli) as call,patch.object(f,'Solver'),patch.object(f,'load_solver',return_value=FakeCalculator()),contextlib.redirect_stdout(io.StringIO()):f.main()
        return json.loads((out/'LLM_vs_Calculator_games.json').read_text()),call.call_args_list

if __name__=='__main__':unittest.main()
