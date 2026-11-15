"""Verify the explicit reviewed R9 -> R10 one-LF release migration.

This module only checks data/source. It never generates a policy, manifest,
source ZIP, pin, launcher or runtime artifact.
"""
import ast,base64,copy,hashlib,io,json,os,stat,zipfile
from pathlib import Path
ORIGIN_RELEASE='7dc7ebc4a9a5c42f3dcbec6cf4e3bdfb240dcf16dac863370fee4c5e6fd5e8fa'
ORIGIN_POLICY='57bdb2f6e763310228d22f277ee606b934c9db07306523c4ff911a56ac4dc3c2'
RELEASE='b7d8299e006c4e9fc9e75dfd0db5da32abb7a48f26bf997083b1400136b32e3b'
POLICY='dad0eb9f807aacc2039e29e53db2f43a539c11353de05a15dfcb38594b1a028c'
PREFIX='src/ag_network_tools/ag_network_tools/'
DELTA={PREFIX+name for name in ['m6_fixed_heartbeat.py','_m6_mvp_policy.json','strict_dependency_gate.py','_strict_asset_pin.py','_strict_launcher_generated/ag_strict_isolated','strict_assets/source.zip','strict_assets/manifest.json']}
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
    s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid in (0,os.geteuid()) and not s.st_mode&0o022
    return path.read_bytes()
def contract(C,*,verify_inert_bytecode=True):
    C=Path(C);P=C/PREFIX;D=C/'docs/validation/r10';proof=json.loads(read(D/'r9-provenance.json'));migration=json.loads(read(D/'release-migration.json'));origin={r['path']:r for r in proof['files']}
    assert proof['r9_release_manifest_sha256']==ORIGIN_RELEASE and proof['r9_mvp_policy_sha256']==ORIGIN_POLICY
    assert migration['reviewed'] and migration['origin_r9_release']==ORIGIN_RELEASE and migration['r10_release']==RELEASE and migration['origin_r9_policy']==ORIGIN_POLICY and migration['r10_policy']==POLICY
    changes={r['path']:r for r in migration['approved_delta']};assert set(changes)==DELTA
    for path,row in changes.items():assert row['before_sha256']==origin[path]['sha256'] and sha(read(C/path))==row['after_sha256'] and (C/path).stat().st_size==row['after_bytes']
    old_fixed=base64.b64decode(read(D/'r9-origin/m6-fixed-heartbeat.base64').strip(),validate=True);new_fixed=read(P/'m6_fixed_heartbeat.py');assert sha(old_fixed)==origin[PREFIX+'m6_fixed_heartbeat.py']['sha256'] and old_fixed.endswith(b'\n\n') and new_fixed==old_fixed[:-1]
    assert ast.dump(ast.parse(old_fixed),include_attributes=False)==ast.dump(ast.parse(new_fixed),include_attributes=False)
    old_policy_raw=read(D/'r9-origin/mvp-policy.json');assert sha(old_policy_raw)==ORIGIN_POLICY;old_policy=json.loads(old_policy_raw);expected_policy=copy.deepcopy(old_policy);expected_policy['source_sha256']['m6_fixed_heartbeat.py']=sha(new_fixed)
    new_policy_raw=read(P/'_m6_mvp_policy.json');assert sha(new_policy_raw)==POLICY and json.loads(new_policy_raw)==expected_policy
    old_gate=read(D/'r9-origin/strict-dependency-gate.py.txt');new_gate=read(P/'strict_dependency_gate.py');assert sha(old_gate)==origin[PREFIX+'strict_dependency_gate.py']['sha256']
    marker=('MVP_POLICY_SHA256='+repr(ORIGIN_POLICY)).encode();assert old_gate.count(marker)==1 and new_gate==old_gate.replace(marker,('MVP_POLICY_SHA256='+repr(POLICY)).encode())
    old_raw=read(D/'r9-origin/release-manifest.json');assert sha(old_raw)==ORIGIN_RELEASE;old_manifest=json.loads(old_raw);expected_manifest=copy.deepcopy(old_manifest)
    updated={'ag_network_tools/m6_fixed_heartbeat.py':new_fixed,'ag_network_tools/strict_dependency_gate.py':new_gate}
    for name,data in updated.items():expected_manifest['members'][name]=sha(data);expected_manifest['network_sources'][Path(name).name]=sha(data)
    raw_zip=read(P/'strict_assets/source.zip');expected_manifest['files']['source.zip']=sha(raw_zip);expected_manifest['m6_mvp_policy_sha256']=POLICY
    raw=read(P/'strict_assets/manifest.json');assert sha(raw)==RELEASE and json.loads(raw)==expected_manifest
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        assert set(archive.namelist())==set(old_manifest['members']) and len(archive.namelist())==len(set(archive.namelist()))
        for name in archive.namelist():assert sha(archive.read(name))==(sha(updated[name]) if name in updated else old_manifest['members'][name])
    pin=ast.parse(read(P/'_strict_asset_pin.py'));assert len(pin.body)==1 and isinstance(pin.body[0],ast.Assign) and len(pin.body[0].targets)==1 and isinstance(pin.body[0].targets[0],ast.Name) and pin.body[0].targets[0].id=='MANIFEST_SHA256' and ast.literal_eval(pin.body[0].value)==RELEASE
    template=read(C/'src/ag_network_tools/scripts/ag_strict_isolated');assert sha(template)==old_manifest['launcher_template_sha256'] and template.count(b'__R8_BOUND_MANIFEST__')==1
    assert read(P/'_strict_launcher_generated/ag_strict_isolated')==template.replace(b'__R8_BOUND_MANIFEST__',RELEASE.encode())
    current=[]
    for original in proof['files']:
        row=copy.deepcopy(original)
        if row['path'] in changes:row['sha256']=changes[row['path']]['after_sha256'];row['bytes']=changes[row['path']]['after_bytes']
        # Static/native admission checks all frozen data. The CI-only source
        # loader can ignore the 44 inherited bytecode objects: it compiles
        # authenticated source bytes and never consults a bytecode loader.
        inert=Path(row['path']).suffix in ('.pyc','.pyo')
        if verify_inert_bytecode or not inert:assert sha(read(C/row['path']))==row['sha256']
        current.append(row)
    return {'origin':proof,'current_files':current,'release':RELEASE,'policy':POLICY,'origin_release':ORIGIN_RELEASE,'origin_policy':ORIGIN_POLICY,'only_fixed_source_one_lf_removed_ast_equal':True,'policy_scope_native_binaries_and_entry_presets_unchanged':True,'reviewed_generated_delta':sorted(DELTA),'frozen_inert_bytecode_verified':verify_inert_bytecode}
