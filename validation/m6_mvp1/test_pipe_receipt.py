"""A real second-pipe failure must retire the already owned first pipe.
No child is spawned; constructor fault is before Popen. Test closes only its
own captured pipe pair after a failing verdict, never changes that verdict.
"""
import hashlib,json,os,sys,traceback,types
from pathlib import Path
C=Path(__file__).resolve().parents[2];sys.path.insert(0,str(C/'src/ag_network_tools'))
from ag_network_tools import strict_entry as facade,isolated_runner as ir
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
original_policy=facade.RuntimePolicy;original_pipe=ir.os.pipe2;original_seal=ir.seal;calls=[];captured=[];primary=OSError('injected second pipe allocation error');error=None;caught=None;before=set(os.listdir('/proc/self/fd'));receipt=facade.AcquisitionReceipt();snapshot=None;leaked=[]
policy=types.SimpleNamespace(ros=True,deployment=True,assets={'manifest_sha256':'a'*64,'manifest':{'native':[]}},bootstrap=b'never executed',probe_bytes=b'never executed',bundle_bytes=b'never executed',paths=[],manifest={},native_roots=[],bundle_members={},hashes={})
def pipe(flags):
    calls.append(True)
    if len(calls)==2:raise primary
    pair=original_pipe(flags);captured.extend(pair);return pair
try:
    facade.RuntimePolicy=lambda **kw:policy;ir.os.pipe2=pipe;ir.seal=lambda name,data:os.open('/dev/null',os.O_RDONLY)
    try:facade.create_session('heartbeat_pub',root/'owned',expected_manifest_sha256='a'*64,acquisition_receipt=receipt)
    except BaseException as failure:caught=failure
    snapshot=receipt.snapshot();leaked=sorted(set(os.listdir('/proc/self/fd'))-before)
    assert caught is primary
    assert len(calls)==2 and len(captured)==2
    assert not leaked,('unregistered real first-pipe descriptors survived',leaked)
    assert snapshot['references_closed'] and not snapshot['has_child']
except BaseException as failure:error=failure
finally:
    facade.RuntimePolicy=original_policy;ir.os.pipe2=original_pipe;ir.seal=original_seal
    # Explicitly separate fixture cleanup from failed evidence. File objects
    # may have reused an integer, so close only those still proven pipe objects.
    cleanup=[]
    for fd in captured:
        try:
            target=os.readlink('/proc/self/fd/'+str(fd))
            if target.startswith('pipe:['):os.close(fd);cleanup.append(fd)
        except FileNotFoundError:pass
row={'id':'R9-ACQUISITION-second-pipe','status':'PASS' if error is None else 'FAIL','no_child_created':True,'fixture_sealed_memfd_replaced_by_owned_devnull_fd_before_any_child_creation':True,'actual_fd_delta_at_verdict':leaked,'first_pipe_fds':captured,'fixture_cleanup_after_verdict':cleanup,'receipt':snapshot,'runner_sha256':hashlib.sha256(Path(ir.__file__).read_bytes()).hexdigest(),'original_exception_same_object':caught is primary,'caught_exception_traceback':''.join(traceback.format_exception(caught)) if caught else None}
if error:row.update(exception=repr(error),traceback=''.join(traceback.format_exception(error)))
(root/'results.json').write_text(json.dumps([row],indent=2)+'\n');(root/'summary.json').write_text(json.dumps({'pass':error is None,'actual':1,'passed':int(error is None),'failed':int(error is not None)},indent=2)+'\n');print(row['id'],row['status'],'ARTIFACTS',root);raise SystemExit(int(error is not None))
