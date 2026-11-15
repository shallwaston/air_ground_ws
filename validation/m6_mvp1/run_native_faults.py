"""Sequential real Linux/Jazzy injections, exact case exits, no auto retry."""
import datetime,json,os,sys,time
from pathlib import Path
C=Path(__file__).resolve().parents[2];sys.path.insert(0,str(C/'src/ag_network_tools'))
from ag_network_tools.isolated_runner import DirectChild
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False);records=[]
cases=['ready-loss','birth-mismatch','foreign-reaper-ignore','file-open','child-nonzero','foreign-reaper-takeover','signal-timeout','evidence-close']
for case in cases:
    argv=[sys._base_executable,'-I','-S','-B',str(Path(__file__).with_name('native_fault_worker.py')),case,str(root/case)]
    tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (root/(case+'.stdout')).open('wb') as out,(root/(case+'.stderr')).open('wb') as err:
        process=DirectChild(argv,stdout=out,stderr=err,stdin=__import__('subprocess').DEVNULL,cwd=C,env=os.environ.copy(),start_new_session=True)
        code=process.wait(timeout=45)
    record=json.loads((root/case/'result.json').read_text()) if (root/case/'result.json').exists() else {'id':'R9-NATIVE-FAULT-'+case,'status':'FAIL','diagnostic':'worker exited before result'}
    record.update(actual_test_worker_returncode=code,actual_test_worker_raw_wait_status=process.raw_wait_status,argv=argv,started_utc=start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),total_seconds=time.monotonic()-tick)
    records.append(record);(root/'results.json').write_text(json.dumps(records,indent=2)+'\n');print(record['id'],record['status'],code,flush=True)
    if code or record['status']!='PASS':break
ok=len(records)==len(cases) and all(r['status']=='PASS' and r['actual_test_worker_returncode']==0 for r in records)
(root/'summary.json').write_text(json.dumps({'pass':ok,'planned':len(cases),'actual':len(records),'passed':sum(r['status']=='PASS' for r in records),'failed':sum(r['status']=='FAIL' for r in records),'native_ros':True,'correct_rejection_not_normal_child_exit':True,'no_auto_retries':True},indent=2)+'\n');print('ARTIFACTS',root);raise SystemExit(0 if ok else 1)
