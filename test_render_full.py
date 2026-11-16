"""Presentation contracts; no rules/solver changes."""
import json
import unittest
from pathlib import Path
import numpy as np
import render_full as r
import full_game as f

class BroadcastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=json.loads(Path('outputs_dev/v7/Calculator_vs_Scripted_games.json').read_text())[0]
        cls.rows=r.absolute_records(cls.game)

    def test_turnover_absolute_continuity(self):
        checked=0
        for i,prev in enumerate(self.rows[:-1]):
            if prev.get('throw_result') not in ('drop','interception'):continue
            h=self.rows[i+1];raw=self.game['history'][i]
            self.assertEqual(h['direction'],-prev['direction'])
            # Only nearest-defender pickup and a player displaced from its
            # occupied pickup cell can jump. All other players move <=1 grid
            # square (diagonals allowed) through the transfer and first action.
            t=h['team'];spot=np.array(prev['turnover_spot'])
            pickup=min((key for key in prev['players'] if key[0]==t),key=lambda key:np.linalg.norm(np.array(prev['players'][key])-spot))
            for key,p in h['players'].items():
                before=np.array(prev['players'][key]);distance=np.max(abs(np.array(p)-before))
                if key==pickup or np.array_equal(before,spot):continue
                self.assertLessEqual(distance,1,(raw['turn'],key,before,p))
            checked+=1
        self.assertGreater(checked,10)

    def test_scoring_switches_ends(self):
        for prev,h in zip(self.rows,self.rows[1:]):
            if prev['goal']:
                self.assertEqual(h['direction'],prev['direction'])
                self.assertNotEqual(h['team'],prev['team'])
                self.assertEqual(h['point'],prev['point']+1)

    def test_whole_points_and_budget(self):
        schedule=r.broadcast_schedule(self.rows,3)
        shown=[h for kind,h,prev,n in schedule if kind in ('play','fast')]
        for point in {h['point'] for h in shown}:
            self.assertEqual([h['turn'] for h in shown if h['point']==point],
                             [h['turn'] for h in self.rows if h['point']==point])
        self.assertLessEqual(sum(n for *_,n in schedule)/30,150)
        self.assertTrue(any(kind=='fast' for kind,*_ in schedule))
        self.assertEqual(sum(kind=='pull' for kind,*_ in schedule),len({h['point'] for h in shown}))
        with self.assertRaises(ValueError):r.broadcast_schedule(self.rows,3,1)

    def test_v8_continuous_rendered_turns(self):
        g=json.loads(Path('outputs_dev/v8/demo/Calculator_vs_Scripted_games.json').read_text())[0]
        rows=r.absolute_records(g)
        schedule=r.broadcast_schedule(rows,3,150,points=[1,2,3])
        count=0
        for kind,h,prev,n in schedule:
            if kind not in ('play','fast','run') or prev is None:continue
            # Administrative seal/pickup changes already exist in the engine;
            # renderer must use exactly adjacent original states, never a cut.
            if kind in ('play','fast') and not h.get('setup'):
                i=rows.index(h);self.assertIs(prev,rows[i-1])
            exception=prev.get('throw_result') in ('caught','drop','interception')
            for key,pos in h['players'].items():
                distance=np.max(abs(np.array(pos)-prev['players'][key]))
                if exception:continue  # inherited seal / pickup only
                self.assertLessEqual(distance,1,(h['turn'],key))
                count+=1
        self.assertGreater(count,500)

    def test_labels_anchor_to_interpolated_players(self):
        # Includes holder swaps, turnovers, and both attack directions.
        for before,h in zip(self.rows,self.rows[1:]):
            players={key:.7*np.array(before['players'][key])+.3*np.array(p)
                     for key,p in h['players'].items()}
            offense,defense=r.role_positions(h,players)
            actual_o,actual_d=r.role_positions(h,h['players'])
            np.testing.assert_array_equal(actual_o,h['absolute_o'])
            np.testing.assert_array_equal(actual_d,h['absolute_d'])
            for k in range(3):
                np.testing.assert_array_equal(defense[k],players[h['defense_keys'][k]])
                np.testing.assert_array_equal(offense[k],players[h['offense_keys'][k]])
            self.assertEqual(set(h['offense_keys'])|set(h['defense_keys']),set(players))
        # Drawing code uses these exact positions for mode labels AND seal.
        import inspect
        source=inspect.getsource(r.video)
        self.assertIn("xy(defense[j]);label=",source)
        self.assertIn("xy(defense[h['marks'].index(0)])",source)

    def test_throw_outcome_geometry(self):
        h=dict(thrower=[3,2],receiver=[3,12],turnover_spot=[3,7],throw_result='interception')
        self.assertEqual(r.throw_endpoint(h),[3,7])
        h['throw_result']='drop'
        self.assertEqual(r.throw_endpoint(h),[3,12])
        np.testing.assert_array_equal(r.drop_skid(.5),[0,0])
        self.assertGreater(np.linalg.norm(r.drop_skid(1)),20)
        np.testing.assert_array_equal(r.drop_skid(1),r.drop_skid(2))
        h['throw_result']='throwaway'
        self.assertGreater(r.throw_endpoint(h)[1],12)

    def test_pacing_and_audio(self):
        schedule=r.broadcast_schedule(self.rows,None)
        self.assertTrue(all(n==45 for kind,h,prev,n in schedule if kind=='hold'))
        self.assertTrue(all(n>=21 for kind,h,prev,n in schedule if kind=='play'))
        self.assertEqual(sum(kind=='set' for kind,_,_,_ in schedule),1+sum(h['goal'] for h in self.rows[:-1]))
        intro=schedule[:next(i+1 for i,x in enumerate(schedule) if x[0]=='set')]
        audio=r.generated_audio(intro)
        self.assertGreater(np.max(abs(audio)),0)
        self.assertLessEqual(np.max(abs(audio)),.65)
        self.assertEqual(len(audio),round(sum(n for _,_,_,n in intro)*44100/30))

    def test_unknown_llm_modes_supported(self):
        g=dict(self.game);g['history']=[dict(h,coach='LLM') for h in self.game['history'][:6]]
        self.assertTrue(all(h['_modes']==['unknown']*3 for h in r.absolute_records(g) if h['side']==1))

if __name__=='__main__':unittest.main()
