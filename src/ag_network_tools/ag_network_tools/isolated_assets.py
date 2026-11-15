"""Verify the installed deployment capsule before any child is spawned."""
import hashlib,io,json,os,stat,sys,zipfile
from pathlib import Path,PurePosixPath
from .isolated_entries import ENTRIES,INTERFACE_SOURCES
from .isolated_probe import C_SOURCE

def sha(b):return hashlib.sha256(b).hexdigest()
def ordinary(path):
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid not in (0,os.geteuid()) or s.st_mode&0o022:
        raise RuntimeError('untrusted deployment asset file: '+str(path))
    return path.read_bytes()

def load_assets(package):
    package=Path(package).resolve();root=package/'strict_assets'
    if root.is_symlink() or not root.is_dir():raise RuntimeError('installed strict assets are required')
    for p in [root,package]:
        s=p.stat()
        if s.st_uid not in (0,os.geteuid()) or s.st_mode&0o022:raise RuntimeError('writable deployment directory')
    pin=ordinary(package/'_strict_asset_pin.py').decode()
    import ast
    tree=ast.parse(pin)
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.Assign) or len(tree.body[0].targets)!=1 or not isinstance(tree.body[0].targets[0],ast.Name) or tree.body[0].targets[0].id!='MANIFEST_SHA256':raise RuntimeError('invalid generated deployment pin')
    expected=ast.literal_eval(tree.body[0].value)
    raw=ordinary(root/'manifest.json');manifest=json.loads(raw)
    if sha(raw)!=expected:raise RuntimeError('deployment manifest pin mismatch')
    if manifest['profile']!='r7-strict-v1' or manifest['interface_sources']!=INTERFACE_SOURCES or manifest['entries']!=ENTRIES:raise RuntimeError('deployment policy mismatch')
    if manifest['probe_c_source_sha256']!=sha(C_SOURCE.encode()):raise RuntimeError('probe source mismatch')
    exe=Path(sys._base_executable).resolve()
    if manifest['interpreter_sha256']!=sha(exe.read_bytes()):raise RuntimeError('deployment interpreter mismatch')
    for name,digest in manifest['network_sources'].items():
        if Path(name).name!=name or not name.endswith('.py'):raise RuntimeError('invalid source pin path')
        if sha(ordinary(package/name))!=digest:raise RuntimeError('deployed Python source differs from release capsule: '+name)
    if 'm6_mvp_policy_sha256' in manifest:
        if sha(ordinary(package/'_m6_mvp_policy.json'))!=manifest['m6_mvp_policy_sha256']:raise RuntimeError('MVP policy differs from deployment release')
    files={}
    for name,digest in manifest['files'].items():
        if Path(name).name!=name:raise RuntimeError('invalid asset path')
        data=ordinary(root/name)
        if sha(data)!=digest:raise RuntimeError('deployment asset checksum mismatch: '+name)
        files[name]=data
    with zipfile.ZipFile(io.BytesIO(files['source.zip'])) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(manifest['members']):raise RuntimeError('deployment source inventory mismatch')
        for n in names:
            p=PurePosixPath(n)
            if p.is_absolute() or '..' in p.parts or not n.endswith('.py') or stat.S_ISLNK(z.getinfo(n).external_attr>>16):raise RuntimeError('unsafe capsule source member')
            if sha(z.read(n))!=manifest['members'][n]:raise RuntimeError('deployment source hash mismatch')
        for entry in ENTRIES.values():
            path=entry['module'].replace('.','/')+'.py'
            if manifest['members'].get(path)!=entry['source_sha256']:raise RuntimeError('entry differs from reviewed baseline')
    return {'root':root,'manifest':manifest,'manifest_sha256':expected,'files':files}
