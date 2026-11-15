"""Fail-closed admission for the deliberately small MVP client grammar.

This is a CI/deployment source checker, not a Python sandbox. Only immutable,
reviewed source checked here may be executed by a trusted deployment driver.
The runtime release/entry/native and process ownership gates remain mandatory.
"""
import argparse
import ast
import hashlib
import json
import re
import stat
from pathlib import Path

FACADE = 'ag_network_tools.strict_entry'
FACTORY = FACADE + '.create_session'
PROFILE = 'm6-s1-mvp-direct-single-heartbeat-v1'
ALLOWED_ENTRIES = ('heartbeat_pub',)

# Exact-source exception cleanup template. This is an admission grammar,
# not a new M6 module or a generic resource-management implementation.
CLIENT_BODY = "def supervise(output, release_pin):\n    owned = factory('heartbeat_pub', output, expected_manifest_sha256=release_pin)\n    primary = None\n    errors = []\n    result = None\n    try:\n        owned.start()\n        owned.query(5)\n        owned.request_stop(2)\n        result = owned.wait(10)\n    except BaseException as error:\n        primary = error\n        try:\n            owned.abort_failed_supervision('MVP operation failed')\n        except BaseException as cleanup:\n            errors.append(cleanup)\n    try:\n        owned.close()\n    except BaseException as cleanup:\n        errors.append(cleanup)\n    if errors:\n        combined = BaseExceptionGroup('MVP operation and cleanup failed', ([primary] if primary is not None else []) + errors)\n        combined.supervision = owned\n        raise combined\n    if primary is not None:\n        raise primary.with_traceback(primary.__traceback__)\n    return result\n"

class AdmissionError(ValueError):
    pass

def audit_sources(sources, entry_module):
    """Admit alias/re-export imports and one fixed, owned-session function.

    No executable module initialization, imports inside functions, arbitrary
    dependencies, reflection, dynamic dispatch, session rebinding or arbitrary
    arguments. The accepted function is supervise(output, release_pin).
    """
    if entry_module not in sources:
        raise AdmissionError('entry module not supplied')
    trees = {}
    for name, text in sources.items():
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', name):
            raise AdmissionError('invalid closed module name')
        trees[name] = ast.parse(text, filename=name + '.py')
    symbols, loading, edges, functions = {}, set(), [], {}
    def imports(module):
        if module in symbols:
            return symbols[module]
        if module in loading:
            raise AdmissionError('module dependency cycle')
        loading.add(module)
        bound = {}
        def bind(name, target):
            reserved={'output','release_pin','owned','primary','errors','result','error','cleanup','combined','supervise','BaseException','BaseExceptionGroup'}
            if name.startswith('_') or name in reserved:
                raise AdmissionError('import alias shadows client lifecycle or exception bindings')
            if name in bound:
                raise AdmissionError('import alias rebinding')
            bound[name] = target
        for node in trees[module].body:
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    raise AdmissionError('relative import resolution unsupported')
                if node.module == FACADE:
                    exports = {'create_session': FACTORY}
                elif node.module in sources:
                    exports = imports(node.module)
                else:
                    raise AdmissionError('unapproved dependency: ' + str(node.module))
                for alias in node.names:
                    if alias.name not in exports:
                        raise AdmissionError('unknown/wildcard re-export')
                    bind(alias.asname or alias.name, exports[alias.name])
                edges.append({'from': module, 'to': node.module})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name != FACADE or not alias.asname:
                        raise AdmissionError('only explicit canonical module aliases admitted')
                    bind(alias.asname, FACADE)
                    edges.append({'from': module, 'to': FACADE})
            elif isinstance(node, ast.Assign):
                if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name) or node.targets[0].id != '__all__':
                    raise AdmissionError('module side effects/rebinding unsupported')
                value = ast.literal_eval(node.value)
                if not isinstance(value, list) or not all(isinstance(x, str) and x in bound for x in value):
                    raise AdmissionError('invalid explicit exports')
                bound = {name: bound[name] for name in value}
            elif isinstance(node, ast.FunctionDef):
                if module != entry_module or node.name != 'supervise' or module in functions or node.name in bound:
                    raise AdmissionError('only one reviewed entry function admitted')
                functions[module] = node
            elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                raise AdmissionError('unreviewed module initialization')
        loading.remove(module)
        symbols[module] = bound
        return bound
    for module in sources:
        imports(module)
    if entry_module not in functions:
        raise AdmissionError('entry supervise function absent')
    fn, bound = functions[entry_module], symbols[entry_module]
    args = fn.args
    if fn.decorator_list or fn.returns or args.posonlyargs or args.kwonlyargs or args.defaults or args.kw_defaults or args.vararg or args.kwarg or [a.arg for a in args.args] != ['output', 'release_pin'] or any(a.annotation for a in args.args):
        raise AdmissionError('entry signature must be supervise(output, release_pin)')
    if {'output', 'release_pin', 'owned'} & set(bound):
        raise AdmissionError('reserved owner/input alias shadowing')
    def origin(expr):
        if isinstance(expr, ast.Name):
            return bound.get(expr.id)
        if isinstance(expr, ast.Attribute) and not expr.attr.startswith('_'):
            parent = origin(expr.value)
            return parent + '.' + expr.attr if parent else None
        return None
    if not fn.body or not isinstance(fn.body[0], ast.Assign):
        raise AdmissionError('entry must bind one owned session')
    assign = fn.body[0]
    if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name) or assign.targets[0].id != 'owned' or not isinstance(assign.value, ast.Call):
        raise AdmissionError('single immutable owned session required')
    call = assign.value
    if origin(call.func) != FACTORY:
        raise AdmissionError('factory is not the canonical strict interface')
    # Canonicalize only a resolved static import alias. Every other node,
    # assertion, timeout, cleanup and exception operation must remain exact.
    import copy
    normalized = copy.deepcopy(fn)
    normalized.body[0].value.func = ast.Name(id='factory', ctx=ast.Load())
    expected = ast.parse(CLIENT_BODY).body[0]
    if ast.dump(normalized, include_attributes=False) != ast.dump(expected, include_attributes=False):
        raise AdmissionError('client outside the reviewed fixed lifecycle and exception template')
    calls = [{'module': entry_module, 'line': call.lineno, 'to': FACTORY, 'entry': 'heartbeat_pub'}]
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'owned':
            calls.append({'module': entry_module, 'line': node.lineno, 'to': 'owned_session.' + node.func.attr})
    return {'admitted': True, 'profile': PROFILE, 'entry_module': entry_module,
            'source_sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n, t in sources.items()},
            'imports': edges, 'calls': calls, 'allowed_entries': list(ALLOWED_ENTRIES),
            'exception_cleanup_template_sha256': hashlib.sha256(CLIENT_BODY.encode()).hexdigest(),
            'limitations': 'closed exact-source grammar, not arbitrary Python or nonexistent M6 production integration; deployment/native/entry gates mandatory; close failures remain observable and trusted supervisor must retain failed ownership'}

def read_source_manifest(path):
    root = path.parent.resolve()
    spec = json.loads(path.read_text())
    sources = {}
    for name, item in spec['modules'].items():
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise AdmissionError('source path outside reviewed root')
        p = root
        for part in relative.parts:
            p = p / part
            if p.is_symlink():
                raise AdmissionError('symlink source path not admitted')
        st = p.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise AdmissionError('non-ordinary source file')
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise AdmissionError('client source hash mismatch')
        sources[name] = data.decode()
    return sources

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--entry-module', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_sources(read_source_manifest(args.source_manifest), args.entry_module)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    return 0

# Exact R9 production profile. This policy is deliberately separate from the
# original R8 closed client grammar, whose inputs/assertions remain unchanged.
MVP_POLICY_SHA256='dad0eb9f807aacc2039e29e53db2f43a539c11353de05a15dfcb38594b1a028c'
MVP_FILES=('m6_owned_session.py','m6_fixed_heartbeat.py')

def review_mvp_sources(sources):
    if set(sources)!=set(MVP_FILES):raise AdmissionError('exact two-module MVP source set required')
    imports=[];calls=[];factories=[]
    standard={'copy','json','math','os','secrets','threading','time','traceback','pathlib'}
    relative={'strict_entry':{'AcquisitionReceipt','StrictSession','create_session','DeadlineError','ProtocolError'},'isolated_assets':{'load_assets'},'strict_dependency_gate':{'audit_mvp_package'},'m6_owned_session':{'OwnedSessionRegistry'}}
    forbidden_methods={'kill','killpg','pidfd_send_signal','send_signal','terminate','shutdown','try_shutdown','destroy_node','run_node','_stop_signals','reap','waitpid','pidfd_open','fork','execv','execve','posix_spawn'}
    for name,text in sources.items():
        tree=ast.parse(text,filename=name);aliases={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for item in node.names:
                    if item.name not in standard:raise AdmissionError('unapproved MVP import: '+item.name)
                    if item.asname and item.asname.startswith('_'):raise AdmissionError('unapproved import alias')
                    aliases[item.asname or item.name]=item.name;imports.append({'module':name,'to':item.name})
            if isinstance(node,ast.ImportFrom):
                allowed=relative.get(node.module,set()) if node.level==1 else ({'Path'} if node.module=='pathlib' and not node.level else set())
                for item in node.names:
                    if item.name not in allowed:raise AdmissionError('unapproved MVP dependency/re-export')
                    binding=item.asname or item.name
                    if binding in ('BaseException','BaseExceptionGroup','__builtins__'):raise AdmissionError('exception/global alias shadow')
                    aliases[binding]=('.' if node.level else '')+str(node.module)+'.'+item.name
                    imports.append({'module':name,'to':aliases[binding]})
        def resolve(expr):
            if isinstance(expr,ast.Name):return aliases.get(expr.id,expr.id)
            if isinstance(expr,ast.Attribute):return resolve(expr.value)+'.'+expr.attr
            return '<dynamic>'
        for node in ast.walk(tree):
            if isinstance(node,(ast.AsyncFunctionDef,ast.Await)):raise AdmissionError('async MVP unsupported')
            if not isinstance(node,ast.Call):continue
            target=resolve(node.func);calls.append({'module':name,'line':node.lineno,'target':target})
            if target in ('eval','exec','compile','__import__','getattr','setattr','globals','locals','vars') or target.startswith(('importlib.','subprocess.','ctypes.','multiprocessing.')):raise AdmissionError('dynamic/process bypass forbidden')
            if isinstance(node.func,ast.Attribute) and node.func.attr in forbidden_methods:raise AdmissionError('new signal/reaper/ROS resource closer forbidden')
            if target in ('threading.Thread','threading.Timer'):raise AdmissionError('new MVP worker thread forbidden')
            if 'borrowed' in target.lower() and target.rsplit('.',1)[-1] in ('close','release','destroy'):raise AdmissionError('borrowed-resource release forbidden')
            if target=='.strict_entry.create_session':
                if name!='m6_owned_session.py' or len(node.args)!=2 or not isinstance(node.args[0],ast.Constant) or node.args[0].value!='heartbeat_pub':raise AdmissionError('only one fixed heartbeat factory binding permitted')
                if {k.arg for k in node.keywords}!={'expected_manifest_sha256','acquisition_receipt'}:raise AdmissionError('exact release/receipt arguments required')
                factories.append({'module':name,'line':node.lineno,'entry':'heartbeat_pub'})
    if len(factories)!=1:raise AdmissionError('one canonical factory source edge required')
    return {'pass':True,'profile':'m6-fixed-heartbeat-owned-session-v1','imports':imports,'calls':calls,'factory_edges':factories,'new_signal_sender':False,'new_reaper':False,'new_domain_allocator':False,'limit':'semantic deny-list supports review; exact reviewed hashes, runtime source loader, deployment pin and negative/native tests remain mandatory; not a universal Python sandbox'}

def audit_mvp_package(package):
    import os,stat
    package=Path(package).resolve();policy_path=package/'_m6_mvp_policy.json'
    def ordinary(path):
        s=path.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid not in (0,os.geteuid()) or s.st_mode&0o022:raise AdmissionError('unsafe MVP policy/source file')
        return path.read_bytes()
    raw=ordinary(policy_path)
    if hashlib.sha256(raw).hexdigest()!=MVP_POLICY_SHA256:raise AdmissionError('reviewed MVP policy identity mismatch')
    policy=json.loads(raw)
    if policy['profile']!='m6-fixed-heartbeat-owned-session-v1' or policy['fixed_entry']!='heartbeat_pub':raise AdmissionError('wrong MVP profile')
    verified={}
    for name,digest in policy['source_sha256'].items():
        if Path(name).name!=name or not name.endswith('.py'):raise AdmissionError('invalid source policy path')
        data=ordinary(package/name)
        if hashlib.sha256(data).hexdigest()!=digest:raise AdmissionError('MVP reviewed source differs: '+name)
        verified[name]=data.decode()
    if not set(MVP_FILES).issubset(verified):raise AdmissionError('MVP source policy incomplete')
    result=review_mvp_sources({n:verified[n] for n in MVP_FILES})
    result.update(policy_sha256=MVP_POLICY_SHA256,verified_source_hashes=policy['source_sha256'],remote_ci_enforcement='NOT DEPLOYED',process_scope='one own strict direct heartbeat child; namespace admission externally required')
    return result

if __name__ == '__main__':
    raise SystemExit(main())
