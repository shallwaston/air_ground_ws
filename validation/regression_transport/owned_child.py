"""R4 test transport only: direct children, pidfd sends, no numeric fallback."""
import json,os,signal,subprocess,time,selectors
from pathlib import Path

def identity(pid,dirfd=None):
 def read(name):
  if dirfd is None:return Path(f'/proc/{pid}/{name}').read_text()
  fd=os.open(name,os.O_RDONLY,dir_fd=dirfd)
  try:return os.read(fd,65536).decode()
  finally:os.close(fd)
 text=read('stat');tail=text[text.rfind(')')+2:].split()
 status=read('status');uid=next(x for x in status.splitlines() if x.startswith('Uid:'))
 return {'pid':pid,'ppid':int(tail[1]),'pgid':int(tail[2]),'sid':int(tail[3]),'starttime':int(tail[19]),'uid':uid,'state':tail[0]}

class OwnedChild(subprocess.Popen):
 def __init__(self,*a,**kw):
  if signal.getsignal(signal.SIGCHLD)!=signal.SIG_DFL:raise RuntimeError('foreign SIGCHLD owner')
  if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):raise RuntimeError('pidfd required')
  super().__init__(*a,**kw)
  self._r4_proc=os.open(f'/proc/{self.pid}',os.O_DIRECTORY|os.O_RDONLY)
  self._r4_birth=identity(self.pid,self._r4_proc)
  if self._r4_birth['ppid']!=os.getpid():raise RuntimeError('not direct birth')
  self._r4_fd=os.pidfd_open(self.pid)
  again=identity(self.pid,self._r4_proc)
  if any(again[k]!=self._r4_birth[k] for k in ['pid','ppid','starttime','uid']):raise RuntimeError('birth changed')
  self._r4_events=[{'birth':self._r4_birth}]
 def send_signal(self,sig):
  if sig==signal.SIGKILL:raise RuntimeError('R4 forbids SIGKILL; failed child remains evidence')
  if self.returncode is not None:return
  now=identity(self.pid,self._r4_proc)
  if any(now[k]!=self._r4_birth[k] for k in ['pid','ppid','starttime','uid']):raise RuntimeError('identity conflict')
  signal.pidfd_send_signal(self._r4_fd,sig)
  self._r4_events.append({'signal':int(sig),'time_ns':time.time_ns(),'target':now,'transport':'pidfd_send_signal'})
 def close_proof(self):
  if self.returncode is None:raise RuntimeError('cannot release live child proof')
  os.close(self._r4_fd);os.close(self._r4_proc)
