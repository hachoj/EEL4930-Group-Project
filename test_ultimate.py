import unittest, math
import ultimate as u
class Rules(unittest.TestCase):
 def test_distance(self):
  o=[[0,0],[0,4],[9,19]]; d=[[9,19]]*3
  self.assertAlmostEqual(u.catch(o,d,1),1/(1+math.exp((20-60)/20)))
 def test_front_behind(self):
  o=[[0,0],[0,5],[9,19]]
  self.assertLess(u.catch(o,[[0,4]],1),u.catch(o,[[0,6]],1))
 def test_overlap(self):
  self.assertTrue(0<=u.catch([[0,0]]*3,[[0,0]]*3,1)<=1)
 def test_holder_and_steps(self):
  o=[[3,4],[0,0],[9,19]];d=[[1,1]]*3
  for a in range(5):
   x,y,r=u.action(o,d,0,a);self.assertEqual(x[0],o[0]);self.assertEqual(y,d)
   for p,q in zip(o,x):self.assertLessEqual(max(abs(p[i]-q[i]) for i in (0,1)),1)
 def test_defense(self):
  o=[[3,4],[0,0],[9,19]];d=[[1,1]]*3
  for a in range(4):
   x,y,r=u.action(o,d,1,a);self.assertEqual(x,o);self.assertEqual(r,0)
 def test_sampling(self):
  import random
  rng=random.Random(4)
  for k in rng.sample(u.KEYS,100):self.assertEqual(u.key(*u.representative(k,rng)),k)
 def test_terminal(self):
  result=u.outcomes([[0,0],[0,17],[9,19]],[[9,0]]*3,0,3)
  self.assertEqual([j for p,j in result],[-1,-2]);self.assertAlmostEqual(sum(p for p,j in result),1)
 def test_horizon(self):
  # A two-state deterministic alternating reachability fixture.
  import numpy as np
  v=np.zeros((3,2));v[:,1]=1
  for t in range(1,3):v[t,0]=max(v[t-1,0],v[t-1,1])
  self.assertEqual(v[2,0],1)
if __name__=='__main__':unittest.main()

class CollisionRules(unittest.TestCase):
 def test_starts(self):
  for seed in range(100):
   o,d=u.start_positions(seed,depth=0)
   self.assertTrue(u.unique(o,d));self.assertEqual((o,d),u.start_positions(seed,depth=0))
   self.assertTrue(all(p[1]<=2 for p in o))
   self.assertTrue(all(1<=math.dist(p,q)<=2 for p,q in zip(o,d)))
 def test_no_overlap_during_play(self):
  for seed in range(30):
   o,d=u.start_positions(seed)
   for t in range(30):
    for a in range(5 if t%2==0 else 4):
     x,y,r=u.action(o,d,t%2,a);self.assertTrue(u.unique(x,y))
    o,d,r=u.action(o,d,t%2,(t+seed)%(5 if t%2==0 else 4))
 def test_collision_holds(self):
  o=[[2,2],[2,1],[5,1]];d=[[2,3],[5,3],[8,3]]
  x,y,r=u.action(o,d,0,1)
  self.assertEqual(x[1],o[1]);self.assertTrue(u.unique(x,y))

class Refinement(unittest.TestCase):
 def test_endzone_has_own_zone(self):
  self.assertNotEqual(u.zone([5,16]),u.zone([5,17]))
  self.assertEqual(u.zone([5,17]),u.zone([5,19]))
 def test_calibrated_starts(self):
  for seed in range(100):
   o,d=u.start_positions(seed)
   self.assertTrue(u.unique(o,d));self.assertEqual([p[1] for p in o],[12,13,14])
 def test_recorded_runs_no_overlap(self):
  import json
  from pathlib import Path
  f=Path('outputs_dev/games.json')
  if not f.exists():self.skipTest('optional recorded pilot absent')
  for g in json.loads(f.read_text()):
   for h in g['history']:self.assertTrue(u.unique(h['o'],h['d']))

class NamedLLM(unittest.TestCase):
 def test_named_reply_and_reported_model(self):
  import json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  from types import SimpleNamespace
  old=u.OUT
  with tempfile.TemporaryDirectory() as folder:
   u.OUT=Path(folder)
   reply={'result':json.dumps({'move_B':'stay','move_C':'stay','action':'hold'}),'modelUsage':{'test-reported-model':{}}}
   try:
    with patch.object(u.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(reply),stderr='')) as call:
     self.assertEqual(u.llm(*u.start_positions(42),0,30,'test-model'),120)
     prompt=json.loads(call.call_args.args[0][-1])
     self.assertIn('B',prompt['move_options']);self.assertNotIn('encoding',prompt)
     self.assertIn('test-reported-model',u.MODEL_IDS)
   finally:u.OUT=old;u.MODEL_IDS.discard('test-reported-model')

class FixedMarks(unittest.TestCase):
 def test_bijection_and_catch_remap(self):
  for seed in range(50):
   o,d=u.start_positions(seed); marks=u.assign_marks(o,d)
   self.assertEqual(sorted(marks),[0,1,2])
   identities=[o[m][:] for m in marks]
   for r in (1,2):
    x=[p[:] for p in o];x[0],x[r]=x[r],x[0]
    remap=[r if m==0 else 0 if m==r else m for m in marks]
    self.assertEqual([x[m] for m in remap],identities)
 def test_all_calculator_macros_follow_fixed_marks(self):
  # Covers every candidate the solved Calculator policy can select.
  for a in range(4):
   for seed in range(30):
    o,d=u.start_positions(seed);marks=u.assign_marks(o,d)
    for turn in range(10):
     o,_,_=u.action(o,d,0,1)
     _,d,_=u.action(o,d,1,a,marks)
     self.assertTrue(u.unique(o,d))
     for j,m in enumerate(marks):self.assertLessEqual(math.dist(d[j],o[m]),3)
 def test_recorded_fixed_marks_and_calculator_proximity(self):
  import json
  from pathlib import Path
  path=Path('outputs_dev/v3/games.json')
  if not path.exists():self.skipTest('v3 validation not generated')
  for game in json.loads(path.read_text()):
   o,d=u.start_positions(game['seed']);marks=u.assign_marks(o,d)
   for h in game['history']:
    self.assertEqual(h['marks'],marks)
    if game['defense']=='Calculator' and h['side']==1:
     self.assertTrue(all(math.dist(h['d'][j],h['o'][m])<=3 for j,m in enumerate(marks)))
    if h.get('throw_result')=='caught':
     r=h['o'].index(h['receiver']);marks=[r if m==0 else 0 if m==r else m for m in marks]

class SymmetricLanes(unittest.TestCase):
 def test_mirrored_lanes(self):
  for y in range(20):
   for x in range(10):self.assertEqual(u.zone([x,y])%3,2-u.zone([9-x,y])%3)
  self.assertEqual([sum(u.lane(x)==i for x in range(10)) for i in range(3)],[3,4,3])

class JointMovement(unittest.TestCase):
 def test_joint_moves(self):
  o=[[1,3],[4,4],[8,5]];d=[[1,6],[4,7],[8,8]]
  x,y,r=u.action(o,d,0,1)
  self.assertEqual(sum(a!=b for a,b in zip(o,x)),2)
  self.assertEqual(x[0],o[0]);self.assertTrue(u.unique(x,y))
  x,y,r=u.action(o,d,1,0,[0,1,2])
  self.assertEqual(sum(a!=b for a,b in zip(d,y)),3)
  self.assertTrue(u.unique(x,y))

class LaneSampling(unittest.TestCase):
 def test_sample_keys(self):
  import random
  rng=random.Random(72)
  for lane in range(3):
   for tag in range(3):
    k=(lane,3+lane,6+lane,tag,2)
    o,d=u.representative(k,rng)
    self.assertEqual(u.key(o,d),k)
 def test_scripted_cuts_are_joint_and_legal(self):
  o=[[1,3],[4,4],[8,5]];d=[[1,6],[4,7],[8,8]]
  x,y,r=u.scripted_cut(o,d)
  self.assertEqual(x[0],o[0]);self.assertTrue(u.unique(x,y))
  self.assertEqual(sum(a!=b for a,b in zip(o,x)),2)
  for a,b in zip(o,x):self.assertLessEqual(max(abs(a[i]-b[i]) for i in (0,1)),1)

class JointCalculator(unittest.TestCase):
 def test_action_product_and_typical_receiver_movement(self):
  import numpy as np
  import joint_calculator as c
  self.assertEqual(len(c.OFF_ACTIONS),300);self.assertEqual(len(c.DEF_ACTIONS),27)
  solver=c.Solver.__new__(c.Solver)
  solver.V=np.zeros((31,2,len(u.KEYS)+2));solver.V[:,:,len(u.KEYS)]=1
  # Equal continuation values exercise policy tie-breaking, without a full build.
  o,d=u.start_positions(1700)
  x,y,r=solver.concrete(o,d,0,30,u.assign_marks(o,d))
  self.assertEqual(x[0],o[0]);self.assertEqual(sum(p!=q for p,q in zip(o,x)),2)
  self.assertTrue(u.unique(x,y))
 def test_vectorized_transitions_match_rules(self):
  import numpy as np
  import joint_calculator as c
  import random
  rng=random.Random(77)
  reps=[u.representative(k,rng) for k in rng.sample(u.KEYS,100)]
  o=np.array([p[0] for p in reps]);d=np.array([p[1] for p in reps]);n=len(u.KEYS)
  self.assertEqual(c.keys(o,d).tolist(),[u.INDEX[u.key(x,y)] for x,y in reps])
  props=c.proposals(o,d)
  for a in (0,44,123,245,299):
   x,y,r=c.realize(o,d,0,a,props);ids,prob=c.transitions(x,y,r,n)
   for j in range(len(o)):
    self.assertTrue(u.unique(x[j].tolist(),y[j].tolist()))
    self.assertTrue(np.max(abs(x[j]-o[j]))<=1)
    if r:self.assertAlmostEqual(prob[j],u.catch(x[j].tolist(),y[j].tolist(),r))
    z=x[j].tolist()
    if r and z[r][1]>=17:self.assertEqual(ids[j],n)
    else:
     if r:z[0],z[r]=z[r],z[0]
     self.assertEqual(ids[j],u.INDEX[u.key(z,y[j].tolist())])
 def test_sparse_bellman_max_min(self):
  import numpy as np
  from scipy.sparse import csr_matrix
  import joint_calculator as c
  solver=c.Solver.__new__(c.Solver)
  solver.V=np.zeros((2,2,3));solver.V[:,:,1]=1
  solver.matrices=[[csr_matrix([[0,.4,.6]]),csr_matrix([[0,.8,.2]])]]*2
  self.assertAlmostEqual(solver.q_all(1,0).max(),.8)
  self.assertAlmostEqual(solver.q_all(1,1).min(),.4)
 def test_batched_policy_matches_scalar_candidates(self):
  import numpy as np
  import joint_calculator as c
  o,d=u.start_positions(1701);marks=u.assign_marks(o,d)
  solver=c.Solver.__new__(c.Solver)
  solver.V=np.random.default_rng(45).random((2,2,len(u.KEYS)+2));solver.V[:,:,len(u.KEYS)]=1;solver.V[:,:,len(u.KEYS)+1]=0
  for side in (0,1):
   oo=np.array(o)[None];dd=np.array(d)[None]
   props=c.proposals(oo,dd) if side==0 else c.defense_proposals(oo,dd,np.array(marks)[None])
   candidates=[];values=[]
   for a in range(300 if side==0 else 27):
    x,y,r=c.realize(oo,dd,side,a,props);ids,p=c.transitions(x,y,r,len(u.KEYS))
    candidates.append((x[0].tolist(),y[0].tolist(),r));values.append(float((p*solver.V[0,1-side,ids])[0]))
   a=max(range(300),key=lambda a:(values[a],sum(p[1] for p in candidates[a][0][1:]),sum(p!=q for p,q in zip(o,candidates[a][0])))) if side==0 else int(np.argmin(values))
   self.assertEqual(solver.concrete(o,d,side,1,marks),candidates[a])
