#!/usr/bin/env python3
"""Build a fixed-source strict deployment capsule; no ROS process is started.

First build only ag_interfaces into a fresh prerequisite prefix, with
CMAKE_SKIP_RPATH=ON. Then run this script using the fixed Jazzy Python.
The final seven-package build installs these package_data assets and script.
"""
import argparse,ast,hashlib,io,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def literal(path,name):
    tree=ast.parse(path.read_bytes())
    n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    return ast.literal_eval(n.value)

def main():
    p=argparse.ArgumentParser();p.add_argument('--interface-prefix',type=Path,required=True);a=p.parse_args()
    if sys.version_info[:2]!=(3,12):raise RuntimeError('fixed Jazzy Python 3.12 required')
    C=Path(__file__).resolve().parents[1];P=C/'src/ag_network_tools/ag_network_tools'
    entries=literal(P/'isolated_entries.py','ENTRIES');messages=literal(P/'isolated_entries.py','INTERFACE_SOURCES')
    assert {q.name:sha(q.read_bytes()) for q in (C/'src/ag_interfaces/msg').glob('*.msg')}==messages
    old=P/'strict_assets'
    if old.exists():raise RuntimeError('asset destination exists; create a separately reviewed new build, do not overwrite')
    out=Path(tempfile.mkdtemp(prefix='.strict-assets-',dir=P))
    source=literal(P/'isolated_probe.py','C_SOURCE');(out/'probe.c').write_text(source)
    cc=Path(shutil.which('cc')).resolve();flags=['-shared','-fPIC','-O2','-pthread']
    subprocess.run([str(cc),*flags,str(out/'probe.c'),'-o',str(out/'probe.so')],check=True)
    prefix=a.interface_prefix.resolve();py=prefix/'lib/python3.12/site-packages/ag_interfaces'
    if not py.is_dir():raise RuntimeError('fresh generated interface prefix missing')
    members={};stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
        roots={'ag_network_tools':P,'ag_tf_tools':C/'src/ag_tf_tools/ag_tf_tools','ag_mock_nodes':C/'src/ag_mock_nodes/ag_mock_nodes','ag_interfaces':py}
        for package,root in roots.items():
            for path in sorted(root.rglob('*.py') if package=='ag_interfaces' else root.glob('*.py')):
                if '__pycache__' in path.parts or path.name in ('node_runner.py','_strict_asset_pin.py'):continue
                if package=='ag_tf_tools' and path.name not in ('__init__.py','tf_healthcheck.py'):continue
                if package=='ag_mock_nodes' and path.name not in ('__init__.py','heartbeat_pub.py','ugv_map_tile_sub.py'):continue
                name=package+'/'+str(path.relative_to(root));data=path.read_bytes();z.writestr(name,data);members[name]=sha(data)
    (out/'source.zip').write_bytes(stream.getvalue())
    libraries=['libag_interfaces__rosidl_generator_c.so','libag_interfaces__rosidl_typesupport_introspection_c.so','libag_interfaces__rosidl_typesupport_fastrtps_c.so','libag_interfaces__rosidl_typesupport_c.so','libag_interfaces__rosidl_generator_py.so']
    native=[]
    for name in libraries:
        source_path=prefix/'lib'/name;data=source_path.read_bytes();(out/name).write_bytes(data)
        info=subprocess.run(['readelf','-d',str(source_path)],check=True,capture_output=True,text=True).stdout
        if 'RUNPATH' in info or 'RPATH' in info:raise RuntimeError('capsule must not retain a build/install runpath')
        native.append({'file':name,'kind':'preload','dynamic_metadata':info})
    name='ag_interfaces_s__rosidl_typesupport_c.so';source_path=py/name;(out/name).write_bytes(source_path.read_bytes())
    info=subprocess.run(['readelf','-d',str(source_path)],check=True,capture_output=True,text=True).stdout
    if 'RUNPATH' in info or 'RPATH' in info:raise RuntimeError('Python interface extension retains a runpath')
    native.append({'file':name,'kind':'extension','module':'ag_interfaces.ag_interfaces_s__rosidl_typesupport_c','dynamic_metadata':info})
    manifest={'profile':'r7-strict-v1','entries':entries,'interface_sources':messages,'probe_c_source_sha256':sha(source.encode()),'compiler':{'path':str(cc),'sha256':sha(cc.read_bytes()),'flags':flags},'interpreter_sha256':sha(Path(sys._base_executable).resolve().read_bytes()),'network_sources':{p.name:sha(p.read_bytes()) for p in P.glob('*.py') if p.name!='_strict_asset_pin.py'},'members':members,'native':native,'files':{p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()},'interface_build_prefix':str(prefix),'native_abi':'fixed Jazzy linux/amd64, CMAKE_SKIP_RPATH=ON, controlled memfd preloads; no inherited native search path'}
    policy=P/'_m6_mvp_policy.json'
    if policy.exists():manifest['m6_mvp_policy_sha256']=sha(policy.read_bytes())
    template=(C/'src/ag_network_tools/scripts/ag_strict_isolated').read_bytes()
    manifest['launcher_template_sha256']=sha(template)
    raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode();(out/'manifest.json').write_bytes(raw)
    for p in out.iterdir():os.chmod(p,0o444)
    out.rename(old)
    (P/'_strict_asset_pin.py').write_text('MANIFEST_SHA256 = '+repr(sha(raw))+'\n')
    generated=P/'_strict_launcher_generated';generated.mkdir()
    if template.count(b'__R8_BOUND_MANIFEST__')!=1:raise RuntimeError('invalid bound launcher template')
    launcher=generated/'ag_strict_isolated';launcher.write_bytes(template.replace(b'__R8_BOUND_MANIFEST__',sha(raw).encode()));os.chmod(launcher,0o755)
    print(json.dumps({'asset_root':str(old),'manifest_sha256':sha(raw),'files':len(manifest['files']),'members':len(members)},indent=2))
if __name__=='__main__':main()
