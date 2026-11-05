"""I2-A-06: validator tests; Python standard library only."""
from copy import deepcopy
import json
from pathlib import Path
from validate_plan import validate_plan

def main():
 case={'orders':{str(i):{'demand_t':1.,'candidates':['H','L']} for i in range(1,4)},'recipes':{'H':{'usage_t_per_t':{'A':.6,'B':.3,'C':.1}},'L':{'usage_t_per_t':{'A':.2,'B':.3,'C':.5}}},'stocks':{'A':1.,'B':.9,'C':1.1}}
 good=[{'order_id':str(i),'recipe_id':rid} for i,rid in enumerate(['H','L','L'],1)]
 forbidden=deepcopy(good); forbidden[0]['recipe_id']='UNKNOWN'
 excess=deepcopy(good)
 for row in excess:row['recipe_id']='H'
 cases={'valid':good,'empty':[],'missing':good[:-1],'duplicate':good+[good[0]],'forbidden':forbidden,'stock_excess':excess}
 results={name:validate_plan(case,plan) for name,plan in cases.items()}
 for name,res in results.items():
  if res['valid'] != (name=='valid'):raise AssertionError(name)
 out=Path(__file__).resolve().parent/'results';out.mkdir(exist_ok=True)
 (out/'validator_checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print('6/6 checks passed: valid + five rejected invalid plans')
if __name__=='__main__':main()
