"""Every contract case owns a fresh interpreter; no quarantine reset/retry."""
import datetime,json,os,subprocess,sys,tempfile,time
from pathlib import Path
C=Path(__file__).resolve().parents[2]
cases=['normal','before-session','created-before-registration','partial-registration','ready-missing','ready-context','entry-mismatch','release-mismatch','early-exit','partial-factory-receipt','identity-mismatch','foreign-reaper','wrong-thread','wrong-creator-thread','concurrent-close','repeat-close','stop-failure','business-multiple-cleanup','borrowed-domain','borrowed-context','file-open-failure','file-close-failure','journal-write-failure','nonzero-child','timeout-ownership','second-child','repeat-acquire','unapproved-entry','after-release','false-close-success','missing-raw-wait','repeat-stop','receipt-consumed','none-release-pin']
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False);rows=[]
for case in cases:
 tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();argv=[sys.executable,'-B',str(Path(__file__).with_name('unit_worker.py')),case,str(root/case)]
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 result=subprocess.run(argv,cwd=C,env=env,capture_output=True)
 (root/(case+'.stdout')).write_bytes(result.stdout);(root/(case+'.stderr')).write_bytes(result.stderr)
 record=json.loads((root/case/'result.json').read_text()) if (root/case/'result.json').exists() else {'id':'R9-UNIT-'+case,'status':'FAIL','diagnostic':'worker failed before result'}
 record.update(actual_test_process_exit=result.returncode,argv=argv,started_utc=start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-tick,actual_ros_child_exit='N/A: simulated Session only')
 rows.append(record);(root/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(record['id'],record['status'],result.returncode,flush=True)
 if result.returncode or record['status']!='PASS':break
ok=len(rows)==len(cases) and all(r['status']=='PASS' and r['actual_test_process_exit']==0 for r in rows)
(root/'summary.json').write_text(json.dumps({'pass':ok,'planned':len(cases),'actual':len(rows),'passed':sum(r['status']=='PASS' for r in rows),'failed':sum(r['status']=='FAIL' for r in rows),'no_test_retries':True,'native_ros':False},indent=2)+'\n');print('ARTIFACTS',root);raise SystemExit(0 if ok else 1)
