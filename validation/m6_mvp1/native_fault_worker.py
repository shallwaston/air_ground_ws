"""Real Jazzy fault injection in this worker only; never a normal PASS claim."""
import json,os,select,signal,sys,threading,time,traceback
from pathlib import Path
C=Path(__file__).resolve().parents[2];A=C.parent;script=C/'install/ag_network_tools/lib/ag_network_tools/ag_strict_isolated'
ns={'__name__':'r9_fault_loader','__file__':str(script)};exec(compile(script.read_bytes(),str(script),'exec'),ns);verified=ns['load_verified_package']()
from ag_network_tools import strict_entry as facade,isolated_runner as ir,m6_owned_session as model
from ag_network_tools.m6_fixed_heartbeat import FixedHeartbeatAdapter
case=sys.argv[1];root=Path(sys.argv[2]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
raw_backend=[];Original=facade.IsolatedSession
class Recorded(Original):
    def __init__(self,*args,**kwargs):raw_backend.append(self);super().__init__(*args,**kwargs)
    def receive(self,*args,**kwargs):
        message=super().receive(*args,**kwargs)
        if case=='ready-loss' and message['type']=='ROS_READY':return {**message,'type':'PHASE','phase':'injected-ready-loss'}
        if case=='birth-mismatch' and message['type']=='BIRTH_ACK':return {**message,'identity':{**message['identity'],'sid':message['identity']['sid']+1}}
        return message
facade.IsolatedSession=Recorded
adapter=None;captured=[];primary=None;extra={};operator_cleanup=[];old_sigchld=None;start=time.monotonic()
def expected(function):
    try:function()
    except BaseException as error:captured.append(error);return error
    raise AssertionError('expected fault rejection missing')
def record_signal(number,reason):
    backend=raw_backend[0];obs=backend.observation
    assert obs.authorized and not select.select([obs.pidfd],[],[],0)[0]
    current=ir.identity(backend.process.pid,obs.anchor)
    assert all(current[k]==obs.bound[k] for k in obs.STABLE)
    extra.setdefault('fixture_signal_audit',[]).append({'number':number,'reason':reason,'identity':current,'same_existing_authenticated_pidfd':True,'no_numeric_fallback':True})
    signal.pidfd_send_signal(obs.pidfd,number)
def wait_callback():
    deadline=time.monotonic()+5
    while not any(e.get('phase')=='callback-return' for e in raw_backend[0].events):
        if time.monotonic()>deadline:raise TimeoutError('real heartbeat callback missing')
        adapter.observe()
try:
    if case=='file-open':
        parent=root/'read-only';parent.mkdir();parent.chmod(0o500);output=parent/'owned'
    else:output=root/'owned'
    adapter=FixedHeartbeatAdapter(output,verified['manifest_sha256'])
    if case=='foreign-reaper-ignore':old_sigchld=signal.signal(signal.SIGCHLD,signal.SIG_IGN)
    if case in ('ready-loss','birth-mismatch','foreign-reaper-ignore','file-open'):
        expected(adapter.acquire_fixed_heartbeat);report=adapter.get_cleanup_report();assert not report['accepted']
        if case in ('foreign-reaper-ignore','file-open'):assert not report['owned']['session_materialized'] and report['raw_wait_status'] is None
        else:assert report['returncode']!=0 and report['raw_wait_status'] is not None
        if case=='birth-mismatch':assert not any(e['event']=='SIGNAL' for e in report['strict_report']['signals'])
    else:
        adapter.acquire_fixed_heartbeat();adapter.start();wait_callback();backend=raw_backend[0]
        if case=='child-nonzero':
            descriptor=backend.command_fd;backend.command_fd=None;os.close(descriptor)
            expected(adapter.wait);expected(adapter.close);report=adapter.get_cleanup_report();assert report['returncode']==1 and report['raw_wait_status']==256 and not report['accepted']
            extra['injection']='closed only this test-owned original private command pipe; actual child protocol failure, no Node/QoS source change'
        elif case=='foreign-reaper-takeover':
            pid=backend.process.pid;ready=threading.Event();reaped=[];tid=[]
            def foreign_waiter():
                tid.append(threading.get_native_id());ready.set();reaped.append(os.waitpid(pid,0))
            thread=threading.Thread(target=foreign_waiter);thread.start();ready.wait(2)
            deadline=time.monotonic()+2
            while (Path('/proc/self/task')/str(tid[0])/'wchan').read_text().strip()!='do_wait':
                if time.monotonic()>deadline:raise TimeoutError('foreign waiter never reached actual kernel do_wait barrier')
                time.sleep(0.001)
            adapter.request_stop();thread.join(10);assert not thread.is_alive() and reaped and reaped[0][0]==pid
            expected(adapter.wait);expected(adapter.close);report=adapter.get_cleanup_report();assert report['state']=='QUARANTINED' and report['raw_wait_status'] is None and not report['accepted']
            extra['foreign_reaper_actual_wait']={'pid':reaped[0][0],'raw_status':reaped[0][1],'not_trusted_as_mvp_wait_status':True,'kernel_do_wait_barrier':True}
            # Test-fixture cleanup after sealed failed verdict, not a production
            # reaper, retry, status repair or normal acceptance.
            backend.close_channels();operator_cleanup.append('known reference objects closed only after actual external reap; cached MVP UNKNOWN verdict unchanged')
        elif case=='signal-timeout':
            record_signal(signal.SIGSTOP,'test-only scheduler suspension, actual timeout fault')
            deadline=time.monotonic()+2
            while ir.identity(backend.process.pid,backend.observation.anchor)['state'] not in ('T','t'):
                if time.monotonic()>deadline:raise TimeoutError('SIGSTOP state barrier missing')
                time.sleep(0.001)
            adapter.request_stop();error=expected(lambda:adapter.wait(0.2));expected(lambda:adapter.close(primary_error=error));report=adapter.get_cleanup_report()
            assert report['state']=='QUARANTINED' and report['raw_wait_status'] is None and not report['accepted']
            record_signal(signal.SIGCONT,'test-only resumption after failed/quarantined verdict')
            residual=adapter.registry.get_residual_owner();code=residual.wait(10);residual.close()
            operator_cleanup.append({'manual_known_capability_after_verdict':True,'returncode':code,'raw_wait_status':backend.process.raw_wait_status,'cached_mvp_verdict_not_rewritten':True})
            assert adapter.get_cleanup_report()['raw_wait_status'] is None
        elif case=='evidence-close':
            original=model._EvidenceJournal.close
            def fail(journal):
                original(journal);journal.closed=False;journal.uncertain=True;raise OSError('native worker injected uncertain journal-close outcome')
            model._EvidenceJournal.close=fail
            adapter.request_stop();adapter.wait();expected(adapter.close);report=adapter.get_cleanup_report()
            assert report['state']=='QUARANTINED' and not report['accepted'] and report['raw_wait_status']==0
            assert report['strict_report']['references_closed'] and not report['owned']['journal']['closed_proven']
        else:raise ValueError(case)
    assert report['borrowed_release_actions']==[] and not report['borrowed']['ros_domain_id']['released']
except BaseException as error:primary=error
finally:
    if old_sigchld is not None:signal.signal(signal.SIGCHLD,old_sigchld)
    if case=='file-open':(root/'read-only').chmod(0o700)
    facade.IsolatedSession=Original
    if adapter is not None:
        try:(root/'cleanup-report.json').write_text(json.dumps(adapter.get_cleanup_report(),indent=2)+'\n')
        except BaseException as error:
            primary=BaseExceptionGroup('fault validation and evidence output failed',([primary] if primary else [])+[error])
row={'id':'R9-NATIVE-FAULT-'+case,'status':'PASS' if primary is None else 'FAIL','seconds':time.monotonic()-start,'release_manifest':verified['manifest_sha256'],'fault_injection':True,'normal_child_acceptance':False,'actual_exception_chains':[''.join(traceback.format_exception(e)) for e in captured],'operator_cleanup_separate_from_verdict':operator_cleanup,**extra}
if primary is not None:row.update(exception=repr(primary),traceback=''.join(traceback.format_exception(primary)))
(root/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(row['id'],row['status']);raise SystemExit(0 if primary is None else 1)
