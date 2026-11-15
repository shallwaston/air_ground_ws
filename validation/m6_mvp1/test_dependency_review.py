"""Semantic negatives plus exact-source review; no ROS/Docker."""
import ast,json,sys,time,traceback
from pathlib import Path
C=Path(__file__).resolve().parents[2];P=C/'src/ag_network_tools/ag_network_tools';sys.path.insert(0,str(P.parent))
from ag_network_tools.strict_dependency_gate import review_mvp_sources,AdmissionError

def run():
 original={n:(P/n).read_text() for n in ['m6_owned_session.py','m6_fixed_heartbeat.py']};rows=[]
 cases={'allowed':None,'legacy-import':'from .node_runner import run_node\n','dynamic-import':"import importlib\n",'numeric-signal':'\ndef bad():\n    os.kill(1,2)\n','second-reaper':'\ndef bad():\n    os.waitpid(1,0)\n','native-handler':'import ctypes\n','new-thread':'\ndef bad():\n    threading.Thread()\n','borrowed-shutdown':'\ndef bad(borrowed_context):\n    borrowed_context.shutdown()\n','borrowed-close':'\ndef bad(borrowed_context):\n    borrowed_context.close()\n','domainpool':'from .domain_pool import DomainPool\n','exception-alias':'from .strict_entry import create_session as BaseExceptionGroup\n','builtin-dynamic':"\ndef bad():\n    __import__('os')\n"}
 for name,addition in cases.items():
  source=dict(original)
  if addition:source['m6_owned_session.py']+=addition
  try:
   result=review_mvp_sources(source)
   assert name=='allowed';status='PASS';reason=result['factory_edges']
  except AdmissionError as error:assert name!='allowed';status='PASS';reason=str(error)
  rows.append({'id':'R9-GATE-'+name,'status':status,'actual_outcome':'admitted' if name=='allowed' else 'rejected','native_ros':False,'reason':reason})
 for name,text in [('second-factory',original['m6_owned_session.py']+"\ndef bad(self):\n    create_session('heartbeat_pub', self.output, expected_manifest_sha256=self.release_pin, acquisition_receipt=self._receipt)\n"),('wrong-entry',original['m6_owned_session.py'].replace("create_session('heartbeat_pub'", "create_session('tf_healthcheck'")),('missing-receipt',original['m6_owned_session.py'].replace(',acquisition_receipt=self._receipt',''))]:
  source=dict(original);source['m6_owned_session.py']=text
  try:review_mvp_sources(source)
  except AdmissionError as error:rows.append({'id':'R9-GATE-'+name,'status':'PASS','actual_outcome':'rejected','native_ros':False,'reason':str(error)})
  else:raise AssertionError('unsafe production graph admitted')
 return rows
if __name__=='__main__':
 root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
 try:rows=run();ok=True
 except BaseException as error:rows=[{'status':'FAIL','exception':repr(error),'traceback':' '.join(traceback.format_exception(error))}];ok=False
 (root/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(root/'summary.json').write_text(json.dumps({'pass':ok,'actual':len(rows),'passed':sum(r['status']=='PASS' for r in rows)},indent=2)+'\n');print('DEPENDENCY REVIEW',ok,'ARTIFACTS',root);raise SystemExit(0 if ok else 1)
