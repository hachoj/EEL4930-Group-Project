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

    def test_highlights_include_all_finishes_and_pulls_under_90(self):
        schedule=r.broadcast_schedule(self.rows,12)
        shown={h['turn'] for kind,h,prev,n in schedule if kind=='play'}
        ends={h['turn'] for h in self.rows if h['goal'] or h.get('throw_result') in ('drop','interception')}
        self.assertTrue(ends<=shown)
        self.assertLess(sum(n for _,_,_,n in schedule)/30,90)
        self.assertEqual(sum(kind=='pull' for kind,_,_,_ in schedule),1+sum(h['goal'] for h in self.rows[:-1]))

    def test_unknown_llm_modes_supported(self):
        g=dict(self.game);g['history']=[dict(h,coach='LLM') for h in self.game['history'][:6]]
        self.assertTrue(all(h['_modes']==['unknown']*3 for h in r.absolute_records(g) if h['side']==1))

if __name__=='__main__':unittest.main()
