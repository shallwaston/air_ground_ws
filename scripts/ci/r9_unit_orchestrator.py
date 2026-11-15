#!/usr/bin/env python3
"""Preserve exact R9 34 case IDs/order/input/assertions; source-only workers.
The original run_unit.py remains byte-identical. Only CI process bootstrapping
is adapted; actual argv/worker exits are recorded rather than fabricated.
"""
import argparse,ast,datetime,json,os,subprocess,sys,time,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();C=a.source_root.resolve();R=a.output_root;R.mkdir(mode=0o700,parents=True,exist_ok=False)
    tree=ast.parse((C/'validation/m6_mvp1/run_unit.py').read_bytes());cases=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cases' for t in n.targets)));assert len(cases)==len(set(cases))==34
    rows=[]
    for case in cases:
        argv=[sys.executable,'-I','-S','-B',str(C/'scripts/ci/r9_source_only.py'),'--source-root',str(C),'--script','validation/m6_mvp1/unit_worker.py','--',case,str(R/case)];t=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(argv,cwd=C,capture_output=True)
        (R/(case+'.stdout')).write_bytes(r.stdout);(R/(case+'.stderr')).write_bytes(r.stderr)
        path=R/case/'result.json';row=json.loads(path.read_text()) if path.exists() else {'id':'R9-UNIT-'+case,'status':'FAIL','diagnostic':'worker failed before result'}
        row.update(actual_test_process_exit=r.returncode,actual_argv=argv,started_utc=began,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,source_only_ci_bootstrap=True,original_worker_inputs_and_assertions_unchanged=True,actual_ros_child_exit='N/A: original simulated Session')
        rows.append(row);(R/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(row['id'],row['status'],r.returncode,flush=True)
        if r.returncode or row['status']!='PASS':break
    ok=len(rows)==34 and all(r['status']=='PASS' and r['actual_test_process_exit']==0 for r in rows)
    (R/'summary.json').write_text(json.dumps({'pass':ok,'actual':len(rows),'planned':34,'passed':sum(r['status']=='PASS' for r in rows),'failed':sum(r['status']!='PASS' for r in rows),'source_only_bootstrap':True,'no_test_assertion_or_case_list_or_round_change':True,'native_ros':False},indent=2)+'\n');return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
