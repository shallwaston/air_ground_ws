"""Real local file/reader controls and literal workflow boundaries, no ROS."""
import argparse,json,os,re,subprocess,sys,textwrap,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();R=a.output_root;R.mkdir(mode=0o700,parents=True,exist_ok=False)
    workflow=(a.source_root/'.github/workflows/m6-static.yml').read_text();code=textwrap.dedent(workflow.split('# R10_EXPORT_BEGIN\n',1)[1].split('# R10_EXPORT_END',1)[0]);rows=[]
    assert re.findall(r'uses: ([^\s#]+)',workflow)==['actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1','actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9']
    assert 'contents: read' in workflow and 'pull_request_target:' not in workflow and '${{ secrets.' not in workflow
    assert '--ci-required-sandbox' in workflow and '--reuid=65532' in workflow and '--bounding-set=-all' in workflow and '--no-new-privs' in workflow and '/usr/bin/env -i' in workflow
    assert 'persist-credentials: false' in workflow and 'fetch-depth: 0' in workflow and 'set-safe-directory: false' in workflow
    assert 'path: ${{ steps.sandbox.outputs.stage }}/export/ci-artifact.json' in workflow and 'path: ${{ steps.sandbox.outputs.stage }}/output/check/' not in workflow
    rows.append({'id':'R10-CI-workflow-profile','status':'PASS','no_ros_execution':True})
    good={'summary':{'pass':True,'native_ros_tests':'NOT EXECUTED'},'test':'owned synthetic evidence'}
    for case in ['regular','symlink','hardlink','fifo','oversize','schema','foreign-owner']:
        path=R/case
        if case=='regular':path.write_text(json.dumps(good))
        elif case=='symlink':
            target=R/'symlink-target';target.write_text(json.dumps(good));path.symlink_to(target)
        elif case=='hardlink':
            target=R/'hardlink-target';target.write_text(json.dumps(good));path.hardlink_to(target)
        elif case=='fifo':os.mkfifo(path)
        elif case=='oversize':
            with path.open('wb') as f:f.truncate(5*1024*1024+1)
        elif case=='schema':path.write_text('{"summary":{"pass":"fake"}}')
        elif case=='foreign-owner':
            path=Path('/etc/hosts');assert path.stat().st_uid!=os.geteuid()
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(path)],env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True)
        (R/(case+'.stdout')).write_bytes(result.stdout);(R/(case+'.stderr')).write_bytes(result.stderr)
        assert result.returncode==(0 if case=='regular' else 1)
        if case=='regular':assert json.loads(result.stdout)==good
        rows.append({'id':'R10-CI-export-'+case,'status':'PASS','actual_reader_exit_code':result.returncode,'expected_reader_exit_code':0 if case=='regular' else 1,'reader_uid':os.geteuid(),'github_uid65532_drop_not_claimed_by_local_test':True})
        if case=='fifo':path.unlink()  # this just-created empty input; diagnostic result remains
    # Execute the reviewed checker bytes, never a cached import. These inputs
    # are tiny owned filesystem fixtures, not alternate R9 production code.
    namespace={'__name__':'ci_control_source_review','__file__':str(a.source_root/'scripts/ci/m6_static.py')}
    exec(compile((a.source_root/'scripts/ci/m6_static.py').read_bytes(),'reviewed_static_checker','exec'),namespace)
    for kind in ['clean','startup-module','source-bytecode','extension-shadow','directory-symlink']:
        source=R/('import-'+kind)
        for name in ['src','scripts','validation']:(source/name).mkdir(parents=True)
        package=source/'src/ag_network_tools/ag_network_tools';package.mkdir(parents=True);(package/'__init__.py').write_text('')
        if kind=='startup-module':p=source/'validation/m6_mvp1/sitecustomize.py';p.parent.mkdir();p.write_text('raise AssertionError("must not execute")')
        elif kind=='source-bytecode':p=package/'__pycache__/__init__.cpython-312.pyc';p.parent.mkdir();p.write_bytes(b'not executed; rejected by path before import')
        elif kind=='extension-shadow':(package.parent/'math.so').write_bytes(b'not executed; rejected before native load')
        elif kind=='directory-symlink':
            target=R/'external-package';target.mkdir();(target/'__init__.py').write_text('raise AssertionError("must not execute")');(package.parent/'math').symlink_to(target,target_is_directory=True)
        try:namespace['source_import_surface'](source,{'files':[{'path':'src/ag_network_tools/ag_network_tools/__init__.py'}]});accepted=True
        except AssertionError:accepted=False
        assert accepted==(kind=='clean')
        rows.append({'id':'R10-CI-import-surface-'+kind,'status':'PASS','accepted':accepted,'no_fixture_code_executed':True})
    import hashlib,shutil,importlib.util,marshal,struct
    for kind in ['known-bytecode-data','tampered-known-bytecode']:
        source=R/kind
        for name in ['src','scripts','validation']:(source/name).mkdir(parents=True)
        p=source/'src/__pycache__/known.pyc';p.parent.mkdir();p.write_bytes(b'known frozen data; never executed')
        proof={'files':[{'path':'src/__pycache__/known.pyc','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
        if kind.startswith('tampered'):p.write_bytes(b'changed unapproved data')
        try:namespace['source_import_surface'](source,proof);accepted=True
        except AssertionError:accepted=False
        assert accepted==(kind=='known-bytecode-data')
        rows.append({'id':'R10-CI-import-surface-'+kind,'status':'PASS','accepted':accepted,'never_executed':True})
    fixture=R/'source-only-fixture';package=fixture/'src/ag_network_tools/ag_network_tools'
    # Copy the complete authenticated source/data inventory. Alter only the
    # deliberately poisoned inherited cache in this owned negative fixture.
    proof=json.loads((a.source_root/'docs/validation/r10/r9-provenance.json').read_text())
    for row in proof['files']:
        target=fixture/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.source_root/row['path'],target)
    proofpath=fixture/'docs/validation/r10/r9-provenance.json';proofpath.parent.mkdir(parents=True);shutil.copy2(a.source_root/'docs/validation/r10/r9-provenance.json',proofpath);(fixture/'scripts').mkdir(exist_ok=True)
    shutil.copytree(a.source_root/'docs/validation/r10/r9-origin',proofpath.parent/'r9-origin');shutil.copy2(a.source_root/'docs/validation/r10/release-migration.json',proofpath.parent/'release-migration.json');(fixture/'scripts/ci').mkdir();shutil.copy2(a.source_root/'scripts/ci/release_contract.py',fixture/'scripts/ci/release_contract.py')
    marker=R/'POISON_BYTECODE_EXECUTED';source=package/'__init__.py';cache=package/'__pycache__'/('__init__.'+sys.implementation.cache_tag+'.pyc');cache.parent.mkdir(exist_ok=True)
    payload=compile('from pathlib import Path\nPath('+repr(str(marker))+').write_text("actual valid bytecode executed in control")\n',str(source),'exec');cache.write_bytes(importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(source.stat().st_mtime)&0xffffffff,source.stat().st_size)+marshal.dumps(payload))
    control=subprocess.run([sys.executable,'-I','-S','-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import ag_network_tools',str(package.parent)],capture_output=True);assert control.returncode==0 and marker.is_file();marker.rename(R/'control-poison-bytecode-evidence.txt')
    # Same exact known release sources and valid poison cache; independent
    # source bootstrap must ignore it, even without the earlier CI precheck.
    argv=[sys.executable,'-I','-S','-B',str(a.source_root/'scripts/ci/r9_source_only.py'),'--source-root',str(fixture),'--script','validation/m6_mvp1/unit_worker.py','--','normal',str(R/'source-only-worker')]
    actual=subprocess.run(argv,capture_output=True);(R/'source-only-worker.stdout').write_bytes(actual.stdout);(R/'source-only-worker.stderr').write_bytes(actual.stderr)
    assert actual.returncode==0 and not marker.exists() and json.loads((R/'source-only-worker/result.json').read_text())['status']=='PASS'
    rows.append({'id':'R10-CI-source-only-valid-pyc-ignored','status':'PASS','actual_normal_import_control_exit':control.returncode,'control_executed_valid_poison':True,'actual_source_only_worker_exit':actual.returncode,'source_only_ignored_same_poison':True,'original_worker_assertions_inputs_unchanged':True,'original_normal_case_not_added_to_R9_unique_count':True})
    worker=a.source_root/'scripts/ci/m6_native_worker.py'
    result=subprocess.run([sys.executable,'-I','-S','-B',str(worker),'build','--output-root',str(R/'must-not-exist'),'--host-gate',str(R/'missing-gate'),'--host-gate-sha256','0'*64],env={'PATH':'/usr/bin:/bin'},capture_output=True)
    assert result.returncode==77 and not (R/'must-not-exist').exists();(R/'native-refusal.stderr').write_bytes(result.stderr)
    rows.append({'id':'R10-CI-native-worker-unauthorized','status':'PASS','actual_exit_code':77,'no_ros_or_docker_or_output_created':True})
    summary={'pass':True,'actual':len(rows),'passed':len(rows),'native_ros':False,'cases':rows};(R/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for row in rows:print(row['id'],'PASS',row.get('actual_reader_exit_code',row.get('actual_exit_code','in-process')))
    return 0
if __name__=='__main__':raise SystemExit(main())
