"""Read-only iteration-three audit. No ML training or May target evaluation."""
from pathlib import Path
import csv,json,math,inspect,collections,hashlib
import numpy as np
import scipy
from scipy.optimize import milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parents[2]; O=R/'alexey/results';O.mkdir(exist_ok=True)
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(name,v):(O/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
p=R/'data/processed/events/ml_events_draft.csv'; events=rows(p)
diag=json.loads((p.parent/'press_link_diag.json').read_text())
fields=list(events[0]); ids=[r['event_id'] for r in events]
coverage={f:dict(collections.Counter(r[f] for r in events)) for f in fields if f in ['period','mass_code','Марка массы, код','sh','shikhta_num','feature_after_recipe_flag','include']}
sample={'rows':len(events),'unique_event_ids':len(set(ids)),'duplicate_event_ids':len(ids)-len(set(ids)),'fields':fields,'coverage':coverage,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'press_rows':diag['n_press_rows'],'linked':diag['n_linked_to_lines'],'unlinked':diag['n_unlinked'],'linked_plus_unlinked':diag['n_linked_to_lines']+diag['n_unlinked'],'counts_reconcile':diag['n_press_rows']==diag['n_linked_to_lines']+diag['n_unlinked'],'training_allowed':False,'reason':'No confirmed target or precise event time; linked-row counts are not necessarily independent events.'}
save('I3-A-05_sample_audit.json',sample)
# Replicate only the existing March q2 diagnostic. No fit and no May evaluation.
k=[r for r in rows(R/'data/processed/kachestvo.csv') if r['period']=='2022-03' and r['q2_press_yield']!='']
y=np.array([float(r['q2_press_yield']) for r in k]); cut=int(len(y)*.7); train=y[:cut]; test=y[cut:]
preds={'all_good_1':np.ones_like(test),'train_mean':np.full_like(test,train.mean()),'fallback_global_mean':np.full_like(test,y.mean()),'simple_mean_model':np.full_like(test,train.mean())}
errors={name:float(np.mean(np.abs(test-v))) for name,v in preds.items()}
old=json.loads((R/'data/processed/ml/baseline_errors.json').read_text())['mae']
assert all(math.isclose(v,old[n],abs_tol=1e-12) for n,v in errors.items())
by_recipe=collections.defaultdict(list)
for row,t in zip(k[cut:],test):by_recipe[row['mass_code']+'/'+row['shikhta_num']].append(abs(float(t)-float(train.mean())))
metrics={'diagnostic_only':True,'target':'normalized March aggregate q2, not confirmed event label','n':len(y),'train_n':cut,'test_n':len(test),'mae':errors,'matches_saved_errors':True,'simple_model_equals_train_mean':True,'leaking_method':'fallback_global_mean uses train and test targets','best_nonleaking_control_in_this_diagnostic':min(['all_good_1','train_mean'],key=errors.get),'train_mean_errors_by_recipe':{key:{'n':len(v),'mae':sum(v)/len(v)} for key,v in by_recipe.items()},'event_scale_error':'not identifiable from normalized recipe aggregates','final_may_test_performed':False,'ml_usefulness_established':False}
save('I3-A-07_metric_audit.json',metrics)
sig=str(inspect.signature(milp)); result=milp(c=[-3.,-2.],integrality=[1,1],bounds=Bounds([0,0],[1,1]),constraints=LinearConstraint([[1.,1.]],[1],[1]))
assert result.success and math.isclose(-result.fun,3.)
save('I3-A-09_api_audit.json',{'scipy_version':scipy.__version__,'signature':sig,'x0_parameter':'x0' in inspect.signature(milp).parameters,'tiny_objective':float(-result.fun),'warm_start_consumption_proven':False,'scope':'installed scipy public interface; no claim about other solver APIs'})
print(json.dumps({'events':len(events),'unique_event_ids':len(set(ids)),'fields':fields,'count_reconciliation':sample['counts_reconcile'],'diagnostic_mae':errors,'groups':len(by_recipe),'tiny_objective':float(-result.fun)},ensure_ascii=False,indent=2))
