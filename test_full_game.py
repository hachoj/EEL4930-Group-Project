import json, math, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy.sparse import csr_matrix
import full_game as f
import ultimate as u

class FullRules(unittest.TestCase):
    def test_complete_action_product(self):
        self.assertEqual(len(f.DEF_ACTIONS),1372)
        self.assertEqual(len(set(f.DEF_ACTIONS)),1372)
    def test_tactics_legal_all_joint_options(self):
        for seed in range(10):
            o,d=u.start_positions(seed,0);marks=u.assign_marks(o,d)
            for (pair,modes),(x,y,m) in zip(f.DEF_ACTIONS,f.defense_candidates(np.array(o)[None],np.array(d)[None],np.array(marks)[None])):
                self.assertTrue(u.unique(x[0].tolist(),y[0].tolist()))
                self.assertTrue(np.max(abs(y[0]-np.array(d)))<=1)
                self.assertEqual(sorted(m[0]),[0,1,2])
                expected=marks[:]
                if pair is not None:expected[pair[0]],expected[pair[1]]=expected[pair[1]],expected[pair[0]]
                self.assertEqual(m[0].tolist(),expected)
    def test_lane_beats_equal_receiver_distance_behind(self):
        o=np.array([[[5,1],[5,9],[8,9]]]);front=np.array([[[5,5],[0,19],[9,19]]]);behind=np.array([[[5,13],[0,19],[9,19]]])
        p,a=f.throw_model(o,front,1);q,b=f.throw_model(o,behind,1)
        self.assertLess(p[0],q[0]);self.assertGreater(a[0,1],b[0,1])
        self.assertEqual(math.dist(front[0,0],o[0,1]),math.dist(behind[0,0],o[0,1]))
    def test_probability_partition_and_vector_parity(self):
        import random
        rng=random.Random(7);reps=[u.representative(k,rng) for k in rng.sample(u.KEYS,100)]
        o=np.array([x for x,y in reps]);d=np.array([y for x,y in reps])
        for r in (1,2):
            p,m=f.throw_model(o,d,r)
            np.testing.assert_allclose(p+m.sum(1),1,atol=1e-14)
            self.assertTrue((m>=0).all());self.assertTrue((p>=0).all())
            for k in range(len(o)):
                q,a=f.throw_model(o[k:k+1],d[k:k+1],r)
                self.assertAlmostEqual(q[0],p[k]);np.testing.assert_allclose(a[0],m[k])
    def test_flip_at_receiver_and_interceptor(self):
        o,d=u.start_positions(42,0)
        for interceptor in (None,0,1,2):
            spot=o[1] if interceptor is None else d[interceptor]
            x,y,m=f.flip(o,d,spot,interceptor)
            self.assertEqual(x[0],f.mirror(spot));self.assertTrue(u.unique(x,y))
            self.assertEqual(sorted(m),[0,1,2])
            if interceptor is not None:self.assertEqual(sorted(x),sorted(f.mirror(p) for p in d))
    def test_mirror_involution(self):
        for x in range(10):
            for y in range(20):self.assertEqual(f.mirror(f.mirror([x,y])),[x,y])
    def test_forced_throw_at_K_no_stall_turnovers(self):
        class Safe:
            def concrete(self,o,d,side,c,marks):return [p[:] for p in o],[p[:] for p in d],(1 if side==0 and c==2 else 0),marks[:]
        with patch.object(f,'throw_model',return_value=(np.array([1.]),np.zeros((1,4)))):
            g=f.game('Calculator','Calculator',1,Safe(),max_hold=3,safety_cap=18)
        self.assertTrue(g['safety_cap_triggered']);self.assertFalse(g['possessions'])
        self.assertEqual(g['history'][4]['throw_result'],'caught')
        for h in g['history']:
            if h['side']==0 and h['hold_counter']==2:self.assertIsNotNone(h['receiver'])
        self.assertEqual(g['history'][6]['hold_counter'],0)
    def test_scripted_forces_even_backward_throw(self):
        o=[[5,15],[2,2],[8,2]];d=[[4,15],[2,3],[8,3]]
        self.assertEqual(f.scripted(o,d,0,0,3,[0,1,2])[2],0)
        self.assertIn(f.scripted(o,d,0,2,3,[0,1,2])[2],(1,2))
    def test_score_other_team_restarts_goal_line(self):
        class Score:
            def concrete(self,o,d,side,c,marks):
                return [o[0],[1,17],[8,18]],d,1,marks
        with patch.object(f,'throw_model',return_value=(np.array([1.]),np.zeros((1,4)))):
            g=f.game('Calculator','Calculator',1,Score(),target=2,safety_cap=10)
        self.assertEqual(g['score'],[2,1]);self.assertTrue(g['finished'])
        self.assertEqual(g['history'][1]['team'],1)
        self.assertIn(g['history'][1]['thrower'][1],range(3))
    def test_llm_reciprocal_switch_and_cache(self):
        o,d=u.start_positions(5,0);marks=u.assign_marks(o,d)
        answer={'D1':'switch_D2','D2':'switch_D1','D3':'poach_deep'}
        result=SimpleNamespace(stdout=json.dumps({'result':json.dumps(answer)}))
        with tempfile.TemporaryDirectory() as td,patch.object(f.subprocess,'run',return_value=result) as call:
            x,y,r,m,n=f.llm(o,d,1,0,3,marks,'haiku',Path(td))
            self.assertEqual(m,[marks[1],marks[0],marks[2]]);self.assertEqual(n,1)
            self.assertTrue(u.unique(x,y))
            self.assertEqual(f.llm(o,d,1,0,3,marks,'haiku',Path(td))[-1],0);self.assertEqual(call.call_count,1)
    def test_llm_illegal_forced_hold_falls_back_to_throw(self):
        o,d=u.start_positions(5,0)
        result=SimpleNamespace(stdout=json.dumps({'result':json.dumps({'move_B':'stay','move_C':'stay','action':'hold'})}))
        with tempfile.TemporaryDirectory() as td,patch.object(f.subprocess,'run',return_value=result):
            self.assertIn(f.llm(o,d,0,2,3,[0,1,2],'haiku',Path(td))[2],(1,2))

class FixedPoint(unittest.TestCase):
    def fixture(self):
        s=f.Solver.__new__(f.Solver);s.n=1;s.max_hold=2;s.gamma=.8
        # Every throw scores with .6, transfers possession with .4; holds remain in place.
        hold=csr_matrix(([1.],([0],[0])),shape=(1,17))
        throw=csr_matrix(([.6,.4],([0,0],[1,2])),shape=(1,17))
        s.matrices=[[hold if a[2]==0 else throw for a in f.j.OFF_ACTIONS],[hold]]
        return s
    def test_converges_and_bellman_residual(self):
        s=self.fixture();v=np.zeros((2,2,1))
        with patch.object(f,'RESTART',np.zeros(15,dtype=int)),patch.object(f,'GOAL_START',0):
            for k in range(300):
                nxt=s.backup(v);err=np.max(abs(v-nxt));v=nxt
                if err<1e-10:break
            self.assertLess(err,1e-10);self.assertLess(k,300)
            np.testing.assert_allclose(s.backup(v),v,atol=1e-10)
            self.assertGreater(v[0,0,0],0)
    def test_contraction_and_forced_mask(self):
        s=self.fixture()
        with patch.object(f,'RESTART',np.zeros(15,dtype=int)),patch.object(f,'GOAL_START',0):
            a=np.random.default_rng(1).random((2,2,1));b=np.random.default_rng(2).random((2,2,1))
            self.assertLessEqual(np.max(abs(s.backup(a)-s.backup(b))),s.gamma*np.max(abs(a-b))+1e-14)
            # Enormously desirable defense continuation would prefer hold; forced mask excludes it.
            v=np.zeros((2,2,1));v[:,1]=100
            self.assertLess(s.backup(v)[1,0,0],1)

class ConcreteRefinement(unittest.TestCase):
    def test_batched_defense_matches_unbatched_joint_actions(self):
        s=f.Solver.__new__(f.Solver);s.n=len(u.KEYS);s.max_hold=3;s.gamma=.97
        s.V=np.random.default_rng(22).random((3,2,s.n))
        o,d=u.start_positions(42,0);marks=u.assign_marks(o,d);oo=np.array(o)[None];dd=np.array(d)[None];mm=np.array(marks)[None]
        candidates=list(f.defense_candidates(oo,dd,mm))
        values=[s.evaluate(x,y,0,m,1,1)[0] for x,y,m in candidates]
        x,y,m=candidates[int(np.argmin(values))]
        self.assertEqual(s.concrete(o,d,1,1,marks),(x[0].tolist(),y[0].tolist(),0,m[0].tolist()))
    def test_calculator_forced_throw_at_K(self):
        s=f.Solver.__new__(f.Solver);s.n=len(u.KEYS);s.max_hold=3;s.gamma=.97
        s.V=np.zeros((3,2,s.n));s.V[:,1]=100
        o,d=u.start_positions(42,0);marks=u.assign_marks(o,d)
        self.assertIn(s.concrete(o,d,0,2,marks)[2],(1,2))

class TurnoverIntegration(unittest.TestCase):
    def test_only_incompletion_turnovers_at_correct_spots_and_flips(self):
        class Throw:
            def concrete(self,o,d,side,c,marks):return [p[:] for p in o],[p[:] for p in d],1 if side==0 else 0,marks[:]
        for k in range(4):
            masses=np.zeros((1,4));masses[0,k]=1
            with patch.object(f,'throw_model',return_value=(np.array([0.]),masses)):
                g=f.game('Calculator','Calculator',7,Throw(),safety_cap=2)
            first=g['history'][0];expected=first['receiver'] if k==0 else first['d'][k-1]
            self.assertEqual(first['turnover_spot'],expected)
            self.assertEqual(first['throw_result'],'drop' if k==0 else 'interception')
            self.assertEqual(g['history'][1]['thrower'],f.mirror(expected))
            self.assertEqual([p['team'] for p in g['possessions']],[0,1])
    def test_llm_accepts_double_and_both_poach_options(self):
        o,d=u.start_positions(7,0)
        for mode in ('poach_lane','poach_deep','double_B','double_C'):
            answer={f'D{k}':mode for k in (1,2,3)}
            result=SimpleNamespace(stdout=json.dumps({'result':json.dumps(answer)}))
            with tempfile.TemporaryDirectory() as td,patch.object(f.subprocess,'run',return_value=result):
                x,y,r,m,n=f.llm(o,d,1,0,3,[0,1,2],'haiku',Path(td))
                self.assertTrue(u.unique(x,y));self.assertEqual(n,1)
