"""One isolated contract case; real journal IO, explicitly simulated Session."""
import copy,json,os,sys,threading,traceback,types
from pathlib import Path
C=Path(__file__).resolve().parents[2];sys.path.insert(0,str(C/'src/ag_network_tools'))
from ag_network_tools import m6_owned_session as m,strict_entry as facade
from ag_network_tools.m6_fixed_heartbeat import FixedHeartbeatAdapter
PIN='a'*64

class Injected(ValueError):pass
class Borrowed:
    def __init__(self):self.calls=[]
    def shutdown(self):self.calls.append('shutdown');raise AssertionError('borrowed Context shutdown')
    def close(self):self.calls.append('close');raise AssertionError('borrowed resource close')

class Backend:
    def __init__(self,config):
        self.config=config;self.allocation_initialized=True;self.references_closed=False;self.process=types.SimpleNamespace(returncode=None)
        self.started=False;self.stop=False;self.raw=None;self.calls=[];self.recovery=[];self.callback=False
        self.identity={'pid':990001,'ppid':os.getpid(),'pgid':990001,'sid':990001,'starttime':1,'uids':[os.getuid()],'namespace':'unit-only','exe':'unit-only','exe_dev':1,'exe_ino':1,'argv':['SIMULATED']}
    def start(self):self.calls.append('start');self.started=True;self.callback=not self.stop
    def signal(self,n,reason):
        self.calls.append('signal-'+str(n))
        if 'stop_error' in self.config:raise self.config['stop_error']
        self.stop=True
    def query(self,timeout):
        self.calls.append('query')
        if self.process.returncode is not None:raise facade.ProtocolError('private child channel EOF')
        return {'stop':self.stop,'context_ok':not self.config.get('bad_context',False)}
    def receive(self,timeout):raise facade.DeadlineError('ordinary simulated idle poll')
    def wait(self,timeout):
        self.calls.append('wait')
        if 'wait_error' in self.config:raise self.config['wait_error']
        self.process.returncode=self.config.get('code',0);self.raw=self.config.get('raw',self.process.returncode<<8)
        return self.process.returncode
    def abort(self,reason):
        self.calls.append('abort')
        if 'abort_error' in self.config:raise self.config['abort_error']
        self.recovery=['SIGTERM'];self.process.returncode=1;self.raw=256;return 1
    def close(self):
        self.calls.append('close')
        if 'close_error' in self.config:raise self.config['close_error']
        if not self.config.get('false_close'):self.references_closed=True
    def report(self):
        code=self.process.returncode
        facts={'callbacks_entered':int(self.callback),'callbacks_finished':int(self.callback),'callback_active':False,'cleanup':{'executor':True,'node':True,'context_shutdown':True,'context_destroy':True},'native_handle_states':{'node':'retired'}}
        return {'allocation_has_child':True,'references_closed':self.references_closed,'ready':not self.config.get('not_ready',False),'birth_authenticated':True,'started':self.started,'launch':{'entry':self.config.get('entry','heartbeat_pub'),'profile':'production','deployment':True,'nonce_sha256':'b'*64,'hashes':{'deployment_manifest':self.config.get('pin',PIN)}},'signals':[{'event':'SIGNAL_CAPABILITY_GRANTED','identity':copy.deepcopy(self.identity)}],'returncode':code,'raw_wait_status':self.raw,'accepted':bool(self.started and code==0 and self.raw==0 and not self.recovery),'errors':[],'recovery':self.recovery,'result':{'facts':facts} if code is not None else None}


def run(case,root):
    m._admit_deployment=lambda pin:pin
    config={};created=[];factory_calls=[];borrowed=Borrowed();primary=Injected('original business');cleanup=OSError('original cleanup')
    def factory(entry,output,*,expected_manifest_sha256,acquisition_receipt):
        factory_calls.append(entry);assert entry=='heartbeat_pub' and expected_manifest_sha256==PIN
        acquisition_receipt._claim()
        if config.get('before_factory'):raise primary
        backend=Backend(config);created.append(backend);acquisition_receipt._capture(backend);acquisition_receipt._phase='READY'
        if config.get('early_exit'):backend.process.returncode=1;backend.raw=256
        if config.get('after_factory'):raise primary
        return acquisition_receipt.session
    m.create_session=factory
    adapter=FixedHeartbeatAdapter(root/'owned',PIN,borrowed_context=borrowed);registry=adapter.registry;caught=[]
    def expect(fn):
        try:fn()
        except BaseException as error:caught.append(error);return error
        raise AssertionError('expected rejection/failure missing')
    def leaves(error):return sum((leaves(e) for e in error.exceptions),[]) if isinstance(error,BaseExceptionGroup) else [error]
    def begin():adapter.acquire_fixed_heartbeat();adapter.start()
    if case=='normal':
        begin();adapter.request_stop();assert adapter.wait()==0;report=adapter.close();assert report['accepted'] and report['state']=='CLOSED'
    elif case=='before-session':
        config['before_factory']=True;assert expect(adapter.acquire_fixed_heartbeat) is primary;assert not created
    elif case=='created-before-registration':
        registry._register_session=lambda:(_ for _ in ()).throw(primary);assert expect(adapter.acquire_fixed_heartbeat) is primary
    elif case=='partial-registration':
        original=registry._register_session
        def fail():original();raise primary
        registry._register_session=fail;assert expect(adapter.acquire_fixed_heartbeat) is primary;assert registry.registration_count==1
    elif case in ('ready-missing','ready-context','entry-mismatch','release-mismatch','early-exit'):
        config.update({'ready-missing':{'not_ready':True},'ready-context':{'bad_context':True},'entry-mismatch':{'entry':'tf_healthcheck'},'release-mismatch':{'pin':'0'*64},'early-exit':{'early_exit':True}}[case]);expect(adapter.acquire_fixed_heartbeat)
    elif case=='partial-factory-receipt':
        config['after_factory']=True;expect(adapter.acquire_fixed_heartbeat);assert created and registry._session is not None
    elif case=='identity-mismatch':
        begin();created[0].identity['pid']+=1;expect(adapter.observe);expect(adapter.close);assert not any(c.startswith('signal') or c=='abort' for c in created[0].calls)
    elif case=='foreign-reaper':
        config.update(wait_error=ChildProcessError('external reaper stole wait status'),abort_error=ChildProcessError('ECHILD'))
        begin();expect(adapter.wait);expect(adapter.close);assert adapter.get_cleanup_report()['raw_wait_status'] is None
    elif case=='wrong-thread':
        adapter.acquire_fixed_heartbeat();errors=[]
        def misuse():
            try:adapter.start()
            except BaseException as error:errors.append(error)
        t=threading.Thread(target=misuse);t.start();t.join();assert len(errors)==1 and isinstance(errors[0],m.WrongThreadError);adapter.close()
    elif case=='wrong-creator-thread':
        errors=[]
        def misuse():
            try:FixedHeartbeatAdapter(root/'thread-owned',PIN)
            except BaseException as error:errors.append(error)
        t=threading.Thread(target=misuse);t.start();t.join();assert isinstance(errors[0],m.WrongThreadError);assert not factory_calls;adapter.close()
    elif case=='concurrent-close':
        adapter.acquire_fixed_heartbeat();original=created[0].close;observed=[]
        def nested():
            try:adapter.close()
            except BaseException as error:observed.append(error)
            original()
        created[0].close=nested;adapter.close();assert isinstance(observed[0],m.BusyError)
    elif case=='repeat-close':
        begin();adapter.request_stop();adapter.wait();first=adapter.close();calls=list(created[0].calls);second=adapter.close();assert first==second and created[0].calls==calls
    elif case=='stop-failure':
        begin();config['stop_error']=cleanup;assert expect(adapter.request_stop) is cleanup;expect(adapter.close);assert created[0].calls.count('signal-2')==1
    elif case=='business-multiple-cleanup':
        begin();config.update(stop_error=OSError('stop'),wait_error=TimeoutError('wait'),abort_error=OSError('abort'),close_error=OSError('close'))
        group=expect(lambda:adapter.close(primary_error=primary));assert primary in leaves(group) and len(leaves(group))>=4
    elif case in ('borrowed-domain','borrowed-context'):
        before=dict(os.environ);begin();adapter.request_stop();adapter.wait();report=adapter.close();assert not borrowed.calls and report['borrowed_release_actions']==[] and os.environ==before and report['borrowed']['ros_domain_id']['released'] is False
    elif case=='file-open-failure':
        m._EvidenceJournal.open=lambda journal:(_ for _ in ()).throw(cleanup);assert expect(adapter.acquire_fixed_heartbeat) is cleanup;assert not created
    elif case=='file-close-failure':
        begin();original=m._EvidenceJournal.close
        def fail(journal):
            original(journal);journal.closed=False;journal.uncertain=True;raise cleanup
        m._EvidenceJournal.close=fail;group=expect(adapter.close);assert cleanup in leaves(group);first_calls=list(created[0].calls);expect(adapter.close);assert first_calls==created[0].calls and adapter.get_cleanup_report()['state']=='QUARANTINED'
    elif case=='journal-write-failure':
        m._EvidenceJournal.write=lambda journal,value:(_ for _ in ()).throw(cleanup);expect(adapter.acquire_fixed_heartbeat);assert not created
    elif case=='nonzero-child':
        config['code']=1;begin();error=expect(adapter.wait);assert isinstance(error,m.ChildExitError) and error.raw_wait_status==256;expect(adapter.close)
    elif case=='timeout-ownership':
        config.update(wait_error=facade.DeadlineError('wait'),abort_error=facade.DeadlineError('abort'));begin();error=expect(adapter.wait);group=expect(lambda:adapter.close(primary_error=error));assert error in leaves(group);assert adapter.get_cleanup_report()['state']=='QUARANTINED'
    elif case=='second-child':
        begin();second=FixedHeartbeatAdapter(root/'second',PIN);expect(second.acquire_fixed_heartbeat);assert len(factory_calls)==1;adapter.request_stop();adapter.wait();adapter.close()
    elif case=='repeat-acquire':
        begin();expect(adapter.acquire_fixed_heartbeat);assert len(factory_calls)==1 and not any(c.startswith('signal') for c in created[0].calls);adapter.request_stop();adapter.wait();adapter.close()
    elif case=='unapproved-entry':
        expect(lambda:FixedHeartbeatAdapter(root/'arbitrary',PIN,entry='arbitrary'));assert not factory_calls;adapter.close()
    elif case=='after-release':
        begin();adapter.request_stop();adapter.wait();adapter.close();before=list(created[0].calls);expect(adapter.start);expect(adapter.request_stop);expect(adapter.wait);assert before==created[0].calls
    elif case=='false-close-success':
        config['false_close']=True;begin();adapter.request_stop();adapter.wait();expect(adapter.close);assert adapter.get_cleanup_report()['state']=='QUARANTINED'
    elif case=='missing-raw-wait':
        config['raw']=None;begin();expect(adapter.wait);expect(adapter.close);assert adapter.get_cleanup_report()['raw_wait_status'] is None
    elif case=='repeat-stop':
        begin();adapter.request_stop();adapter.request_stop();adapter.wait();adapter.close();assert created[0].calls.count('signal-2')==1
    elif case=='receipt-consumed':
        receipt=facade.AcquisitionReceipt();receipt._claim();expect(receipt._claim);adapter.close()
    elif case=='none-release-pin':
        expect(lambda:FixedHeartbeatAdapter(root/'none-pin',None));assert not created;adapter.close()
    else:raise ValueError('unknown contract case')
    report=adapter.get_cleanup_report();assert not borrowed.calls
    return {'registry':report,'factory_calls':factory_calls,'simulated_backend_calls':[b.calls for b in created], 'caught':[{'type':type(e).__name__,'traceback':''.join(traceback.format_exception(e))} for e in caught],'scope':'controlled stand-in Session + real file IO; no native ROS child; simulated status is not a real exit code','real_child_created':False}

if __name__=='__main__':
    case=sys.argv[1];root=Path(sys.argv[2]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    try:
        data=run(case,root);data.update(id='R9-UNIT-'+case,status='PASS');code=0
    except BaseException as error:
        data={'id':'R9-UNIT-'+case,'status':'FAIL','exception':repr(error),'traceback':''.join(traceback.format_exception(error))};code=1
    (root/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(data['id'],data['status']);raise SystemExit(code)
