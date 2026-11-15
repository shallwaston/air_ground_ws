"""Sealed -I -S child bootstrap. Concatenated after isolated_probe.py.

No handler restoration is performed. ROS is imported only after authenticated
birth and single-owner startup. This is a one-shot address space, never a forked
parent Context or an in-process signal-manager takeover.
"""
import fcntl
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import stat
import sys
import threading
import time
import traceback

class ChildAdmissionError(RuntimeError): pass
class ChildProtocolError(RuntimeError): pass
class NativeOwnershipConflict(RuntimeError): pass


def _sha(data): return hashlib.sha256(data).hexdigest()

def _sealed_bytes(fd):
    if fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=15:raise ChildAdmissionError('unsealed child input')
    with os.fdopen(os.dup(fd),'rb') as stream:
        stream.seek(0);return stream.read()


def _child_identity():
    text=Path('/proc/self/stat').read_text();fields=text[text.rfind(')')+2:].split()
    status=Path('/proc/self/status').read_text();uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1:]
    es=os.stat('/proc/self/exe')
    return {'pid':os.getpid(),'ppid':os.getppid(),'pgid':os.getpgid(0),'sid':os.getsid(0),'starttime':int(fields[19]),'uids':[int(x) for x in uid],'namespace':os.readlink('/proc/self/ns/pid'),'exe':os.readlink('/proc/self/exe'),'exe_dev':es.st_dev,'exe_ino':es.st_ino,'argv':Path('/proc/self/cmdline').read_bytes().decode().rstrip('\0').split('\0')}


def _tasks():
    rows=[]
    for p in sorted(Path('/proc/self/task').iterdir()):
        s=(p/'stat').read_text();fields=s[s.rfind(')')+2:].split()
        rows.append({'tid':int(p.name),'starttime':int(fields[19]),'comm':(p/'comm').read_text().strip(),'signal_status':[v for v in (p/'status').read_text().splitlines() if v.startswith(('SigBlk:','SigCgt:','SigIgn:'))]})
    return rows


def _exception(error):
    return {'type':type(error).__name__,'id':id(error),'message':str(error),'traceback':''.join(traceback.format_exception(type(error),error,error.__traceback__)),'children':[_exception(e) for e in error.exceptions] if isinstance(error,BaseExceptionGroup) else []}


class Reporter:
    def __init__(self,config,read_fd,write_fd,reader):
        self.config=config;self.read_fd=read_fd;self.write_fd=write_fd;self.reader=reader;self.seq=0;self.command_seq=0;self.pending=b'';self.managed_actions=None;self.stop=False;self.signal_count=0;self.last_signal=None;self.context=None;self.result_sent=False
        os.set_blocking(write_fd,False)
    def send(self,kind,**data):
        self.seq+=1;payload={'type':kind,'nonce':self.config['nonce'],'seq':self.seq,**data}
        line=json.dumps(payload,separators=(',',':')).encode()+b'\n'
        view=memoryview(line);deadline=time.monotonic()+3.0
        while view:
            try:written=os.write(self.write_fd,view)
            except BlockingIOError:
                remaining=deadline-time.monotonic()
                if remaining<=0 or not select.select([],[self.write_fd],[],remaining)[1]:raise TimeoutError('private telemetry writer deadline')
                continue
            if written<=0:raise BrokenPipeError('short private protocol write')
            view=view[written:]
    def receive(self,timeout=5):
        deadline=time.monotonic()+timeout
        while b'\n' not in self.pending:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not select.select([self.read_fd],[],[],remaining)[0]:raise TimeoutError('parent command deadline')
            data=os.read(self.read_fd,65536)
            if not data:raise ChildProtocolError('parent control channel closed')
            self.pending+=data
            if len(self.pending)>131072:raise ChildProtocolError('oversized parent command')
        line,self.pending=self.pending.split(b'\n',1);message=json.loads(line)
        if message.get('nonce')!=self.config['nonce'] or message.get('seq')!=self.command_seq+1:raise ChildProtocolError('parent command authentication mismatch')
        self.command_seq+=1;return message
    def checkpoint(self,phase,**facts):
        if phase!='before-boot':self.send('PHASE',phase=phase,**facts)
    def status(self):
        return {'stop':self.stop,'signal_count':self.signal_count,'last_signal':self.last_signal,'context_ok':self.context.ok() if self.context else False,'native_actions':self.reader.actions(),'tasks':_tasks()}
    def check_actions(self,phase):
        actual=self.reader.actions()
        if actual!=self.managed_actions:
            self.send('NATIVE_CONFLICT',phase=phase,expected=self.managed_actions,actual=actual,restore_attempted=False)
            raise NativeOwnershipConflict('native signal owner changed; no action restoration is permitted')
        return actual
    def ready(self,ros=False,**facts):
        self.check_actions('ready')
        self.send('ROS_READY' if ros else 'PROTOCOL_READY',native_actions_unchanged=True,**facts)
        # START is a second handoff: resources remain valid while QUERY/signals
        # are tested, and no business callback runs until the parent accepts.
        while True:
            message=self.receive()
            if message['type']=='QUERY':self.send('STATUS',**self.status())
            elif message['type']=='START':return
            else:raise ChildProtocolError('unexpected command before START')
    def poll_commands(self):
        if b'\n' in self.pending or select.select([self.read_fd],[],[],0)[0]:
            message=self.receive()
            if message['type']=='QUERY':self.send('STATUS',**self.status())
            elif message['type']=='RELEASE':return 'RELEASE'
            else:raise ChildProtocolError('unexpected running command')
        return None


def _protected(path):
    path=Path(path).resolve(strict=True);s=path.stat()
    if s.st_uid!=0 or s.st_mode&0o022 or not stat.S_ISREG(s.st_mode):raise ChildAdmissionError('unprotected dependency origin: '+str(path))
    for d in [path.parent,*path.parent.parents]:
        m=d.stat()
        if m.st_uid!=0 or m.st_mode&0o022:raise ChildAdmissionError('unprotected dependency directory')
    return path


class VerifiedImports(importlib.abc.MetaPathFinder):
    EXTRA={'ag_network_tools','ag_tf_tools','ag_mock_nodes','ag_interfaces','rclpy','rcl_interfaces','builtin_interfaces','ament_index_python','rpyutils','rosidl_parser','rosidl_runtime_py','rosidl_generator_py','rosidl_pycommon','tf2_ros','tf2_py','tf2_msgs','geometry_msgs','std_msgs','sensor_msgs','nav_msgs','action_msgs','actionlib_msgs','trajectory_msgs','unique_identifier_msgs','statistics_msgs','service_msgs','rosgraph_msgs','type_description_interfaces','yaml','numpy','typing_extensions','packaging','pkg_resources','lark','em'}
    def __init__(self,config):self.config=config;self.origins={};self.bundle='/proc/self/fd/'+str(config['bundle_fd'])
    def verify(self,origin):
        native=next((x for x in self.config.get('native_assets',[]) if origin=='/proc/self/fd/'+str(x['fd'])),None)
        if native:
            if _sha(_sealed_bytes(native['fd']))!=native['sha256']:raise ChildAdmissionError('sealed native extension changed')
            self.origins[origin]=native['sha256'];return
        if origin.startswith(self.bundle+'/'):
            name=origin[len(self.bundle)+1:]
            if name not in self.config['bundle_members']:raise ChildAdmissionError('unknown sealed source member')
            self.origins[origin]=self.config['bundle_members'][name];return
        real=_protected(origin)
        expected=self.config['manifest'].get(str(real))
        if expected is None or _sha(real.read_bytes())!=expected:raise ChildAdmissionError('dependency not in pinned manifest: '+str(real))
        self.origins[str(real)]=expected
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='ag_network_tools.node_runner':raise ChildAdmissionError('legacy signal manager unavailable in strict child')
        native=next((x for x in self.config.get('native_assets',[]) if x.get('module')==fullname),None)
        if native:
            origin='/proc/self/fd/'+str(native['fd'])
            spec=importlib.util.spec_from_file_location(fullname,origin,loader=importlib.machinery.ExtensionFileLoader(fullname,origin))
        else:spec=importlib.machinery.PathFinder.find_spec(fullname,path)
        if spec is None:return None  # preserve ordinary optional-import failure
        top=fullname.partition('.')[0]
        if top not in sys.stdlib_module_names and top not in self.EXTRA:raise ChildAdmissionError('unapproved module: '+fullname)
        if spec.origin is None:return spec
        self.verify(spec.origin)
        original=spec.loader;verifier=self;origin=spec.origin
        class Loader:
            def create_module(self,inner_spec):
                verifier.verify(origin)
                return original.create_module(inner_spec) if hasattr(original,'create_module') else None
            def exec_module(self,module):
                verifier.verify(origin)
                # Do not execute an unchecked on-disk pyc in place of .py.
                if origin.endswith('.py') and isinstance(original,importlib.machinery.SourceFileLoader):
                    content=Path(origin).read_bytes();exec(compile(content,origin,'exec'),module.__dict__)
                else:original.exec_module(module)
            def __getattr__(self,name):return getattr(original,name)
        spec.loader=Loader();return spec


def _native_maps(config):
    rows={};sealed={os.fstat(fd).st_ino for fd in config['sealed_fds']}
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts=line.split(maxsplit=5)
        if 'x' not in parts[1]:continue
        if len(parts)<6 or not parts[5].startswith('/'):
            if len(parts)>5 and parts[5] in ('[vdso]','[vsyscall]'):continue
            raise ChildAdmissionError('unapproved anonymous executable mapping')
        name=parts[5]
        if name.startswith('/memfd:'):
            if int(parts[4]) not in sealed:raise ChildAdmissionError('unapproved mapped memfd')
            continue
        real=Path(name).resolve(strict=True)
        if not any(real.is_relative_to(Path(root).resolve()) for root in config['native_roots']):raise ChildAdmissionError('unapproved native mapping: '+str(real))
        p=_protected(real);rows[str(p)]=_sha(p.read_bytes())
    return rows


def _audit_policy(config,event,args):
    if event in ('subprocess.Popen','os.fork','os.forkpty','os.exec','os.posix_spawn','os.system'):raise ChildAdmissionError('child process creation is outside strict node mode')
    if event=='ctypes.dlopen' and args and args[0] is not None:
        name=str(args[0])
        allowed={'/proc/self/fd/'+str(fd) for fd in config['sealed_fds']}
        if name not in allowed:
            p=Path(name)
            if not p.is_absolute():raise ChildAdmissionError('unqualified ctypes library path')
            real=_protected(p)
            if not any(real.is_relative_to(Path(r).resolve()) for r in config['native_roots']):raise ChildAdmissionError('unapproved ctypes library')


def child_main():
    config_fd,read_fd,write_fd=map(int,sys.argv[1:4]);config_bytes=_sealed_bytes(config_fd);config=json.loads(config_bytes)
    code,probe,bundle=config['sealed_fds'][:3]
    for fd,name in [(code,'bootstrap'),(probe,'probe'),(bundle,'bundle')]:
        if _sha(_sealed_bytes(fd))!=config['hashes'][name]:raise ChildAdmissionError('sealed source hash mismatch')
    if config.get('fixture_fd') is not None:_sealed_bytes(config['fixture_fd'])
    for item in config.get('native_assets',[]):
        if _sha(_sealed_bytes(item['fd']))!=item['sha256']:raise ChildAdmissionError('native capsule seal/hash mismatch')
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.ignore_environment):raise ChildAdmissionError('isolated no-site interpreter required')
    if any(k.startswith('PYTHON') or k in ('LD_PRELOAD','LD_AUDIT') for k in os.environ):raise ChildAdmissionError('unexpected startup injection')
    reader=ActionReader('/proc/self/fd/'+str(probe));reporter=Reporter(config,read_fd,write_fd,reader)
    # This is a fresh verified -I -S exec, before any extension/ROS hook.
    # Bind the actual CPython action, rather than accepting any OTHER pointer
    # as the expected Python SIGINT trampoline. No later restoration uses it.
    trusted_birth_actions=reader.actions()
    # R6_TEST_EXTENSION
    try:
        reporter.checkpoint('before-boot')
        reporter.send('BOOT',identity=_child_identity(),hashes=config['hashes'],config_hash=_sha(config_bytes),actions=reader.actions(),mask=reader.mask(),tasks=_tasks(),flags={'isolated':sys.flags.isolated,'no_site':sys.flags.no_site})
        command=reporter.receive(config['startup_timeout'])
        if command['type']!='CHALLENGE':raise ChildProtocolError('birth challenge required')
        reporter.send('BIRTH_ACK',identity=_child_identity(),challenge=command['challenge'])
        command=reporter.receive(config['startup_timeout'])
        if command['type']!='ADMIT':raise ChildProtocolError('explicit admission required')
        reporter.checkpoint('before-admission')
        actions=reader.actions();mask=reader.mask();tasks=_tasks()
        valid=(actions==trusted_birth_actions and signal.getsignal(signal.SIGINT) is signal.default_int_handler and signal.getsignal(signal.SIGTERM)==signal.SIG_DFL and actions['2']['kind']==2 and actions['15']['kind']==0 and not any(n in mask for n in (2,15)) and len(tasks)==1 and tasks[0]['tid']==os.getpid() and threading.current_thread() is threading.main_thread())
        if not valid:
            reporter.send('REFUSED',actions=actions,mask=mask,tasks=tasks,global_mutations=0,reason='untrusted inherited/startup state')
            return 78
        # There are no third-party imports or other tasks in this owned birth
        # window. No compare-and-restore action will ever be used on exit.
        def stop_handler(number,frame):
            reporter.stop=True;reporter.last_signal=number;reporter.signal_count+=1
            if reporter.context is not None:reporter.context.stop_requested=True
        previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
        try:
            reporter.checkpoint('install-int-before');signal.signal(signal.SIGINT,stop_handler);reporter.checkpoint('install-int-after')
            reporter.checkpoint('install-term-before');signal.signal(signal.SIGTERM,stop_handler);reporter.checkpoint('install-term-after')
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
        reporter.managed_actions=reader.actions();reporter.checkpoint('managed-handlers-installed',actions=reporter.managed_actions,tasks=_tasks())
        if config['entry']=='protocol':
            reporter.ready()
            while not reporter.stop:
                reporter.poll_commands();reporter.check_actions('protocol-loop');time.sleep(0.01)
            reporter.send('RESULT',ok=True,cleanup={'no_ros_resources':True},signals=reporter.signal_count,native_actions=reader.actions(),restore_attempted=False)
            reporter.result_sent=True;return 0
        # Only verified roots and immutable source ZIP are added. No .pth/site
        # hook or caller PYTHONPATH is executed under -I -S.
        sys.path=[str('/proc/self/fd/'+str(bundle)),*config['python_paths']]
        verifier=VerifiedImports(config);sys.meta_path.insert(0,verifier)
        sys.addaudithook(lambda event,args:_audit_policy(config,event,args))
        reporter.check_actions('before-ros-import')
        from ag_network_tools.isolated_runtime import run_ros
        return run_ros(reporter,config,verifier,_native_maps,_tasks,_exception)
    except BaseException as error:
        try:reporter.send('ERROR',exception=_exception(error),result_already_sent=reporter.result_sent,actions=reader.actions(),restore_attempted=False)
        except (BrokenPipeError,OSError):pass
        raise

if __name__=='__main__':
    raise SystemExit(child_main())
