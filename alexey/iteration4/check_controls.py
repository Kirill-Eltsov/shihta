"""Controls for a future method adapter; current reference implementation only."""
from pathlib import Path
import sys,json,hashlib,math,copy,platform
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
from validate_plan import validate_plan
from score_plan import score_plan
from reference_case import enumerate_all,solve
import scipy

def classify(case,plan,q,proof_infeasible=False):
    if proof_infeasible:return {'status':'infeasible','objective':None}
    if not plan:return {'status':'no_solution_found','objective':None}
    try:
        v=validate_plan(case,plan)
        if not v['valid']:return {'status':'invalid_plan','objective':None,'errors':v['errors']}
        return {'status':'feasible','objective':score_plan(case,plan,q)}
    except (KeyError,TypeError,ValueError) as e:
        return {'status':'error','objective':None,'error':str(e)}

def main():
    raw=(P/'scenarios_v1.json').read_bytes(); scenarios=json.loads(raw)['scenarios'];checks=[]
    for s in scenarios:
        case=s['case'];q={(r['order_id'],r['recipe_id']):r['value'] for r in s['q']}
        rows=enumerate_all(case,q); feasible=[v for v in rows if v['feasible']]
        res,plan=solve(case,q)
        if s['expected_status']=='infeasible':
            assert not feasible and res.status==2
            checks.append({'id':'deficit','status':'infeasible','objective':None,'proof':'complete enumeration and MILP status 2'})
        else:
            actual=classify(case,plan,q)
            assert res.success and actual['status']=='feasible'
            best=max(v['objective'] for v in feasible)
            assert math.isclose(best,s['expected_objective'],abs_tol=1e-8,rel_tol=1e-9)
            assert math.isclose(actual['objective'],best,abs_tol=1e-8,rel_tol=1e-9)
            checks.append({'id':s['scenario_id'],'status':'optimal','objective':actual['objective'],'plan':plan,'used_t':validate_plan(case,plan)['used_t']})
    base=scenarios[0];case=base['case'];q={(r['order_id'],r['recipe_id']):r['value'] for r in base['q']}
    old=[{'order_id':str(i),'recipe_id':r} for i,r in enumerate(['H','L','L'],1)]
    assert math.isclose(score_plan(case,old,q),2.5)
    banned=copy.deepcopy(case);banned['orders']['1']['candidates']=['L']
    bad=classify(banned,old,q);assert bad['status']=='invalid_plan' and any('forbidden_recipe' in e for e in bad['errors'])
    checks.append({'id':'forbidden_candidate',**bad})
    assert any(v['feasible'] for v in enumerate_all(banned,q))
    checks.append({'id':'forbidden_does_not_imply_infeasible','passed':True})
    changed=dict(q);changed['1','H']=.1
    assert math.isclose(score_plan(case,old,changed),1.65)
    checks.append({'id':'explicit_changed_q_old_plan','objective':1.65,'passed':True})
    empty=classify(case,[],q);assert empty['status']=='no_solution_found';checks.append({'id':'unproven_empty',**empty})
    malformed=classify(case,[{'wrong':'schema'}],q);assert malformed['status']=='error';checks.append({'id':'malformed_output',**malformed})
    result={'scope':'reference controls passed; Kirill integration not tested','input_sha256':hashlib.sha256(raw).hexdigest(),'python':platform.python_version(),'scipy':scipy.__version__,'checks_run':len(checks),'all_passed':True,'checks':checks}
    (P/'control_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{len(checks)}/{len(checks)} controls passed; reference only")
if __name__=='__main__':main()
