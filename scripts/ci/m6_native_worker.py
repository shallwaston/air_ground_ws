#!/usr/bin/env python3
"""Operator-only native worker, not a deployed GitHub Actions job.

It never invokes Docker, starts/replaces a container, changes image, pulls,
installs dependencies, deletes build/history, edits source/pins or runs G5.
A separately trusted host supervisor owns exact-container admission, exclusive
flock, full namespace scans between phases and final safe container stopping.
The gate JSON is that supervisor's receipt, not a cryptographic process proof.
"""
import argparse,datetime,hashlib,json,os,shlex,stat,subprocess,sys,time,traceback
from pathlib import Path

CID='a726e9d27fc88c3c01ad64379cd230c38208e4aadfbf5c595392353e987d79b2'
IMAGE='sha256:3e1ba97a2cda53301c6ba7e831e2c8506e54631f911c0bd26cfbc976479810c7'
RELEASE='b7d8299e006c4e9fc9e75dfd0db5da32abb7a48f26bf997083b1400136b32e3b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['build','collect','regress','mvp-positive','mvp-faults']);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--host-gate',type=Path,required=True);p.add_argument('--host-gate-sha256',required=True);a=p.parse_args()
    if os.environ.get('R10_NATIVE_AUTHORIZED')!='1':print('Native worker refused: separate controlled-host authorization required',file=sys.stderr);return 77
    C=Path(__file__).resolve().parents[2];R=a.output_root.resolve();gate=a.host_gate.resolve(strict=True);s=gate.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==os.getuid()==1000 and os.getgid()==1000
    assert sha(gate)==a.host_gate_sha256
    receipt=json.loads(gate.read_text());assert receipt['pass'] and receipt['container_id']==CID and receipt['image_id']==IMAGE and receipt['source']==str(C) and receipt['release']==RELEASE
    assert receipt['exclusive_lock_held'] and receipt['full_namespace_admitted'] and receipt['external_supervisor_retains_container_ownership']
    assert sys.version_info[:2]==(3,12) and Path('/opt/ros/jazzy/setup.bash').is_file()
    assert os.environ.get('ROS_DOMAIN_ID')=='42' and os.environ.get('RMW_IMPLEMENTATION')=='rmw_fastrtps_cpp' and os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')=='LOCALHOST'
    for key in ['SSL_CERT_FILE','REQUESTS_CA_BUNDLE','PIP_CERT']:assert os.environ[key]=='/run/cloud-ca.pem'
    assert not R.is_relative_to(C) and str(R).startswith('/workspace/')
    ns={'__name__':'reviewed_release_contract','__file__':str(C/'scripts/ci/release_contract.py')};exec(compile((C/'scripts/ci/release_contract.py').read_bytes(),'reviewed_release_contract','exec'),ns);admitted=ns['contract'](C)
    proof=admitted['origin'];current_files=admitted['current_files'];assert admitted['release']==RELEASE
    for row in current_files:assert sha(C/row['path'])==row['sha256']
    for name,digest in proof['validation_only_transport'].items():assert sha(C/'validation/regression_transport'/name)==digest
    if a.phase=='build':
        assert not any((C/name).exists() for name in ['build','install','log']);R.mkdir(mode=0o700,parents=True,exist_ok=False);save(R/'admission.json',{'gate_sha256':a.host_gate_sha256,'release':RELEASE,'source':str(C),'started_utc':now()})
    else:assert R.is_dir() and json.loads((R/'admission.json').read_text())['gate_sha256']==a.host_gate_sha256
    Q=shlex.quote;prefix='set -e; unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH; export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; source /opt/ros/jazzy/setup.bash; '
    overlay=prefix+'source '+Q(str(C/'install/local_setup.bash'))+'; cd '+Q(str(C))+'; '
    commands=[];primary=None;started=now();tick=time.monotonic();env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',ROS_HOME=str(R/'ros-home'),PYTHONPYCACHEPREFIX=str(R/'pycache'))
    def run(name,command):
        began=now();t=time.monotonic();r=subprocess.run(['bash','--noprofile','--norc','-c',command],env=env,capture_output=True)
        (R/(name+'.stdout')).write_bytes(r.stdout);(R/(name+'.stderr')).write_bytes(r.stderr);commands.append({'name':name,'argv':['bash','--noprofile','--norc','-c',command],'started_utc':began,'ended_utc':now(),'seconds':time.monotonic()-t,'actual_exit_code':r.returncode})
        save(R/(a.phase+'-commands.json'),commands);print(r.stdout.decode(errors='replace')[-18000:],flush=True)
        if r.returncode:print(r.stderr.decode(errors='replace')[-18000:],flush=True);raise RuntimeError(name+' failed, no dependent phase authorized')
        return r
    try:
        if a.phase=='build':
            build=run('seven-package-build',prefix+'cd '+Q(str(C))+'; ./scripts/build_ws.sh --parallel-workers 2')
            packages=sorted(p.parent.name for p in (C/'src').glob('*/package.xml'));assert len(packages)==7 and all(('Finished <<< '+name+' ') in build.stdout.decode() for name in packages)
            run('installation-check',overlay+'python3 -B '+Q(str(C/'validation/native_helpers/installation_check.py'))+' '+Q(str(R/'installation-check.json')))
        elif a.phase=='collect':
            assert json.loads((R/'build-result.json').read_text())['pass'];data=run('collect-original283',overlay+'python3 -B -m pytest src -p no:cacheprovider --collect-only -q')
            ids=[s.strip().split('/test/',1)[-1] for s in data.stdout.decode().splitlines() if '::test_' in s and not s.startswith(' ')]
            expected=json.loads((C/'docs/validation/r1-baseline/evidence-index.json').read_text())['unique_test_ids'];assert len(ids)==len(set(ids))==283 and set(ids)==set(expected);save(R/'collection.json',{'ids':ids,'count':283,'same_original_ids':True,'not_a_test_pass':True})
        elif a.phase=='regress':
            assert json.loads((R/'collect-result.json').read_text())['pass']
            transport='export R4_OWNED_SIGNAL_TRANSPORT=1 R4_SIGNAL_AUDIT='+Q(str(R/'signal-audit'))+'; export PYTHONPATH='+Q(str(C/'validation/regression_transport'))+':"${PYTHONPATH:-}"; '
            run('original-native283',overlay+transport+'python3 -B -m pytest src -p no:cacheprovider -vv -s --junitxml='+Q(str(R/'native-regression.xml'))+' --basetemp='+Q(str(R/'pytest-tmp')))
            import xml.etree.ElementTree as ET
            cases=list(ET.parse(R/'native-regression.xml').getroot().iter('testcase'));assert len(cases)==283 and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in cases)
            save(R/'native283-results.json',{'pass':True,'unique_original_ids':283,'cases':[{'class':c.attrib.get('classname'),'name':c.attrib['name'],'seconds':c.attrib.get('time'),'status':'PASS'} for c in cases],'host89_and_native141_are_subsets':True,'release':RELEASE})
        elif a.phase=='mvp-positive':
            assert json.loads((R/'regress-result.json').read_text())['pass'];run('production-heartbeat',overlay+'python3 -I -S -B '+Q(str(C/'validation/m6_mvp1/native_heartbeat.py'))+' '+Q(str(R/'mvp-positive')));assert json.loads((R/'mvp-positive/summary.json').read_text())['pass']
        elif a.phase=='mvp-faults':
            assert json.loads((R/'mvp-positive-result.json').read_text())['pass'];run('native-negative8',overlay+'python3 -B '+Q(str(C/'validation/m6_mvp1/run_native_faults.py'))+' '+Q(str(R/'mvp-faults')));assert json.loads((R/'mvp-faults/summary.json').read_text())['pass']
        for row in current_files:assert sha(C/row['path'])==row['sha256']
    except BaseException as error:primary=error
    result={'pass':primary is None,'phase':a.phase,'started_utc':started,'ended_utc':now(),'seconds':time.monotonic()-tick,'commands':commands,'exact_r9_source_and_release':RELEASE,'github_native_ci':'NOT DEPLOYED','standalone_g5':'NOT EXECUTED','gate_receipt_is_not_independent_process_proof':True}
    if primary:result.update(exception=repr(primary),traceback=''.join(traceback.format_exception(primary)));print(result['traceback'],flush=True)
    save(R/(a.phase+'-result.json'),result);print('NATIVE_PHASE_RESULT '+json.dumps({k:v for k,v in result.items() if k not in ('commands','traceback')},sort_keys=True),flush=True);return 0 if primary is None else 1
if __name__=='__main__':raise SystemExit(main())
