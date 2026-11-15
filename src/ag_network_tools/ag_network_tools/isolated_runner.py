"""Explicit opt-in direct-child supervisor. Legacy run_node is never replaced.

Only fixed entries and a fresh isolated exec are supported. No forked ROS object,
preexec_fn, pickle, numeric signal fallback, process-group signal, or SIGKILL.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import selectors
import select
import signal
import stat
import subprocess
import sys
import sysconfig
import time
import threading
import zipfile
from .isolated_entries import ENTRIES as APPROVED_ENTRIES

APPROVED_HELPERS={'ag_tf_tools/tf_healthcheck.py': 'e67de41db79105e4da30ed1afa344237ba6e336d072e92a77f0c109f6076b64c', 'ag_network_tools/qos_profiles.py': 'aabbc3da390557a718ec14fe8da7adf550927a131b94643e8fbaf140979fe901', 'ag_network_tools/topic_names.py': 'b7fd17545034b67f241edc4b0f66c1e2a0e6fcc5565627bd70ef5eaf8014ddd3', 'ag_network_tools/node_runner.py': '6261934716b96410414c2c8aeae56ef303532b7201c365fdb583a93eda2d75cd'}

class AdmissionError(RuntimeError): pass
class ProtocolError(RuntimeError): pass
class DeadlineError(TimeoutError): pass


def digest(data): return hashlib.sha256(data).hexdigest()

def protected_file(path):
    path = Path(path).resolve(strict=True)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise AdmissionError('interpreter/dependency must be a root-owned non-writable regular file: '+str(path))
    for directory in [path.parent, *path.parent.parents]:
        meta = directory.stat()
        if meta.st_uid != 0 or meta.st_mode & 0o022:
            raise AdmissionError('unprotected dependency ancestor: '+str(directory))
    return {'path':str(path),'sha256':digest(path.read_bytes()),'dev':info.st_dev,'ino':info.st_ino,'bytes':info.st_size}


def seal(name, data):
    if not hasattr(os,'memfd_create') or not hasattr(fcntl,'F_ADD_SEALS'):
        raise AdmissionError('sealed memfd capability unavailable')
    fd = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd,view)
            if written <= 0: raise OSError('short memfd write')
            view = view[written:]
        flags = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        fcntl.fcntl(fd,fcntl.F_ADD_SEALS,flags)
        if fcntl.fcntl(fd,fcntl.F_GET_SEALS) != flags:
            raise AdmissionError('memfd seal mismatch')
        return fd
    except BaseException:
        os.close(fd)
        raise


def identity(pid, anchor):
    def read(name):
        fd = os.open(name,os.O_RDONLY,dir_fd=anchor)
        try: return os.read(fd,131072)
        finally: os.close(fd)
    text=read('stat').decode(); fields=text[text.rfind(')')+2:].split()
    status=read('status').decode(); uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1:]
    exe=os.readlink('exe',dir_fd=anchor); es=os.stat('exe',dir_fd=anchor)
    return {'pid':pid,'ppid':int(fields[1]),'pgid':int(fields[2]),'sid':int(fields[3]),'starttime':int(fields[19]),'state':fields[0],'uids':[int(x) for x in uid],'namespace':os.readlink('ns/pid',dir_fd=anchor),'exe':exe,'exe_dev':es.st_dev,'exe_ino':es.st_ino,'argv':read('cmdline').decode().rstrip('\0').split('\0')}


class DirectChild(subprocess.Popen):
    def __init__(self,*args,**kwargs):
        self.raw_wait_status=None
        super().__init__(*args,**kwargs)
    def _try_wait(self,wait_flags):
        # Do not turn an external reaper/ECHILD into a fabricated exit 0.
        return os.waitpid(self.pid,wait_flags)
    def _handle_exitstatus(self,status,*args,**kwargs):
        self.raw_wait_status=status
        return super()._handle_exitstatus(status,*args,**kwargs)
    def poll(self):
        try: return self.wait(timeout=0)
        except subprocess.TimeoutExpired: return None
    def send_signal(self,*args,**kwargs):
        raise AdmissionError('use authenticated pidfd capability')
    def kill(self): raise AdmissionError('SIGKILL is not a supported cleanup path')
    def terminate(self): raise AdmissionError('use authenticated pidfd capability')


class ChildObservation:
    BIRTH_STABLE=('pid','ppid','starttime','uids','namespace')
    STABLE=('pid','ppid','pgid','sid','starttime','uids','namespace','exe','exe_dev','exe_ino','argv')
    def __init__(self,process,expected_exe,argv):
        self.process=process;self.authorized=False;self.events=[];self.anchor=None;self.pidfd=None;self.bound=None;self.expected_exe=expected_exe;self.expected_argv=argv;self.lock=threading.RLock()
        try:
            self.anchor=os.open('/proc/'+str(process.pid),os.O_RDONLY|os.O_DIRECTORY)
            self.initial=identity(process.pid,self.anchor)
            self.pidfd=os.pidfd_open(process.pid)
            current=identity(process.pid,self.anchor)
            if any(current[k]!=self.initial[k] for k in self.BIRTH_STABLE): raise AdmissionError('birth identity changed during observation binding')
            if current['ppid']!=os.getpid() or current['uids'][0]!=os.getuid() or current['namespace']!=os.readlink('/proc/self/ns/pid'):
                raise AdmissionError('not this supervisor direct child')
            # Initial proc observation may overlap exec completion. It grants
            # no signal rights. The exact image/argv is verified after private
            # child liveness, without reopening/rebinding the numeric PID.
            self.events.append({'event':'INITIAL_OBSERVATION','identity':current,'signal_authority':False})
        except BaseException:
            self.close_observation()
            raise
    def grant(self,receipt):
        with self.lock:return self._grant_locked(receipt)
    def _grant_locked(self,receipt):
        current=identity(self.process.pid,self.anchor)
        if any(current[k]!=self.initial[k] for k in self.BIRTH_STABLE): raise AdmissionError('birth identity changed before nonce liveness proof')
        if current['exe_dev']!=self.expected_exe['dev'] or current['exe_ino']!=self.expected_exe['ino'] or current['argv']!=self.expected_argv:
            raise AdmissionError('authenticated exec/argv mismatch')
        if current['sid']!=current['pid'] or current['pgid']!=current['pid']:raise AdmissionError('child did not create the declared private session')
        reported=receipt['identity']
        for key in ('pid','ppid','pgid','sid','starttime','uids','namespace','exe_dev','exe_ino'):
            if current[key]!=reported[key]: raise AdmissionError('private receipt identity mismatch: '+key)
        if select.select([self.pidfd],[],[],0)[0]: raise AdmissionError('child exited before capability grant')
        self.bound=current
        self.authorized=True
        self.events.append({'event':'SIGNAL_CAPABILITY_GRANTED','identity':current})
    def send(self,number,reason):
        with self.lock:return self._send_locked(number,reason)
    def _send_locked(self,number,reason):
        if number not in (signal.SIGINT,signal.SIGTERM): raise AdmissionError('unsupported signal')
        if not self.authorized: raise AdmissionError('no authenticated signal capability')
        if select.select([self.pidfd],[],[],0)[0]: raise ProcessLookupError('bound child already exited')
        current=identity(self.process.pid,self.anchor)
        if any(current[k]!=self.bound[k] for k in self.STABLE): raise AdmissionError('bound identity changed; no signal sent')
        signal.pidfd_send_signal(self.pidfd,number)
        self.events.append({'event':'SIGNAL','number':int(number),'reason':reason,'identity':current,'time_ns':time.time_ns()})
    def close_observation(self):
        errors=[]
        with self.lock:
            self.authorized=False
            for name in ('pidfd','anchor'):
                fd=getattr(self,name,None)
                setattr(self,name,None)  # retire before close; never retry an FD integer
                if fd is not None:
                    try:os.close(fd)
                    except OSError as error:errors.append(error)
        if errors:raise BaseExceptionGroup('capability close failed',errors)


class RuntimePolicy:
    """Pinned source bundle plus root-protected, explicitly listed image paths."""
    def __init__(self,probe=None,*,ros=False,interpreter=None,deployment=False):
        if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
            raise AdmissionError('pidfd and pidfd_send_signal required before spawn')
        if interpreter is not None and Path(interpreter).resolve()!=Path(sys._base_executable).resolve():
            raise AdmissionError('interpreter must match the policy-building Python runtime')
        self.interpreter=protected_file(interpreter or sys._base_executable)
        self.source=Path(__file__).resolve().parent
        self.deployment=deployment;self.assets=None
        if deployment or (ros and (self.source/'strict_assets').is_dir()):
            from .isolated_assets import load_assets
            self.assets=load_assets(self.source)
        if deployment:
            if not ros or probe is not None:raise AdmissionError('deployment uses only its installed verified probe')
            probe=self.assets['root']/'probe.so'
        if probe is None:raise AdmissionError('explicit evidence probe or installed deployment required')
        self.probe=Path(probe).resolve(strict=True);self.probe_bytes=self.probe.read_bytes()
        self.source=Path(__file__).resolve().parent
        self.ros=ros
        if ros and (sys.version_info[:2]!=(3,12) or not Path('/opt/ros/jazzy/lib/python3.12/site-packages').is_dir()):
            raise AdmissionError('fixed Jazzy Python 3.12 installation required')
        self.paths=[str(Path(sysconfig.get_path('stdlib')).resolve()),str(Path(sysconfig.get_path('stdlib')).resolve()/'lib-dynload')]
        if ros:
            self.paths+=['/opt/ros/jazzy/lib/python3.12/site-packages','/usr/lib/python3/dist-packages']
        self.paths=[p for p in self.paths if Path(p).is_dir()]
        self.manifest={}
        for root in self.paths:
            for base,dirs,names in os.walk(root):
                dirs[:]=[d for d in dirs if d not in ('__pycache__','site-packages','dist-packages','tests','test')]
                for name in names:
                    p=Path(base)/name
                    if p.is_file() and p.suffix in ('.py','.so'):
                        real=p.resolve()
                        if str(real) not in self.manifest:self.manifest[str(real)]=protected_file(real)['sha256']
        self.ld_paths=['/opt/ros/jazzy/lib','/opt/ros/jazzy/lib/x86_64-linux-gnu'] if ros else []
        self.ld_paths=[p for p in self.ld_paths if Path(p).is_dir()]
        # Native loader provenance is the fixed root-owned image. Hash mapped
        # libraries per checkpoint; Python extension origins are pinned above.
        self.native_roots=[str(Path(sys.base_prefix).resolve()),'/usr/lib','/lib']
        if ros:self.native_roots+=['/opt/ros/jazzy']
        self.bootstrap=(self.source/'isolated_probe.py').read_bytes()+b'\n'+(self.source/'isolated_bootstrap.py').read_bytes()
        if self.assets:
            self.bundle_bytes=self.assets['files']['source.zip'];self.bundle_members=self.assets['manifest']['members']
        else:self.bundle_bytes,self.bundle_members=self._bundle()
        self.hashes={'bootstrap':digest(self.bootstrap),'probe':digest(self.probe_bytes),'bundle':digest(self.bundle_bytes),'interpreter':self.interpreter['sha256']}
        if self.assets:self.hashes['deployment_manifest']=self.assets['manifest_sha256']
    def _bundle(self):
        stream=io.BytesIO();members={}
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as archive:
            roots={'ag_network_tools':self.source}
            tf=self.source.parents[1]/'ag_tf_tools/ag_tf_tools'
            if tf.is_dir():roots['ag_tf_tools']=tf
            for package,root in roots.items():
                for p in sorted(root.glob('*.py')):
                    if p.name=='node_runner.py':continue  # strict child never imports the legacy signal manager
                    name=package+'/'+p.name;b=p.read_bytes()
                    if name in APPROVED_HELPERS and digest(b)!=APPROVED_HELPERS[name]:raise AdmissionError('approved helper/entry source changed: '+name)
                    archive.writestr(name,b);members[name]=digest(b)
        return stream.getvalue(),members


class IsolatedSession:
    ENTRIES=('protocol','minimal',*APPROVED_ENTRIES)
    def __init__(self,policy,output,*,entry='minimal',ros_args=(),extension=b'',fixture_bytes=None):
        if entry not in self.ENTRIES: raise AdmissionError('unapproved entry')
        if entry!='protocol' and not policy.ros: raise AdmissionError('Jazzy policy required')
        allowed_pilot=tuple(APPROVED_ENTRIES[entry]['args']) if entry in APPROVED_ENTRIES else ()
        if policy.deployment and (entry not in APPROVED_ENTRIES or tuple(ros_args)!=allowed_pilot):
            raise AdmissionError('deployment entry/parameter preset mismatch')
        if entry in ('heartbeat_pub','ugv_map_tile_sub') and not policy.assets:raise AdmissionError('installed interface capsule required')
        if not extension and tuple(ros_args) not in ((),allowed_pilot):
            raise AdmissionError('unapproved isolated entry arguments')
        if signal.getsignal(signal.SIGCHLD)!=signal.SIG_DFL: raise AdmissionError('foreign SIGCHLD/reaper unsupported')
        self.controller=threading.current_thread();self.policy=policy;self.output=Path(output);self.output.mkdir(parents=True,exist_ok=False)
        self.nonce=secrets.token_hex(32);self.challenge=secrets.token_hex(32);self.entry=entry
        self.events=[];self.errors=[];self.started=False;self.ready=False;self.birth=False;self.sequence=0;self.command_sequence=0
        self.process=None;self.observation=None;self.selector=None;self.stdout=None;self.stderr=None;self.references_closed=False;self.uncertain_closures=[];self._uncertain_resource_objects=[];self.launch={};self.buffer=b'';self.fds=[];self.recovery=[]
        self.command_fd=None;self.read_fd=None;self.last_result=None;self.phases=[];self.spawn_ends=[]
        self.allocation_initialized=True
        try:
            self.selector=selectors.DefaultSelector()
            self.stdout=(self.output/'stdout.log').open('wb');self.stderr=(self.output/'stderr.log').open('wb')
            script=policy.bootstrap
            if extension:
                marker=b'    # R6_TEST_EXTENSION\n'
                if script.count(marker)!=1:raise AdmissionError('invalid explicit test extension marker')
                # Explicit test profile only. No CLI input enables code injection.
                indented=b'\n'.join(b'    '+line for line in extension.splitlines())+b'\n'
                script=script.replace(marker,indented)
            code=seal('r6-bootstrap',script);self.fds.append(code)
            probe=seal('r6-probe',policy.probe_bytes);self.fds.append(probe)
            bundle=seal('r6-source',policy.bundle_bytes);self.fds.append(bundle)
            native_assets=[]
            if policy.assets:
                for item in policy.assets['manifest']['native']:
                    native_fd=seal('r7-native-'+item['file'],policy.assets['files'][item['file']]);self.fds.append(native_fd)
                    native_assets.append({**{k:v for k,v in item.items() if k!='dynamic_metadata'},'fd':native_fd,'sha256':digest(policy.assets['files'][item['file']])})
            fixture=None
            if fixture_bytes is not None:
                fixture=seal('r6-test-fixture',fixture_bytes);self.fds.append(fixture)
            config={'nonce':self.nonce,'entry':entry,'ros':policy.ros,'ros_args':list(ros_args),'python_paths':policy.paths,'manifest':policy.manifest,'native_roots':policy.native_roots,'bundle_members':policy.bundle_members,'hashes':{**policy.hashes,'bootstrap':digest(script)},'sealed_fds':[code,probe,bundle],'bundle_fd':bundle,'probe_fd':probe,'fixture_fd':fixture,'test_profile':bool(extension),'startup_timeout':5.0}
            config['sealed_fds']=list(self.fds)
            config['native_assets']=native_assets;config['deployment']=policy.deployment
            config['deployment_manifest_sha256']=policy.assets['manifest_sha256'] if policy.assets else None
            config_bytes=json.dumps(config,separators=(',',':')).encode();self.config_sha=digest(config_bytes)
            cfd=seal('r6-config',config_bytes);self.fds.append(cfd)
            to_child_r,to_child_w=os.pipe2(os.O_CLOEXEC)
            # Register the first pair before the second allocation can fail.
            self.spawn_ends=[to_child_r];self.command_fd=to_child_w
            from_child_r,from_child_w=os.pipe2(os.O_CLOEXEC)
            self.spawn_ends.append(from_child_w);self.read_fd=from_child_r
            self.selector.register(from_child_r,selectors.EVENT_READ)
            child_fds=[*self.fds,to_child_r,from_child_w]
            self.argv=[policy.interpreter['path'],'-I','-S','-B',f'/proc/self/fd/{code}',str(cfd),str(to_child_r),str(from_child_w)]
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(self.output/'home'),'ROS_HOME':str(self.output/'ros-home'),'ROS_DOMAIN_ID':'42','ROS_DISTRO':'jazzy','ROS_VERSION':'2','ROS_PYTHON_VERSION':'3','AMENT_PREFIX_PATH':'/opt/ros/jazzy','RMW_IMPLEMENTATION':'rmw_fastrtps_cpp','ROS_AUTOMATIC_DISCOVERY_RANGE':'LOCALHOST','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','RCUTILS_LOGGING_USE_STDOUT':'0'}
            if policy.ld_paths:env['LD_LIBRARY_PATH']=':'.join(policy.ld_paths)
            for k in ('SSL_CERT_FILE','REQUESTS_CA_BUNDLE','PIP_CERT'):env[k]='/run/cloud-ca.pem' if Path('/run/cloud-ca.pem').is_file() else '/etc/ssl/certs/ca-certificates.crt'
            cwd=self.output/'cwd';cwd.mkdir(mode=0o700)
            self.launch={'argv':self.argv,'interpreter':policy.interpreter,'hashes':config['hashes'],'nonce_sha256':digest(self.nonce.encode()),'profile':'test' if extension else 'production','deployment':policy.deployment,'entry':entry,'environment':env,'private_source_members':policy.bundle_members}
            self.process=DirectChild(self.argv,stdin=subprocess.DEVNULL,stdout=self.stdout,stderr=self.stderr,env=env,cwd=cwd,pass_fds=child_fds,start_new_session=True)
            os.close(to_child_r);os.close(from_child_w);self.spawn_ends=[]
            # Observation only; no signal until private challenge response.
            self.observation=ChildObservation(self.process,policy.interpreter,self.argv)
        except BaseException as primary:
            cleanup_errors=[]
            if self.command_fd is not None:
                fd=self.command_fd;self.command_fd=None
                try:os.close(fd)
                except BaseException as cleanup:cleanup_errors.append(cleanup);self.uncertain_closures.append('constructor-command-fd')
            if self.process is not None:
                try:self.process.wait(timeout=5)
                except BaseException as cleanup:
                    grouped=BaseExceptionGroup('launch failed; child ownership retained',[primary,*cleanup_errors,cleanup]);grouped.supervision=self;raise grouped
            try:
                (self.output/'launch-failure.json').write_text(json.dumps({'error':repr(primary),'returncode':self.process.returncode if self.process else None,'raw_wait_status':self.process.raw_wait_status if self.process else None,'signal_authority':False,'launch':self.launch},indent=2)+'\n')
            except BaseException as cleanup:cleanup_errors.append(cleanup)
            try:self.close_channels()
            except BaseException as cleanup:cleanup_errors.append(cleanup)
            if cleanup_errors:
                grouped=BaseExceptionGroup('launch and independent resource cleanup failed',[primary,*cleanup_errors]);grouped.supervision=self;raise grouped
            raise
    def _check_controller(self):
        if threading.current_thread() is not self.controller:raise AdmissionError('one supervisor thread must own a Session')
    def receive(self,timeout=5):
        self._check_controller()
        deadline=time.monotonic()+timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise DeadlineError('private protocol deadline')
            if not self.selector.select(remaining):raise DeadlineError('private protocol deadline')
            data=os.read(self.read_fd,65536)
            if not data:raise ProtocolError('private child channel EOF')
            self.buffer+=data
            if len(self.buffer)>1024*1024:raise ProtocolError('oversized protocol packet')
        line,self.buffer=self.buffer.split(b'\n',1)
        message=json.loads(line)
        if message.get('nonce')!=self.nonce:raise ProtocolError('message nonce mismatch')
        if message.get('seq')!=self.sequence+1:raise ProtocolError('message sequence mismatch')
        self.sequence+=1
        redacted={k:v for k,v in message.items() if k not in ('nonce','challenge')}
        redacted['nonce_sha256']=digest(self.nonce.encode());self.events.append(redacted)
        if message['type']=='PHASE':self.phases.append(message['phase'])
        if message['type']=='RESULT':self.last_result=message
        return message
    def command(self,kind,**payload):
        self._check_controller()
        self.command_sequence+=1
        data=json.dumps({'type':kind,'nonce':self.nonce,'seq':self.command_sequence,**payload},separators=(',',':')).encode()+b'\n'
        view=memoryview(data)
        while view:
            n=os.write(self.command_fd,view);view=view[n:]
    def authenticate_birth(self,timeout=5):
        first=self.receive(timeout)
        if first['type']!='BOOT' or first['hashes']!=self.launch['hashes'] or first.get('config_hash')!=self.config_sha:raise ProtocolError('untrusted bootstrap receipt')
        self.command('CHALLENGE',challenge=self.challenge)
        ack=self.receive(timeout)
        if ack['type']!='BIRTH_ACK' or ack.get('challenge')!=self.challenge:raise ProtocolError('birth challenge mismatch')
        self.observation.grant(ack)
        self.birth=True
        return ack
    def admit(self): self.command('ADMIT')
    def await_ready(self,timeout=10,*,start=True):
        deadline=time.monotonic()+timeout
        expected='PROTOCOL_READY' if self.entry=='protocol' else 'ROS_READY'
        while True:
            message=self.receive(max(0.001,deadline-time.monotonic()))
            kind=message['type']
            if kind in ('REFUSED','ERROR','RESULT'):raise ProtocolError('child failed before READY: '+kind)
            if kind in ('ROS_READY','PROTOCOL_READY'):
                if kind!=expected:raise ProtocolError('READY mode mismatch')
                if 'managed-handlers-installed' not in self.phases:raise ProtocolError('premature READY before managed startup')
                if not message.get('native_actions_unchanged'):raise ProtocolError('unverified READY signal state')
                if expected=='ROS_READY':
                    required=['ros-imported','context-initialized','executor-created','node-created','node-added','ros-ready-verified']
                    if any(p not in self.phases for p in required) or not message.get('private_context') or not message.get('node_owned') or not message.get('executor_owned'):
                        raise ProtocolError('premature or unowned ROS READY')
                self.ready=True
                if start:self.start()
                return message
    def start(self):self.command('START');self.started=True
    def query(self,timeout=5):
        self.command('QUERY')
        deadline=time.monotonic()+timeout
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise DeadlineError('query total deadline exceeded')
            result=self.receive(remaining)
            if result['type']=='STATUS':return result
    def signal(self,number,reason='requested-stop'):
        self._check_controller();self.observation.send(number,reason)
    def wait(self,timeout=10):
        self._check_controller()
        deadline=time.monotonic()+timeout
        while True:
            try:self.receive(min(0.1,max(0.001,deadline-time.monotonic())))
            except DeadlineError:pass
            except ProtocolError as exc:
                if str(exc)=='private child channel EOF':break
                self.errors.append(str(exc))
            if time.monotonic()>=deadline:
                self.errors.append('child completion deadline exceeded');raise DeadlineError('child completion deadline')
        remaining=deadline-time.monotonic()
        if remaining<=0:
            self.errors.append('waitpid deadline exceeded');raise DeadlineError('waitpid deadline')
        code=self.process.wait(timeout=remaining)
        if self.process.raw_wait_status is None:raise AdmissionError('no direct raw waitpid status')
        return code
    def abort(self,reason,timeout=5):
        self.errors.append(reason)
        if self.command_fd is not None:
            os.close(self.command_fd);self.command_fd=None
        if self.observation is not None and self.observation.authorized and not select.select([self.observation.pidfd],[],[],0)[0]:
            self.observation.send(signal.SIGTERM,'recovery-after-failure')
            self.recovery.append('SIGTERM')
        return self.wait(timeout=timeout)
    def report(self):
        return {'references_closed':self.references_closed,'uncertain_closures':list(self.uncertain_closures),'allocation_has_child':self.process is not None,'accepted':bool(self.ready and self.process and self.process.returncode==0 and not self.errors and not self.recovery and self.last_result and self.last_result.get('ok')),'launch':self.launch,'birth_authenticated':self.birth,'ready':self.ready,'started':self.started,'events':self.events,'errors':self.errors,'signals':self.observation.events if self.observation else [],'returncode':self.process.returncode if self.process else None,'raw_wait_status':self.process.raw_wait_status if self.process else None,'recovery':self.recovery,'result':{k:v for k,v in self.last_result.items() if k!='nonce'} if self.last_result else None}
    def close_channels(self):
        errors=[]
        if self.observation is not None:
            try:self.observation.close_observation()
            except BaseException as error:errors.append(error)
        descriptors=[self.command_fd,self.read_fd,*self.fds,*self.spawn_ends]
        self.command_fd=None;self.read_fd=None;self.fds=[];self.spawn_ends=[]
        for fd in dict.fromkeys(fd for fd in descriptors if fd is not None):
            try:os.close(fd)
            except OSError as error:errors.append(error)
        for name in ('selector','stdout','stderr'):
            resource=getattr(self,name);setattr(self,name,None)
            if resource is None:continue
            try:resource.close()
            except BaseException as error:
                errors.append(error);self.uncertain_closures.append(name);self._uncertain_resource_objects.append(resource)
        if errors:
            self.uncertain_closures.append('descriptor-close-failure')
            raise BaseExceptionGroup('supervisor descriptor cleanup failed',errors)
        self.references_closed=not self.uncertain_closures
    def close(self):
        self._check_controller()
        if self.process is not None and self.process.returncode is None:
            raise AdmissionError('live direct child must be supervised, not silently closed')
        self.close_channels()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Explicit strict isolated Jazzy entry; legacy console scripts are unchanged')
    parser.add_argument('--probe',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--entry',choices=['minimal','tf_healthcheck'],default='minimal')
    args,ros_args=parser.parse_known_args(argv)
    policy=RuntimePolicy(args.probe,ros=True)
    session=IsolatedSession(policy,args.output,entry=args.entry,ros_args=ros_args)
    primary=None;cleanup_errors=[];returncode=None
    try:
        session.authenticate_birth();session.admit();session.await_ready()
        returncode=session.wait(timeout=30)
    except BaseException as error:
        primary=error
        if session.process.returncode is None:
            try:session.abort('parent CLI failure')
            except BaseException as cleanup:cleanup_errors.append(cleanup)
    finally:
        try:(Path(args.output)/'supervision.json').write_text(json.dumps(session.report(),indent=2)+'\n')
        except BaseException as cleanup:cleanup_errors.append(cleanup)
        if session.process.returncode is not None:
            try:session.close()
            except BaseException as cleanup:cleanup_errors.append(cleanup)
    if cleanup_errors:
        raise BaseExceptionGroup('supervision and cleanup failed',([primary] if primary else [])+cleanup_errors)
    if primary is not None:raise primary.with_traceback(primary.__traceback__)
    # Raw child wait status and negative signal returncode remain in the JSON;
    # the CLI's own conventional shell status is a distinct value.
    return returncode if returncode>=0 else 128-returncode

if __name__=='__main__':
    raise SystemExit(main())
