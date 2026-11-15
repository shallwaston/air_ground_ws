"""The sole approved opt-in R7 production facade. No arbitrary Node/argv/probe.

Existing legacy consoles are unchanged. Parent signal handlers/masks are never
installed or taken over. A parent owner must explicitly request child stopping.
"""
import argparse,copy,json,os,secrets,threading,time
from pathlib import Path
from .isolated_entries import ENTRIES
from .isolated_runner import RuntimePolicy,IsolatedSession,DeadlineError,ProtocolError

class AcquisitionReceipt:
    """Public provisional receipt, never an authority to adopt an external PID.

    The facade binds its own allocated backend before constructor side effects.
    Caller receives only the existing opaque StrictSession after materialization.
    An empty object is a provisional record, not invented child ownership.
    """
    def __init__(self):
        self.generation=secrets.token_hex(16);self._creator_pid=os.getpid();self._thread=threading.current_thread()
        self._claimed=False;self._backend=None;self._session=None;self._phase='NEW';self._errors=[]
    def _check(self):
        if os.getpid()!=self._creator_pid or threading.current_thread() is not self._thread:raise RuntimeError('acquisition receipt creator mismatch')
    def _claim(self):
        self._check()
        if self._claimed:raise ValueError('acquisition receipt already consumed')
        self._claimed=True;self._phase='CLAIMED'
    def _capture(self,backend):
        self._check();self._backend=backend;self._phase='PROVISIONAL_OBJECT'
    def _materialize(self):
        self._check()
        if self._backend is not None and getattr(self._backend,'allocation_initialized',False) and self._session is None:self._session=StrictSession(self._backend)
    @property
    def session(self):
        self._materialize();return self._session
    def snapshot(self):
        self._check();self._materialize();report=self._session.report() if self._session is not None else None
        return copy.deepcopy({'generation':self.generation,'creator_pid':self._creator_pid,'phase':self._phase,'claimed':self._claimed,'materialized_session':self._session is not None,'has_child':bool(report and report['allocation_has_child']),'references_closed':bool(report and report['references_closed']),'no_resource_allocation':self._backend is None or not getattr(self._backend,'allocation_initialized',False),'report':report,'errors':self._errors})

class StrictSession:
    """One creator thread owns observation, signalling, waitpid and close."""
    def __init__(self,session):self._session=session
    def start(self):return self._session.start()
    def request_stop(self,number=2):return self._session.signal(number,'approved-interface-request')
    def receive(self,timeout=1):return self._session.receive(timeout)
    def query(self,timeout=5):return self._session.query(timeout)
    def wait(self,timeout=10):return self._session.wait(timeout)
    def report(self):return self._session.report()
    def close(self):return self._session.close()
    def abort_failed_supervision(self,reason):return self._session.abort(reason)

def create_session(entry,output,*,expected_manifest_sha256=None,acquisition_receipt=None):
    if entry not in ENTRIES:raise ValueError('entry is not approved for strict deployment')
    receipt=acquisition_receipt if acquisition_receipt is not None else AcquisitionReceipt()
    if not isinstance(receipt,AcquisitionReceipt):raise TypeError('typed acquisition receipt required')
    receipt._claim()
    try:
        policy=RuntimePolicy(ros=True,deployment=True)
        if expected_manifest_sha256 is not None and policy.assets['manifest_sha256']!=expected_manifest_sha256:
            raise RuntimeError('caller bound release identity mismatch')
        # Anchor the exact object before constructor allocation; no callback,
        # new signal sender, reaper, or arbitrary PID adoption is introduced.
        session=IsolatedSession.__new__(IsolatedSession);receipt._capture(session)
        IsolatedSession.__init__(session,policy,output,entry=entry,ros_args=tuple(ENTRIES[entry]['args']))
        public=receipt.session;receipt._phase='CREATED'
    except BaseException:
        receipt._phase='CREATION_FAILED';receipt._materialize();raise
    try:
        session.authenticate_birth();session.admit();session.await_ready(start=False)
    except BaseException as primary:
        errors=[]
        if session.process.returncode is None:
            try:session.abort('strict facade admission failed')
            except BaseException as cleanup:errors.append(cleanup)
        try:(Path(output)/'supervision.json').write_text(json.dumps(session.report(),indent=2)+'\n')
        except BaseException as cleanup:errors.append(cleanup)
        if session.process.returncode is not None:
            try:session.close()
            except BaseException as cleanup:errors.append(cleanup)
        receipt._phase='ADMISSION_FAILED';receipt._errors=[repr(e) for e in errors]
        if errors:
            combined=BaseExceptionGroup('strict admission and cleanup failed',[primary,*errors]);combined.supervision=session;combined.acquisition_receipt=receipt;raise combined
        raise
    receipt._phase='READY';return public

def main(argv=None,*,expected_manifest_sha256=None):
    p=argparse.ArgumentParser(description='Explicit fixed-config strict Jazzy exec; no legacy fallback')
    p.add_argument('--entry',required=True,choices=tuple(ENTRIES));p.add_argument('--output',required=True,type=Path)
    p.add_argument('--run-for',type=float,help='optional planned lifetime, then an owned SIGINT; not a failure/retry timeout')
    args=p.parse_args(argv)
    if args.run_for is not None and not 0<args.run_for<=3600:p.error('--run-for must be in (0,3600]')
    owned=None;primary=None;errors=[];code=None
    try:
        owned=create_session(args.entry,args.output,expected_manifest_sha256=expected_manifest_sha256);owned.start();started=time.monotonic();stop_started=None
        while True:
            try:
                if args.run_for is not None and stop_started is None and time.monotonic()-started>=args.run_for:
                    try:owned.request_stop(2)
                    except ProcessLookupError:pass  # same bound pidfd already reports exit, never a new target
                    stop_started=time.monotonic()
                if stop_started is not None and time.monotonic()-stop_started>10:raise DeadlineError('approved child stop deadline exceeded')
                try:owned.receive(0.1)
                except DeadlineError:continue
                except ProtocolError as error:
                    if str(error)=='private child channel EOF':break
                    raise
            except KeyboardInterrupt:
                # Honor the parent's existing Python semantics, without
                # modifying its handler. Only the authenticated child is sent.
                try:owned.request_stop(2)
                except ProcessLookupError:pass
                if stop_started is None:stop_started=time.monotonic()
        code=owned.wait()
        if code==0 and not owned.report()['accepted']:raise RuntimeError('raw child exit0 did not satisfy strict acceptance')
    except BaseException as error:
        primary=error
        if owned is not None and owned._session.process.returncode is None:
            try:owned.abort_failed_supervision('strict CLI supervision failed')
            except BaseException as cleanup:errors.append(cleanup)
    finally:
        if owned is not None:
            try:(args.output/'supervision.json').write_text(json.dumps(owned.report(),indent=2)+'\n')
            except BaseException as cleanup:errors.append(cleanup)
            if owned._session.process.returncode is not None:
                try:owned.close()
                except BaseException as cleanup:errors.append(cleanup)
    if errors:
        combined=BaseExceptionGroup('strict supervision and cleanup failed',([primary] if primary else [])+errors);combined.supervision=owned;raise combined
    if primary is not None:raise primary.with_traceback(primary.__traceback__)
    return code if code>=0 else 128-code

if __name__=='__main__':raise SystemExit(main())
