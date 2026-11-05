"""Three orders x two recipes x three resources; all data explicitly synthetic."""
from copy import deepcopy
from itertools import product
from math import isclose
import csv
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from validate_plan import validate_plan
from score_plan import score_plan

HERE = Path(__file__).resolve().parent


def make_case():
    return {
        'synthetic': True, 'period': 'educational',
        'orders': {str(i): {'demand_t': 1., 'candidates': ['H', 'L']} for i in range(1,4)},
        'recipes': {
            'H': {'usage_t_per_t': {'A': .6, 'B': .3, 'C': .1}},
            'L': {'usage_t_per_t': {'A': .2, 'B': .3, 'C': .5}}},
        'stocks': {'A': 1.0, 'B': .9, 'C': 1.1}}


def default_q():
    return {(str(i), r): v for i, pair in enumerate([(.95,.70),(.90,.80),(.85,.75)], 1)
            for r,v in zip(['H','L'],pair)}


def enumerate_all(case, q):
    """Independent arithmetic: does not call solver, validator or scorer."""
    rows = []
    ids = list(case['orders'])
    for choice in product(*(case['orders'][i]['candidates'] for i in ids)):
        used = {c: sum(case['orders'][i]['demand_t'] *
                       case['recipes'][r]['usage_t_per_t'].get(c,0.)
                       for i,r in zip(ids,choice)) for c in case['stocks']}
        obj = sum(case['orders'][i]['demand_t']*q[i,r] for i,r in zip(ids,choice))
        feasible = all(used[c] <= case['stocks'][c]+1e-8 for c in used)
        rows.append({'choices': '/'.join(choice), **used, 'objective':obj,'feasible':feasible})
    return rows


def solve(case,q):
    pairs = [(o,r) for o,v in case['orders'].items() for r in v['candidates']]
    matrix=[]; lb=[]; ub=[]
    for o in case['orders']:
        matrix.append([float(oo==o) for oo,r in pairs]);lb.append(1.);ub.append(1.)
    for component, stock in case['stocks'].items():
        matrix.append([case['orders'][o]['demand_t'] *
                       case['recipes'][r]['usage_t_per_t'].get(component,0.) for o,r in pairs])
        lb.append(-np.inf);ub.append(stock)
    result=milp(c=-np.array([case['orders'][o]['demand_t']*q[o,r] for o,r in pairs]),
                integrality=np.ones(len(pairs)),bounds=Bounds(0,1),
                constraints=LinearConstraint(np.array(matrix),lb,ub))
    plan=[] if result.x is None else [{'order_id':o,'recipe_id':r}
                                     for (o,r),x in zip(pairs,result.x) if x>.5]
    return result,plan


class Checks(unittest.TestCase):
    def setUp(self):
        self.case=make_case();self.q=default_q()
        self.plan=[{'order_id':str(i),'recipe_id':r} for i,r in enumerate(['H','L','L'],1)]
    def test_valid_and_score(self):
        self.assertTrue(validate_plan(self.case,self.plan)['valid'])
        self.assertAlmostEqual(score_plan(self.case,self.plan,self.q),2.5)
    def test_empty(self): self.assertFalse(validate_plan(self.case,[])['valid'])
    def test_missing(self): self.assertFalse(validate_plan(self.case,self.plan[:-1])['valid'])
    def test_duplicate(self): self.assertFalse(validate_plan(self.case,self.plan+[self.plan[0]])['valid'])
    def test_forbidden(self):
        self.plan[0]['recipe_id']='UNKNOWN'
        self.assertFalse(validate_plan(self.case,self.plan)['valid'])
    def test_excess(self):
        for row in self.plan: row['recipe_id']='H'
        self.assertIn('stock_exceeded:A',validate_plan(self.case,self.plan)['errors'])
    def test_unknown_order(self):
        self.assertFalse(validate_plan(self.case,self.plan+[{'order_id':'X','recipe_id':'H'}])['valid'])
    def test_missing_stock(self):
        del self.case['stocks']['A']
        self.assertFalse(validate_plan(self.case,self.plan)['valid'])
    def test_explicit_q(self):
        q=dict(self.q);q['1','H']=.1
        self.assertAlmostEqual(score_plan(self.case,self.plan,q),1.65)
    def test_resource_optimum(self):
        rows=enumerate_all(self.case,self.q);result,plan=solve(self.case,self.q)
        self.assertEqual(len(rows),8);self.assertTrue(result.success)
        self.assertAlmostEqual(-result.fun,max(r['objective'] for r in rows if r['feasible']))
        self.assertAlmostEqual(score_plan(self.case,plan,self.q),2.5)
    def test_infeasible(self):
        self.case['stocks']['B']=.8
        self.assertFalse(any(r['feasible'] for r in enumerate_all(self.case,self.q)))
        result,plan=solve(self.case,self.q)
        self.assertEqual(result.status,2);self.assertEqual(plan,[])
    def test_changed_q(self):
        self.q['1','H']=.1
        result,plan=solve(self.case,self.q)
        self.assertAlmostEqual(-result.fun,2.35)
        self.assertAlmostEqual(score_plan(self.case,plan,self.q),2.35)


def main():
    out=HERE/'results';out.mkdir(exist_ok=True)
    case=make_case();q=default_q();rows=enumerate_all(case,q)
    with (out/'eight_assignments.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    scenarios={}
    for name in ['base','deficit','changed_q']:
        c=deepcopy(case);qq=dict(q)
        if name=='deficit':c['stocks']['B']=.8
        if name=='changed_q':qq['1','H']=.1
        res,plan=solve(c,qq)
        scenarios[name]={'solver_status':int(res.status),'message':res.message,'plan':plan,
                         'objective':None if res.fun is None else float(-res.fun),
                         'validation':validate_plan(c,plan),
                         'independent_score':score_plan(c,plan,qq) if res.success else None}
    runner=unittest.TextTestRunner(verbosity=2)
    tests=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    import scipy,sys
    payload={'synthetic':True,'scenarios':scenarios,'tests_run':tests.testsRun,
             'tests_passed':tests.wasSuccessful(),'python':sys.version,'scipy':scipy.__version__}
    (out/'reference_results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 0 if tests.wasSuccessful() else 1


if __name__=='__main__': raise SystemExit(main())
