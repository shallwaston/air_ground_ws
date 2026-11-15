#!/usr/bin/env python3
"""CI-only source bootstrap for unchanged R9 offline tests.

Retained heritage pyc files are data, never import authority. This is not a ROS
production entry, sender, reaper, signal manager or replacement console.
"""
import argparse,ast,hashlib,json,os,stat,sys
import importlib.abc,importlib.util
from pathlib import Path

RELEASE='b7d8299e006c4e9fc9e75dfd0db5da32abb7a48f26bf997083b1400136b32e3b'
SCRIPTS={'validation/m6_mvp1/unit_worker.py','validation/m6_mvp1/test_acquisition_receipt.py','validation/m6_mvp1/test_pipe_receipt.py','validation/m6_mvp1/test_dependency_review.py','validation/m6_mvp1/test_policy_identity.py'}
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
    s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid in (0,os.geteuid()) and not s.st_mode&0o022
    return path.read_bytes()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--script',choices=sorted(SCRIPTS),required=True);p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args();C=a.source_root.resolve(strict=True);P=C/'src/ag_network_tools/ag_network_tools'
    assert sys.flags.isolated and sys.flags.no_site and sys.flags.ignore_environment
    raw=read(P/'strict_assets/manifest.json');assert sha(raw)==RELEASE;manifest=json.loads(raw);sources={}
    for name,digest in manifest['network_sources'].items():
        assert Path(name).name==name and name.endswith('.py');data=read(P/name);assert sha(data)==digest;sources[name]=data
    ns={'__name__':'reviewed_release_contract','__file__':str(C/'scripts/ci/release_contract.py')};exec(compile((C/'scripts/ci/release_contract.py').read_bytes(),'reviewed_release_contract','exec'),ns);admitted=ns['contract'](C,verify_inert_bytecode=False)
    proof=admitted['origin'];golden={r['path']:r['sha256'] for r in proof['files']};script=C/a.script;data=read(script);assert sha(data)==golden[a.script]
    assert not any(n=='ag_network_tools' or n.startswith('ag_network_tools.') for n in sys.modules)
    class ReviewSources(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if fullname!='ag_network_tools' and not fullname.startswith('ag_network_tools.'):return None
            name='__init__.py' if fullname=='ag_network_tools' else fullname.removeprefix('ag_network_tools.')+'.py'
            if '/' in name or name not in sources or name=='node_runner.py':raise ImportError('CI source import outside approved strict test surface')
            spec=importlib.util.spec_from_loader(fullname,self,origin=str(P/name),is_package=fullname=='ag_network_tools');spec.loader_state=name;return spec
        def create_module(self,spec):return None
        def exec_module(self,module):
            name=module.__spec__.loader_state;module.__file__=str(P/name)
            if module.__spec__.submodule_search_locations is not None:module.__path__=[]
            exec(compile(sources[name],module.__file__,'exec'),module.__dict__)
    sys.meta_path.insert(0,ReviewSources());sys.dont_write_bytecode=True
    args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments;sys.argv=[str(script),*args]
    exec(compile(data,str(script),'exec'),{'__name__':'__main__','__file__':str(script)})
if __name__=='__main__':main()
