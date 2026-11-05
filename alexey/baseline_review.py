"""Independent check of reproduced educational baseline; upstream files unchanged."""
from pathlib import Path
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'alexey/results'
def rows(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
    orders=sorted([o for o in rows(ROOT/'data/processed/zakazy.csv') if o['period']=='2022-03'],key=lambda o:float(o['demand_t']),reverse=True)[:25]
    recipes=rows(ROOT/'data/processed/recepty.csv')
    quality=rows(ROOT/'data/processed/kachestvo.csv')
    qmap={(int(float(r['mass_code'])),int(float(r['shikhta_num']))):float(r['q2_press_yield'] or 'nan') for r in quality if r['period']=='2022-03'}
    cands={}
    for r in recipes:
        if r['period']=='2022-03':cands.setdefault(int(float(r['mass_code'])),set()).add(int(float(r['shikhta_num'])))
    plan=rows(OUT/'upstream_edu_assign.csv'); checks=[]
    for o in orders:
        oid=int(float(o['order_id'])); mc=int(float(o['mass_code'])); d=float(o['demand_t']); cs=sorted(cands.get(mc,set()))
        def q(sn):
            v=qmap.get((mc,sn),float('nan'))
            return .5 if math.isnan(v) else v
        chosen=[r for r in plan if int(float(r['order_id']))==oid]
        assert len(chosen)==1,('coverage',oid)
        r=chosen[0]; sn=int(float(r['shikhta_num']))
        assert sn in cs and int(float(r['mass_code']))==mc
        assert math.isclose(float(r['demand_t']),d) and math.isclose(float(r['q_used']),q(sn))
        checks.append({'order_id':oid,'mass_code':mc,'demand_t':d,'candidates':cs,'candidate_count':len(cs),'selected':sn,'q':q(sn),'contribution':d*q(sn),'best_without_resources':d*max(q(s) for s in cs)})
    assert len(plan)==len(orders)
    objective=math.fsum(x['contribution'] for x in checks)
    upper=math.fsum(x['best_without_resources'] for x in checks)
    reported=json.loads((OUT/'upstream_edu_solve.json').read_text())['objective']
    assert math.isclose(objective,reported,abs_tol=1e-8) and math.isclose(objective,upper,abs_tol=1e-8)
    result={'scope':'reproduced educational baseline, no material constraints','orders_checked':len(checks),'single_candidate_orders':sum(x['candidate_count']==1 for x in checks),'multiple_candidate_orders':sum(x['candidate_count']>1 for x in checks),'objective_recomputed':objective,'objective_reported':reported,'independent_upper_bound_without_resources':upper,'coverage_and_candidate_checks_passed':True,'material_feasibility':'not established: confirmed stocks and material constraints absent','orders':checks}
    (OUT/'baseline_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='orders'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
