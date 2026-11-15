"""R4-only test transport. No test assertions, counters or deadlines changed."""
import os
if os.environ.get('R4_OWNED_SIGNAL_TRANSPORT')=='1':
 import json,signal,subprocess,time
 from pathlib import Path
 from owned_child import OwnedChild
 _registry={};_base=OwnedChild
 _audit=Path(os.environ['R4_SIGNAL_AUDIT']);_audit.mkdir(parents=True,exist_ok=True)
 def record(value):
  with (_audit/(str(os.getpid())+'.jsonl')).open('a') as f:f.write(json.dumps({'time_ns':time.time_ns(),**value})+'\n')
 class RecordedChild(_base):
  def __init__(self,*a,**kw):
   super().__init__(*a,**kw);_registry[self.pid]=self;record({'event':'birth','proof':self._r4_birth,'argv':str(a[0]) if a else str(kw.get('args'))})
  def send_signal(self,sig):
   super().send_signal(sig);record({'event':'signal','sig':int(sig),'proof':self._r4_birth,'fd':self._r4_fd,'returncode':self.returncode})
  def wait(self,*a,**kw):
   result=super().wait(*a,**kw);record({'event':'wait','child':self.pid,'exit_code':result});return result
 subprocess.Popen=RecordedChild
 def only_owned(pid,sig):
  if pid==os.getpid():
   fd=os.pidfd_open(pid)
   try:signal.pidfd_send_signal(fd,sig)
   finally:os.close(fd)
   record({'event':'self-signal','sig':int(sig),'pid':pid});return
  if pid in _registry:return _registry[pid].send_signal(sig)
  raise RuntimeError('R4 refused numeric signal to unbound target')
 def no_group(pgid,sig):raise RuntimeError('R4 forbids process-group signal fallback')
 os.kill=only_owned;os.killpg=no_group
 record({'event':'transport-enabled','no_numeric_fallback':True})
