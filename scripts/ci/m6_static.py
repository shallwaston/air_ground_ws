#!/usr/bin/env python3
"""Non-ROS admission on the reviewed R9/R10 overlay; no native results claimed.

GitHub mode requires an externally prepared nonprivileged, no-network PID/mount
namespace. Local review mode is labelled separately and cannot claim that mode.
"""
import argparse,ast,datetime,hashlib,io,json,os,re,stat,subprocess,sys,time,traceback,zipfile
from pathlib import Path,PurePosixPath

BASE='2781146abcebf04d9470eb9627098be077cbb2ee'
RELEASE='b7d8299e006c4e9fc9e75dfd0db5da32abb7a48f26bf997083b1400136b32e3b'
POLICY='dad0eb9f807aacc2039e29e53db2f43a539c11353de05a15dfcb38594b1a028c'
LEGACY='6261934716b96410414c2c8aeae56ef303532b7201c365fdb583a93eda2d75cd'

def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def literal(path,name):
    tree=ast.parse(path.read_bytes())
    return ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))
def plain(path):
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid not in (0,os.geteuid()) or s.st_mode&0o022:raise RuntimeError('untrusted regular source/asset: '+str(path))
    return path.read_bytes()
def profile(required):
    status={r.split(':',1)[0]:r.split(':',1)[1].strip() for r in Path('/proc/self/status').read_text().splitlines() if ':' in r}
    result={'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'no_new_privileges':status.get('NoNewPrivs'),'capabilities':{k:status.get(k) for k in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']},'network_interfaces':sorted(line.split(':',1)[0].strip() for line in Path('/proc/self/net/dev').read_text().splitlines()[2:] if ':' in line),'docker_socket_present':Path('/var/run/docker.sock').exists(),'credential_environment_names':[k for k in os.environ if k.endswith(('_TOKEN','_SECRET','_PASSWORD')) or k in ('GITHUB_TOKEN','GH_TOKEN','SSH_AUTH_SOCK')],'required':required}
    if required:
        assert result['uid']==result['gid']==65532 and result['groups']==[]
        assert result['no_new_privileges']=='1' and all(int(v,16)==0 for v in result['capabilities'].values())
        assert result['network_interfaces']==['lo'] and not result['docker_socket_present'] and not result['credential_environment_names']
    result['sandbox']='ENFORCED' if required else 'NOT EXECUTED: local review profile';return result

def source_import_surface(C,proof):
    golden={r['path']:r for r in proof['files']}
    allowed=set(golden)|{'scripts/ci/m6_static.py','scripts/ci/m6_native_worker.py','scripts/ci/r9_source_only.py','scripts/ci/r9_unit_orchestrator.py','scripts/ci/release_contract.py','validation/ci_controls.py','validation/native_helpers/installation_check.py','validation/regression_transport/sitecustomize.py','validation/regression_transport/owned_child.py'}
    historical_cache_dirs={str(Path(name).parent) for name in golden if '__pycache__' in name and name.endswith(('.pyc','.pyo'))}
    checked=0;cached=0
    for root in [C/'src',C/'scripts',C/'validation']:
        assert root.is_dir() and not root.is_symlink()
        for path in root.rglob('*'):
            rel=str(path.relative_to(C));assert not path.is_symlink(),('source import symlink refused',str(path))
            if path.is_dir():
                if path.name=='__pycache__':assert rel in historical_cache_dirs,('unknown source cache directory',rel)
                continue
            if path.suffix in ('.pyc','.pyo') or '__pycache__' in path.parts:
                assert rel in golden and sha(plain(path))==golden[rel]['sha256'],('unapproved/tampered source bytecode',rel)
                cached+=1;continue
            if path.suffix in ('.py','.so','.pyd','.pth'):
                assert rel in allowed,('unapproved importable addition',str(path));checked+=1
    return {'admitted_importable_files':checked,'historical_bytecode_data_files':cached,'bytecode_execution':'DENIED by CI source-only bootstrap','unapproved_or_tampered_importable_additions':'DENIED','source_symlinks':'DENIED'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--ci-required-sandbox',action='store_true');args=parser.parse_args()
    C=args.source_root.resolve(strict=True);R=args.output_root.resolve();assert not R.is_relative_to(C);R.mkdir(mode=0o700,parents=True,exist_ok=False)
    records=[];commands=[];start=now();tick=time.monotonic();P=C/'src/ag_network_tools/ag_network_tools'
    env={k:os.environ[k] for k in ['PATH','LANG','LC_ALL','HOME','TMPDIR'] if k in os.environ};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null')
    G=['git','-c','safe.directory='+str(C),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','gc.auto=0']
    def check(name,function):
        began=now();t=time.monotonic()
        try:detail=function();row={'id':'R10-STATIC-'+name,'status':'PASS','detail':detail}
        except BaseException as error:
            row={'id':'R10-STATIC-'+name,'status':'FAIL','exception':repr(error),'traceback':''.join(traceback.format_exception(error))};records.append({**row,'started_utc':began,'ended_utc':now(),'seconds':time.monotonic()-t});save(R/'checks.json',records);raise
        records.append({**row,'started_utc':began,'ended_utc':now(),'seconds':time.monotonic()-t});save(R/'checks.json',records);print(row['id'],'PASS',flush=True);return detail
    def run(name,argv,expected=0):
        t=time.monotonic();began=now();r=subprocess.run(argv,cwd=C,env=env,capture_output=True)
        (R/(name+'.stdout')).write_bytes(r.stdout);(R/(name+'.stderr')).write_bytes(r.stderr)
        commands.append({'name':name,'argv':argv,'started_utc':began,'ended_utc':now(),'seconds':time.monotonic()-t,'actual_exit_code':r.returncode,'expected_exit_code':expected});save(R/'commands.json',commands)
        print(r.stdout.decode(errors='replace')[-16000:],flush=True)
        if r.returncode!=expected:print(r.stderr.decode(errors='replace')[-16000:],flush=True);raise RuntimeError(name+' actual exit '+str(r.returncode))
        return r
    def requirement(value,detail):assert value;return detail
    primary=None;groups={};selected_profile=None
    try:
        selected_profile=check('execution-profile',lambda:profile(args.ci_required_sandbox))
        if args.ci_required_sandbox:check('source-not-writable',lambda:requirement(not os.access(P/'m6_owned_session.py',os.W_OK),'root-owned admitted input is readonly to UID65532'))
        ns={'__name__':'reviewed_release_contract','__file__':str(C/'scripts/ci/release_contract.py')};exec(compile((C/'scripts/ci/release_contract.py').read_bytes(),'reviewed_release_contract','exec'),ns);admitted=ns['contract'](C)
        proof=admitted['origin'];current_files=admitted['current_files']
        check('fixed-provenance',lambda:requirement(proof['r3_base']==BASE and admitted['release']==RELEASE and admitted['policy']==POLICY and admitted['only_fixed_source_one_lf_removed_ast_equal'],'fixed reviewed R3/R9 identities'))
        def exact_source():
            assert len(proof['files'])==276 and len({r['path'] for r in proof['files']})==276
            for row in current_files:
                p=PurePosixPath(row['path']);assert not p.is_absolute() and '..' not in p.parts
                assert sha(plain(C/p))==row['sha256'] and (C/p).stat().st_size==row['bytes']
            return {'r9_files_accounted':276,'original_files_byte_identical':269,'explicit_reviewed_release_delta_files':7,'single_lf_ast_equal':True,'mode_policy':'Git executable bit and no group/world write; original exact archive modes recorded in R9 backup'}
        check('all-r9-source-and-assets',exact_source)
        check('source-import-surface',lambda:source_import_surface(C,proof))
        run('git-diff-check',G+['diff','--no-ext-diff','--no-textconv','--check',BASE,'HEAD']);run('git-working-diff-check',G+['diff','--no-ext-diff','--no-textconv','--check'])
        def syntax():
            result=[]
            for root in [C/'src',C/'scripts',C/'validation']:
                for p in sorted(root.rglob('*.py')):
                    if '__pycache__' in p.parts or any(x.endswith('.egg-info') for x in p.parts):continue
                    b=plain(p);compile(ast.parse(b,filename=str(p)),str(p),'exec');result.append(str(p.relative_to(C)))
            return {'files':result,'count':len(result)}
        check('python-ast-and-compile',syntax)
        check('mvp-policy-pin',lambda:requirement(sha(plain(P/'_m6_mvp_policy.json'))==POLICY,'exact reviewed policy, not automatically regenerated'))
        namespace={'__name__':'reviewed_mvp_checker','__file__':str(P/'strict_dependency_gate.py')};exec(compile(plain(P/'strict_dependency_gate.py'),str(P/'strict_dependency_gate.py'),'exec'),namespace)
        check('closed-mvp-dependency-graph',lambda:namespace['audit_mvp_package'](P))
        def artifact():
            raw=plain(P/'strict_assets/manifest.json');assert sha(raw)==RELEASE;manifest=json.loads(raw)
            assert literal(P/'_strict_asset_pin.py','MANIFEST_SHA256')==RELEASE
            assert manifest['entries']==literal(P/'isolated_entries.py','ENTRIES') and manifest['interface_sources']==literal(P/'isolated_entries.py','INTERFACE_SOURCES')
            assert manifest['m6_mvp_policy_sha256']==POLICY
            for name,digest in manifest['network_sources'].items():assert Path(name).name==name and sha(plain(P/name))==digest
            for name,digest in manifest['files'].items():assert Path(name).name==name and sha(plain(P/'strict_assets'/name))==digest
            with zipfile.ZipFile(io.BytesIO(plain(P/'strict_assets/source.zip'))) as z:
                assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(manifest['members'])
                assert 'ag_network_tools/node_runner.py' not in z.namelist()
                for name,digest in manifest['members'].items():
                    assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and name.endswith('.py') and sha(z.read(name))==digest
            return {'manifest':RELEASE,'zip_source_members':len(manifest['members']),'native_files_byte_integrity':'PASS','native_abi_execution':'NOT EXECUTED: requires fixed Jazzy image','no_pin_generation':True}
        check('release-and-source-capsule',artifact)
        def bound_launcher():
            template=plain(C/'src/ag_network_tools/scripts/ag_strict_isolated');bound=plain(P/'_strict_launcher_generated/ag_strict_isolated')
            assert template.count(b'__R8_BOUND_MANIFEST__')==1 and bound==template.replace(b'__R8_BOUND_MANIFEST__',RELEASE.encode())
            assert bound.startswith(b'#!/usr/bin/python3 -IS\n')
            return {'source_only_bound_entry':True,'alias_not_added':True,'no_ambient_overlay':True}
        check('bound-source-only-launcher',bound_launcher)
        def legacy_isolation():
            assert sha(plain(P/'node_runner.py'))==LEGACY
            assert set(p.name for p in P.glob('m6_*.py'))=={'m6_owned_session.py','m6_fixed_heartbeat.py'}
            resource=ast.parse(plain(P/'isolated_resources.py'));assert not any(isinstance(n,ast.ImportFrom) and n.module and 'node_runner' in n.module for n in ast.walk(resource))
            for filename in ['m6_owned_session.py','m6_fixed_heartbeat.py']:
                t=ast.parse(plain(P/filename))
                assert not any(isinstance(n,ast.ImportFrom) and n.module and 'node_runner' in n.module for n in ast.walk(t))
                assert not any(isinstance(n,ast.Name) and n.id=='_stop_signals' for n in ast.walk(t))
            runtime=plain(P/'isolated_runtime.py');assert b"origin='strict-approved-entry-bridge'" in runtime and b"bridge.run_node=strict_driver" in runtime and b"if node_type is not approved_class" in runtime
            return {'mvp_legacy_bypass':'DENIED','child_legacy_source':'ABSENT','original21_legacy_consoles':'RETAINED, not certified S1 safe','legacy_s1':'BLOCKED/UNCHANGED'}
        check('legacy-isolation-only-in-strict-graph',legacy_isolation)
        def entries():
            current={}
            for setup in sorted((C/'src').glob('*/setup.py')):
                for n in ast.walk(ast.parse(plain(setup))):
                    if isinstance(n,ast.keyword) and n.arg=='entry_points':current[setup.parent.name]=ast.literal_eval(n.value)['console_scripts'];break
                else:current[setup.parent.name]=[]
            assert current==proof['original21_entrypoints'] and sum(map(len,current.values()))==21
            return {'console_count':21,'unchanged_targets':True,'new_mvp_is_explicit_api':True}
        check('original21-entrypoints',entries)
        def packages():
            import xml.etree.ElementTree as ET
            info={}
            for path in sorted((C/'src').glob('*/package.xml')):
                t=ET.fromstring(plain(path));name=t.findtext('name');typ=t.findtext('export/build_type');assert typ==('ament_cmake' if name=='ag_interfaces' else 'ament_python')
                info[name]={'type':typ,'dependencies':sorted({n.text for n in t if n.tag.endswith('depend')})}
            done=[];active=set()
            def visit(name):
                assert name not in active
                if name in done:return
                active.add(name)
                for dep in info[name]['dependencies']:
                    if dep in info:visit(dep)
                active.remove(name);done.append(name)
            for name in info:visit(name)
            assert len(info)==7;return {'packages':info,'order':done,'cycle':False}
        check('seven-package-xml-and-dependency-dag',packages)
        def original_ids():
            data=json.loads(plain(C/'docs/validation/r10/oracle-index.json'));groups=data['groups'];ids=[i for g in groups.values() for i in g['ids']]
            assert len(ids)==len(set(ids))==211
            assert sum(g['count'] for k,g in groups.items() if k.startswith('r6_'))==72 and sum(g['count'] for k,g in groups.items() if k.startswith('r7_'))==66 and sum(g['count'] for k,g in groups.items() if k.startswith('r8_'))==73
            baseline=json.loads(plain(C/'docs/validation/r1-baseline/evidence-index.json'))['unique_test_ids'];assert len(baseline)==len(set(baseline))==283
            return {'r6':72,'r7':66,'r8':73,'original_ros_unique_ids':283,'execution':'NOT EXECUTED in non-ROS CI; exact ID/provenance review only'}
        check('historical-oracle-id-integrity',original_ids)
        for label,filename,count in [('unit','run_unit.py',34),('acquisition','test_acquisition_receipt.py',3),('partial-pipe','test_pipe_receipt.py',1),('dependency','test_dependency_review.py',15),('policy','test_policy_identity.py',6)]:
            destination=R/label
            argv=([sys.executable,'-I','-S','-B',str(C/'scripts/ci/r9_unit_orchestrator.py'),'--source-root',str(C),'--output-root',str(destination)] if label=='unit' else [sys.executable,'-I','-S','-B',str(C/'scripts/ci/r9_source_only.py'),'--source-root',str(C),'--script','validation/m6_mvp1/'+filename,'--',str(destination)])
            run('offline-'+label,argv)
            summary=json.loads((destination/'summary.json').read_text());rows=json.loads((destination/'results.json').read_text());assert summary['pass'] and len(rows)==count and all(r['status']=='PASS' for r in rows)
            groups[label]={'count':count,'summary':summary,'ids':[r['id'] for r in rows],'actual_suite_exit_code':0,'native_ros':False,'results_sha256':sha((destination/'results.json').read_bytes())}
        assert sum(g['count'] for g in groups.values())==59
        run('ci-controls',[sys.executable,'-I','-S','-B',str(C/'validation/ci_controls.py'),'--source-root',str(C),'--output-root',str(R/'ci-controls')])
        assert json.loads((R/'ci-controls/summary.json').read_text())['pass']
        if args.ci_required_sandbox:
            pids=sorted(int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit());check('no-residual-processes',lambda:requirement(pids==[os.getpid()],{'visible_pids':pids,'self':os.getpid(),'unknown_children':False}))
    except BaseException as error:primary=error
    result={'pass':primary is None,'started_utc':start,'ended_utc':now(),'seconds':time.monotonic()-tick,'profile':selected_profile,'source_root':str(C),'fixed_release_manifest':RELEASE,'checks':records,'offline_r9_cases':groups,'offline_count':sum(g['count'] for g in groups.values()),'native_ros_tests':'NOT EXECUTED','native_ros_ci':'NOT DEPLOYED','g5':'NOT EXECUTED','legacy_s1':'BLOCKED/UNCHANGED','branch_protection_enforcement':'NOT CONFIGURED by this workflow','no_ros_skips_counted_as_pass':True}
    if primary:result.update(exception=repr(primary),traceback=''.join(traceback.format_exception(primary)));print(result['traceback'],flush=True)
    save(R/'summary.json',result)
    # One bounded data object, read/exported later by a separate unprivileged
    # literal workflow command. Never give a host uploader an untrusted tree.
    evidence={'summary':result,'commands':commands,'offline_records':{label:json.loads((R/label/'results.json').read_text()) for label in groups},'r10_ci_control_records':json.loads((R/'ci-controls/results.json').read_text()) if (R/'ci-controls/results.json').exists() else [],'command_logs':{c['name']:{'stdout':(R/(c['name']+'.stdout')).read_text(errors='replace'),'stderr':(R/(c['name']+'.stderr')).read_text(errors='replace')} for c in commands}}
    save(R/'ci-artifact.json',evidence)
    print('M6_STATIC_RESULT '+json.dumps({k:v for k,v in result.items() if k not in ['checks','offline_r9_cases','traceback']},sort_keys=True),flush=True);return 0 if primary is None else 1
if __name__=='__main__':raise SystemExit(main())
