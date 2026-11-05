"""Read-only checks of upstream code/data; reproduction in a disposable directory."""
from pathlib import Path
import ast,csv,json,subprocess,sys,tempfile,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'alexey/results'


def main():
    OUT.mkdir(exist_ok=True)
    notebook=json.loads((ROOT/'docs/MILP_Solvers.ipynb').read_text())
    code=''.join(notebook['cells'][5]['source'])
    tree=ast.parse(code)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compute_metrics')
    ns={'orders':[{'mass_code':1,'demand':10.}], 'supply':{'A':10.},
        'recipes':{1:{1:{'A':20.}}},'quality':{(1,1):.9}}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'upstream_compute_metrics','exec'),ns)
    empty=ns['compute_metrics']([None])
    score_old=ns['compute_metrics']([1])[0]
    alternative_q={(1,1):.1}
    expected=10*alternative_q[1,1]
    checks={'empty_assignment_metrics':{'objective':empty[0],'violation':empty[1],
             'would_pass_violation_only':empty[1]<1e-3},
            'global_quality_probe':{'global_score':score_old,'alternative_q_score_expected':expected,
             'q_is_function_argument':any(a.arg=='q' for a in fn.args.args)}}
    stats={}
    for name in ['zakazy','recepty','kachestvo']:
        p=ROOT/f'data/processed/{name}.csv'
        with p.open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        stats[name]={'rows':len(rows),'fields':list(rows[0]) if rows else [],
                     'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    p=ROOT/'data/processed/events/ml_events_draft.csv'
    with p.open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    stats['ml_events_draft']={'rows':len(rows),'unique_event_ids':len({r['event_id'] for r in rows}),
         'fields':list(rows[0]),'contains_date_and_target':False,
         'note':'No timestamp/good/bad/target fields in this draft; known_at is not an event date.'}
    checks['data_stats']=stats
    repro={}
    with tempfile.TemporaryDirectory(prefix='shihta-review-') as tmp:
        d=Path(tmp)
        for pth in ['scripts','data/processed/milp','docs/iteration2']: (d/pth).mkdir(parents=True)
        for name in ['zakazy','recepty','kachestvo']:
            shutil.copy2(ROOT/f'data/processed/{name}.csv',d/f'data/processed/{name}.csv')
        for name in ['i2_k06_milp.py','i2_k08_validate.py']:
            shutil.copy2(ROOT/'scripts'/name,d/'scripts'/name)
            p=subprocess.run([sys.executable,str(d/'scripts'/name)],cwd=d,text=True,capture_output=True,timeout=60)
            repro[name]={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        for p in (d/'data/processed/milp').glob('*'):
            shutil.copy2(p,OUT/('upstream_'+p.name))
    checks['isolated_reproductions']=repro
    (OUT/'repository_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
