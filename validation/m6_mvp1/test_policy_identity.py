import json,shutil,sys,traceback
from pathlib import Path
C=Path(__file__).resolve().parents[2];P=C/'src/ag_network_tools/ag_network_tools';sys.path.insert(0,str(P.parent))
from ag_network_tools.strict_dependency_gate import audit_mvp_package,AdmissionError

def run(root):
 rows=[]
 for kind in ['positive','registry-tamper','policy-tamper','backend-tamper','unsafe-permission','symlink-source']:
  package=root/kind;shutil.copytree(P,package)
  if kind=='registry-tamper':p=package/'m6_owned_session.py';p.write_bytes(p.read_bytes()+b'\n# not reviewed')
  if kind=='backend-tamper':p=package/'isolated_runner.py';p.write_bytes(p.read_bytes()+b'\n# not reviewed')
  if kind=='policy-tamper':p=package/'_m6_mvp_policy.json';p.write_bytes(p.read_bytes()+b'\n')
  if kind=='unsafe-permission':(package/'m6_owned_session.py').chmod(0o664)
  if kind=='symlink-source':p=package/'m6_owned_session.py';p.unlink();p.symlink_to(P/'m6_owned_session.py')
  try:
   result=audit_mvp_package(package);assert kind=='positive' and result['pass'];outcome='admitted'
  except AdmissionError as error:assert kind!='positive';outcome='rejected'
  rows.append({'id':'R9-POLICY-'+kind,'status':'PASS','outcome':outcome,'no_session_spawned':True})
 return rows
if __name__=='__main__':
 root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False)
 try:rows=run(root);ok=True
 except BaseException as error:rows=[{'status':'FAIL','exception':repr(error),'traceback':' '.join(traceback.format_exception(error))}];ok=False
 (root/'results.json').write_text(json.dumps(rows,indent=2)+'\n');(root/'summary.json').write_text(json.dumps({'pass':ok,'actual':len(rows),'passed':sum(r['status']=='PASS' for r in rows)},indent=2)+'\n');print('POLICY IDENTITY',ok,'ARTIFACTS',root);raise SystemExit(0 if ok else 1)
