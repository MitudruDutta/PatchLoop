"""Illustrative planning arithmetic only; no PATCHLOOP experiments."""
from math import ceil, sqrt, isclose, log
from statistics import NormalDist, mean, pstdev
import json

z=NormalDist().inv_cdf
za,zb=z(0.975),z(0.8)
p1,p2=0.40,0.25
pbar=(p1+p2)/2
security=((za*sqrt(2*pbar*(1-pbar))+
           zb*sqrt(p1*(1-p1)+p2*(1-p2)))**2)/(p1-p2)**2
utility={str(d):ceil(2*0.9*0.1*(za+zb)**2/d**2)
         for d in (0.02,0.05,0.10)}
assert ceil(security)==152
assert list(utility.values())==[3532,566,142]
mixed={str(p):{str(g):1-p**g-(1-p)**g for g in (4,8)}
       for p in (0.02,0.05,0.10,0.30,0.50)}
for p in (0.02,0.05,0.10,0.30):
    for g in (4,8):
        assert isclose(1-p**g-(1-p)**g,
                       1-(1-p)**g-p**g,abs_tol=1e-14)
# Exact cost attenuation with a positive numerical stabilizer.
cost=[100.0,200.0,300.0,400.0]
eta,eps,a=0.1,1e-4,1.0
rewards=[a-eta*c for c in cost]
for c,r in zip(cost,rewards):
    direct=(r-mean(rewards))/(pstdev(rewards)+eps)
    derived=-(c-mean(cost))/pstdev(cost)*(
        eta*pstdev(cost)/(eta*pstdev(cost)+eps))
    assert isclose(direct,derived,rel_tol=1e-12,abs_tol=1e-12)
# Exact Bernoulli KL gradient w.r.t. the policy logit at policy=reference.
policy=reference=0.4
kl_gradient=policy*(1-policy)*log(
    policy*(1-reference)/(reference*(1-policy)))
assert isclose(kl_gradient,0.0,abs_tol=1e-14)
print(json.dumps({
    "status":"Illustrations; no project measurements",
    "security_per_arm":ceil(security),
    "utility_per_arm":utility,
    "mixed_probabilities_under_conditional_independence":mixed,
    "cost_identity_verified":True,
    "exact_kl_gradient_at_reference":kl_gradient,
    "joint_power_bounds_for_two_80_percent_tests":[0.6,0.8],
    "joint_power_if_independent":0.64,
    "assumptions":"Independent-arm normal approximations; 80% marginal power; security two-sided alpha .05; utility one-sided alpha .025 with both true rates .90; no continuity correction"
},indent=2))
