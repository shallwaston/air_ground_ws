"""One fixed strict heartbeat capability and its own evidence journal.

This is not DomainPool, a generic ResourceScope, a signal manager or a process
adopter. All process observation/signalling/reaping is delegated to the existing
strict facade. Namespace exclusivity is a separate supervisor admission.
"""
import copy
import json
import math
import os
import secrets
import threading
import time
import traceback
from pathlib import Path

from .strict_entry import AcquisitionReceipt,StrictSession,create_session,DeadlineError,ProtocolError
from .isolated_assets import load_assets
from .strict_dependency_gate import audit_mvp_package

_SLOT_LOCK=threading.Lock()
_ACTIVE_GENERATION=None
_ACTIVE_OWNER=None

class OwnershipError(RuntimeError):pass
class StateError(OwnershipError):pass
class WrongThreadError(OwnershipError):pass
class BusyError(OwnershipError):pass
class IdentityError(OwnershipError):pass
class UnresolvedResponsibility(OwnershipError):pass
class ChildExitError(OwnershipError):
    def __init__(self,code,raw,report):
        super().__init__('owned child nonzero/unaccepted exit: '+str(code)+' raw='+str(raw))
        self.returncode=code;self.raw_wait_status=raw;self.child_report=report


def _error(error):
    try:message=str(error)
    except BaseException:message='<exception string unavailable; original object retained>'
    try:formatted=''.join(traceback.format_exception(error))
    except BaseException:formatted='<exception formatting unavailable; original traceback retained>'
    return {'type':type(error).__name__,'id':id(error),'message':message,
            'traceback':formatted,
            'children':[_error(e) for e in error.exceptions] if isinstance(error,BaseExceptionGroup) else []}


def _admit_deployment(pin):
    package=Path(__file__).resolve().parent
    assets=load_assets(package)
    if assets['manifest_sha256']!=pin:raise IdentityError('MVP release identity mismatch')
    audit_mvp_package(package)
    return assets['manifest_sha256']


class _EvidenceJournal:
    """Only a new exclusive file; no caller-supplied closer or borrowed file."""
    def __init__(self,directory):
        self.directory=directory;self.stream=None;self.opened=False;self.close_attempted=False
        self.closed=False;self.uncertain=False;self.rows=0
    def open(self):
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=False)
        path=self.directory/'ownership.jsonl'
        self.stream=path.open('x',encoding='utf-8');self.opened=True
        path.chmod(0o600)
    def write(self,value):
        if self.stream is None or self.close_attempted:raise StateError('journal not writable')
        self.stream.write(json.dumps(value,sort_keys=True)+'\n');self.stream.flush();self.rows+=1
    def close(self):
        if self.close_attempted:return
        self.close_attempted=True
        if not self.opened:self.closed=True;return
        try:self.stream.close()
        except BaseException:
            self.uncertain=True;raise  # retire object; never blindly retry an uncertain close
        self.closed=True
    def report(self):
        return {'owned':self.opened,'opened':self.opened,'close_attempted':self.close_attempted,
                'closed_proven':self.closed,'uncertain':self.uncertain,'rows':self.rows,
                'path':str(self.directory/'ownership.jsonl')}


class OwnedSessionRegistry:
    """Single-use, one-slot registry. Borrowed objects are metadata, not closers."""
    def __init__(self,output,release_manifest_sha256,*,borrowed_context=None):
        if threading.current_thread() is not threading.main_thread():raise WrongThreadError('MVP creator must be main thread')
        if type(release_manifest_sha256) is not str or len(release_manifest_sha256)!=64 or any(c not in '0123456789abcdef' for c in release_manifest_sha256):raise ValueError('explicit 64-character lowercase release pin required')
        self.output=Path(output);self.release_pin=release_manifest_sha256
        self.creator_pid=os.getpid();self.creator_thread=threading.current_thread();self.creator_native_tid=threading.get_native_id()
        self.generation=secrets.token_hex(16);self.state='NEW';self._busy=None;self._slot_owned=False
        self._session=None;self._receipt=None;self._journal=None;self._registered=False;self.registration_count=0
        self._identity=None;self._identity_trusted=True;self._user_started=False;self._cleanup_started=False
        self._stop_attempted=False;self._stop_requested=False;self._wait_attempted=False;self._raw=None;self._code=None
        self._history=[];self._close_errors=[];self._cached=None;self._last_strict=None
        self.borrowed={'ros_domain_id':{'value':42,'ownership':'BORROWED','released':False},
                       'container_and_image':{'ownership':'BORROWED','actions':[]},
                       'parent_context':{'ownership':'BORROWED','object_id':id(borrowed_context) if borrowed_context is not None else None,'type':type(borrowed_context).__module__+'.'+type(borrowed_context).__qualname__,'actions':[]},
                       'foreign_handlers_threads_processes_and_dds':{'ownership':'BORROWED','actions':[]}}
        _admit_deployment(self.release_pin)
    def _enter(self,operation):
        if os.getpid()!=self.creator_pid or threading.current_thread() is not self.creator_thread:raise WrongThreadError('creator PID and exact thread object required')
        if self._busy is not None:raise BusyError('operation already in flight: '+self._busy)
        self._busy=operation
    def _leave(self):self._busy=None
    def _claim_slot(self):
        global _ACTIVE_GENERATION,_ACTIVE_OWNER
        with _SLOT_LOCK:
            if _ACTIVE_GENERATION is not None:raise BusyError('another MVP registry retains its one live/uncertain slot')
            _ACTIVE_GENERATION=self.generation;_ACTIVE_OWNER=self;self._slot_owned=True
    def _release_slot(self):
        global _ACTIVE_GENERATION,_ACTIVE_OWNER
        if not self._slot_owned:return
        with _SLOT_LOCK:
            if _ACTIVE_GENERATION!=self.generation or _ACTIVE_OWNER is not self:raise IdentityError('MVP slot generation mismatch')
            _ACTIVE_GENERATION=None;_ACTIVE_OWNER=None;self._slot_owned=False
    def _emit(self,event,**fields):
        if self._journal is not None and self._journal.opened:
            self._journal.write({'event':event,'time_ns':time.time_ns(),'generation':self.generation,'state':self.state,**fields})
    def _remember(self,session):
        if not isinstance(session,StrictSession):raise IdentityError('factory did not return a strict capability')
        if self._session is not None and self._session is not session:raise IdentityError('second or foreign capability refused')
        self._session=session
    def _receipt_capture(self):
        if self._session is None and self._receipt is not None and self._receipt.session is not None:self._remember(self._receipt.session)
    def _stable_identity(self,report):
        grants=[x['identity'] for x in report['signals'] if x['event']=='SIGNAL_CAPABILITY_GRANTED']
        if len(grants)!=1:raise IdentityError('one authenticated owned birth required')
        value=grants[0]
        if value['ppid']!=self.creator_pid:raise IdentityError('capability is not this creator direct child')
        return {'birth':copy.deepcopy(value),'nonce_sha256':report['launch']['nonce_sha256'],
                'entry':report['launch']['entry'],'release':report['launch']['hashes']['deployment_manifest']}
    def _report_strict(self):
        report=self._session.report();self._last_strict=copy.deepcopy(report)
        if self._identity is not None:
            try:
                if self._stable_identity(report)!=self._identity:raise IdentityError('registered session identity changed')
            except BaseException:
                self._identity_trusted=False;raise
        return report
    def _register_session(self):
        if self._registered:raise StateError('same Session cannot be registered twice')
        if self._receipt.session is not self._session:raise IdentityError('receipt/capability mismatch')
        report=self._report_strict()
        if not report['ready'] or not report['birth_authenticated'] or report['started']:raise IdentityError('factory did not return an unstarted verified READY Session')
        identity=self._stable_identity(report)
        if identity['entry']!='heartbeat_pub' or identity['release']!=self.release_pin or not report['launch']['deployment'] or report['launch']['profile']!='production':raise IdentityError('wrong fixed production entry or release')
        if report['returncode'] is not None or report['raw_wait_status'] is not None:raise IdentityError('child exited before registration')
        status=self._session.query(5)
        if not status['context_ok'] or status['stop']:raise IdentityError('READY liveness/context mismatch')
        self._identity=identity;self._registered=True;self.registration_count=1;self.state='READY'
        self._emit('session-registered',identity=identity,registration_count=1)
    def acquire_fixed_heartbeat(self):
        self._enter('acquire');primary=None;capture_errors=[]
        if self.state!='NEW':
            self._leave();raise StateError('registry is single-use; existing ownership untouched')
        try:
            self._claim_slot();self.state='ACQUIRING'
            self._journal=_EvidenceJournal(self.output);self._journal.open();self._emit('journal-owned')
            self._receipt=AcquisitionReceipt()
            received=create_session('heartbeat_pub',self.output/'strict-child',expected_manifest_sha256=self.release_pin,acquisition_receipt=self._receipt)
            self._remember(received);self._register_session()
        except BaseException as error:
            primary=error;self._history.append(error)
            try:self._receipt_capture()
            except BaseException as capture:capture_errors.append(capture)
        finally:self._leave()
        if primary is not None:
            if capture_errors:primary=BaseExceptionGroup('acquisition and receipt registration failed',[primary,*capture_errors])
            return self.close(primary_error=primary)
        return self.observe()
    def start(self):
        self._enter('start')
        try:
            if self.state!='READY':raise StateError('only READY can START')
            self._report_strict();self._session.start();self._user_started=True;self.state='RUNNING';self._emit('started')
        except BaseException as error:self._history.append(error);raise
        finally:self._leave()
    def _stop(self):
        if self._stop_attempted:return
        self._stop_attempted=True;self._report_strict()
        if not self._identity_trusted:raise IdentityError('unknown identity cannot receive a stop')
        self._session.request_stop(2);self._stop_requested=True;self.state='STOP_REQUESTED';self._emit('stop-requested',signal=2)
    def request_stop(self):
        self._enter('request-stop')
        try:
            if self.state not in ('READY','RUNNING','STOP_REQUESTED'):raise StateError('stop not available in this state')
            self._stop()
        except BaseException as error:self._history.append(error);raise
        finally:self._leave()
    def _wait(self,timeout):
        if self._raw is not None:return self._code
        if self._wait_attempted:raise StateError('wait already failed; no production retry')
        self._wait_attempted=True
        code=self._session.wait(timeout);report=self._report_strict();raw=report['raw_wait_status']
        if raw is None:raise UnresolvedResponsibility('direct raw wait status missing')
        self._code=code;self._raw=raw;self.state='REAPED';self._emit('reaped',returncode=code,raw_wait_status=raw)
        if code!=0 or raw!=0 or not report['accepted']:raise ChildExitError(code,raw,report)
        return code
    def wait(self,timeout=10):
        self._enter('wait')
        try:
            if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=10:raise ValueError('bounded wait in (0,10] required')
            if self.state not in ('RUNNING','STOP_REQUESTED','REAPED'):raise StateError('wait requires a started/stopping child')
            return self._wait(timeout)
        except BaseException as error:self._history.append(error);raise
        finally:self._leave()
    def observe(self):
        self._enter('observe')
        try:
            if self._cached is not None:return copy.deepcopy(self._cached)
            report=self._report_strict() if self._session is not None else None
            if report is not None and self._user_started and report['returncode'] is None:
                try:self._session.receive(0.001)
                except DeadlineError:pass  # ordinary bounded telemetry poll, not a failed wait
                except ProtocolError as error:
                    if str(error)!='private child channel EOF':
                        self._identity_trusted=False;self._history.append(error);raise
                report=self._report_strict()
            return self._snapshot(report,False)
        finally:self._leave()
    def _snapshot(self,report,complete):
        facts=report.get('result',{}).get('facts',{}) if report and report.get('result') else {}
        closed_refs=self._session is None or bool(report and report.get('references_closed'))
        journal=self._journal.report() if self._journal is not None else {'owned':False,'closed_proven':True,'uncertain':False}
        errors=self._history+self._close_errors
        accepted=bool(complete and self._user_started and self._registered and self._raw==0 and self._code==0 and report and report['accepted'] and facts.get('callbacks_entered',0)>=1 and not errors)
        outstanding=[]
        if self._session is not None and not closed_refs:outstanding.append('strict-session/reap/reference responsibility')
        if not journal['closed_proven']:outstanding.append('owned evidence journal close responsibility')
        return {'generation':self.generation,'creator':{'pid':self.creator_pid,'native_tid':self.creator_native_tid,'thread_name':self.creator_thread.name},'state':self.state,'registration_count':self.registration_count,'registered':self._registered,'ready_verified':self._registered,'user_started':self._user_started,'stop_attempted':self._stop_attempted,'stop_requested':self._stop_requested,'wait_attempted':self._wait_attempted,'returncode':self._code,'raw_wait_status':self._raw,'child_identity':self._identity,'strict_report':report,'acquisition_receipt':self._receipt.snapshot() if self._receipt is not None else None,'owned':{'session_materialized':self._session is not None,'session_references_closed_proven':closed_refs,'journal':journal},'borrowed':copy.deepcopy(self.borrowed),'borrowed_release_actions':[],'cleanup_complete':complete,'accepted':accepted,'outstanding_responsibilities':outstanding,'errors':[_error(e) for e in errors],'single_slot_retained':self._slot_owned}
    def _raise_errors(self,primary=None):
        all_errors=[]
        for error in ([primary] if primary is not None else [])+self._history+self._close_errors:
            if not any(error is known for known in all_errors):all_errors.append(error)
        if not all_errors:return
        if len(all_errors)==1 and not self._close_errors:raise all_errors[0].with_traceback(all_errors[0].__traceback__)
        group=BaseExceptionGroup('MVP operation and independent cleanup failed',all_errors);group.owned_registry=self;raise group
    def close(self,*,primary_error=None):
        try:self._enter('close')
        except BaseException as admission:
            if primary_error is not None:raise BaseExceptionGroup('operation and close admission failed',[primary_error,admission])
            raise
        try:
            if self._cached is not None:
                self._raise_errors(primary_error);return copy.deepcopy(self._cached)
            self.state='CLOSING';self._cleanup_started=True
            if primary_error is not None and not any(primary_error is e for e in self._history):self._history.append(primary_error)
            report=None
            if self._session is not None:
                try:
                    report=self._report_strict()
                    if report['raw_wait_status'] is not None:self._raw=report['raw_wait_status'];self._code=report['returncode']
                except BaseException as error:self._close_errors.append(error)
                if report is not None and not report.get('references_closed') and self._identity_trusted:
                    has_child=report.get('allocation_has_child',True)
                    if has_child and report['returncode'] is None:
                        if self._registered and not self._stop_attempted:
                            try:self._stop()
                            except BaseException as error:self._close_errors.append(error)
                        if self._registered and not self._user_started and self._stop_requested:
                            try:
                                status=self._session.query(5)
                                if not status['stop']:raise UnresolvedResponsibility('pre-START stop not acknowledged')
                                self._session.start()
                            except BaseException as error:self._close_errors.append(error)
                        if self._registered and not self._wait_attempted:
                            try:self._wait(10)
                            except BaseException as error:self._close_errors.append(error)
                        try:report=self._report_strict()
                        except BaseException as error:self._close_errors.append(error);report=None
                        if report is not None and report['returncode'] is None:
                            try:self._session.abort_failed_supervision('MVP failed supervision cleanup, never normal acceptance')
                            except BaseException as error:self._close_errors.append(error)
                    try:
                        report=self._report_strict()
                        if not report.get('allocation_has_child',True) or (report['returncode'] is not None and report['raw_wait_status'] is not None):
                            self._session.close();report=self._report_strict()
                            if report['raw_wait_status'] is not None:self._raw=report['raw_wait_status'];self._code=report['returncode']
                        else:raise UnresolvedResponsibility('live/unknown direct child retains ownership')
                    except BaseException as error:self._close_errors.append(error)
            closed_refs=self._session is None or bool(report and report.get('references_closed'))
            try:self._emit('close-result-before-journal-close',session_references_closed=closed_refs,raw_wait_status=self._raw,errors=[_error(e) for e in self._history+self._close_errors])
            except BaseException as error:self._close_errors.append(error)
            if self._journal is not None:
                try:self._journal.close()
                except BaseException as error:self._close_errors.append(error)
            journal_closed=self._journal is None or self._journal.closed
            if not closed_refs:self._close_errors.append(UnresolvedResponsibility('strict Session closure is not proven'))
            if not journal_closed:self._close_errors.append(UnresolvedResponsibility('journal closure is not proven; object retired without retry'))
            complete=bool(closed_refs and journal_closed)
            if complete:
                try:self._release_slot()
                except BaseException as error:self._close_errors.append(error);complete=False
            self.state='CLOSED' if complete else 'QUARANTINED'
            self._cached=self._snapshot(report or self._last_strict,complete)
            self._raise_errors(primary_error);return copy.deepcopy(self._cached)
        finally:self._leave()
    def get_cleanup_report(self):
        self._enter('cleanup-report')
        try:return copy.deepcopy(self._cached) if self._cached is not None else self._snapshot(self._last_strict,False)
        finally:self._leave()
    def get_residual_owner(self):
        self._enter('residual-owner')
        try:
            if self.state!='QUARANTINED':raise StateError('no quarantined responsibility')
            return self._session
        finally:self._leave()
