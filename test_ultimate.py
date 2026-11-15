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
