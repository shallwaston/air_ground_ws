import ast,hashlib,importlib,inspect,json,os,sys
from pathlib import Path
from ament_index_python.packages import get_package_prefix
C=Path(__file__).resolve().parents[2];A=C.parent
packages=[p.parent.name for p in (C/'src').glob('*/package.xml')]
result={'packages':[],'entrypoints':[],'environment':{k:os.environ.get(k) for k in ['AMENT_PREFIX_PATH','CMAKE_PREFIX_PATH','COLCON_PREFIX_PATH','PYTHONPATH','LD_LIBRARY_PATH','ROS_DOMAIN_ID','RMW_IMPLEMENTATION','ROS_AUTOMATIC_DISCOVERY_RANGE']},'python':sys.version}
for name in sorted(packages):
 prefix=Path(get_package_prefix(name));assert prefix==C/'install'/name
 result['packages'].append({'package':name,'prefix':str(prefix),'pass':True})
for setup in sorted((C/'src').glob('*/setup.py')):
 for n in ast.walk(ast.parse(setup.read_text())):
  if isinstance(n,ast.keyword) and n.arg=='entry_points':
   for item in ast.literal_eval(n.value)['console_scripts']:
    name,target=item.split('=',1);module,function=target.strip().split(':');m=importlib.import_module(module);f=getattr(m,function);path=Path(inspect.getfile(f));assert path.resolve().is_relative_to(C)
    installed=C/'install'/setup.parent.name/'lib'/setup.parent.name/name.strip();assert installed.is_file() and os.access(installed,os.X_OK)
    result['entrypoints'].append({'entry':name.strip(),'module':module,'source':str(path),'installed':str(installed),'source_real':str(path.resolve()),'pass':True})
assert len(packages)==7 and len(result['entrypoints'])==21
assert not any('/air_ground_ws/' in v or '/air-ground-r1-' in v or '/air-ground-r3-' in v for v in result['environment'].values() if v)
(Path(sys.argv[1]) if len(sys.argv)>1 else A/'runtime/installation-check.json').write_text(json.dumps(result,indent=2)+'\n');print('7 package prefixes + 21 installed entrypoints verified')
