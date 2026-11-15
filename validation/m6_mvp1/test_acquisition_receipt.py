"""Real parent FD allocation tests; no ROS import or child creation."""
import json,os,sys,tempfile,traceback,types
from pathlib import Path
C=Path(__file__).resolve().parents[2];sys.path.insert(0,str(C/'src/ag_network_tools'))
from ag_network_tools import strict_entry as facade,isolated_runner as ir


def run(root):
    rows=[]
    for kind in ('stderr-open','diagnostic-and-seal','receipt-reuse'):
        before=set(os.listdir('/proc/self/fd'));out=root/kind;original_open=Path.open;original_write=Path.write_text;original_seal=ir.seal;original_policy=facade.RuntimePolicy
        primary=OSError('original allocation failure');diagnostic=OSError('original diagnostic write failure');receipt=facade.AcquisitionReceipt();caught=None
        policy=types.SimpleNamespace(ros=True,deployment=True,assets={'manifest_sha256':'a'*64},bootstrap=b'never executed')
        facade.RuntimePolicy=lambda **kw:policy
        try:
            if kind=='stderr-open':
                def open_fault(path,*args,**kwargs):
                    if path.name=='stderr.log':raise primary
                    return original_open(path,*args,**kwargs)
                Path.open=open_fault
            elif kind=='diagnostic-and-seal':
                def seal_fault(*args,**kwargs):raise primary
                def write_fault(path,*args,**kwargs):
                    if path.name=='launch-failure.json':raise diagnostic
                    return original_write(path,*args,**kwargs)
                ir.seal=seal_fault;Path.write_text=write_fault
            else:receipt._claim()
            try:facade.create_session('heartbeat_pub',out,expected_manifest_sha256='a'*64,acquisition_receipt=receipt)
            except BaseException as error:caught=error
            else:raise AssertionError('injected failure missing')
            if kind=='stderr-open':assert caught is primary
            elif kind=='diagnostic-and-seal':assert isinstance(caught,BaseExceptionGroup) and list(caught.exceptions)==[primary,diagnostic]
            else:assert isinstance(caught,ValueError) and not out.exists()
            snapshot=receipt.snapshot()
            if kind!='receipt-reuse':assert snapshot['has_child'] is False and snapshot['references_closed'] is True
            assert set(os.listdir('/proc/self/fd'))==before
            rows.append({'id':'R9-ACQUISITION-'+kind,'status':'PASS','native_ros':False,'actual_parent_fd_delta':[],'no_child_created':True,'receipt':snapshot,'exception_type':type(caught).__name__,'traceback':''.join(traceback.format_exception(caught))})
        finally:Path.open=original_open;Path.write_text=original_write;ir.seal=original_seal;facade.RuntimePolicy=original_policy
    return rows
if __name__=='__main__':
    root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    try:rows=run(root);ok=True
    except BaseException as error:rows=[{'status':'FAIL','exception':repr(error),'traceback':' '.join(traceback.format_exception(error))}];ok=False
    (root/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(root/'summary.json').write_text(json.dumps({'pass':ok,'planned':3,'actual':len(rows),'passed':sum(r['status']=='PASS' for r in rows)},indent=2)+'\n');print('ACQUISITION',ok,'ARTIFACTS',root);raise SystemExit(0 if ok else 1)
