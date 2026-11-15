"""Unpatched installed production API + actual DDS subscriber and raw wait.

Run in the admitted fixed container with python3 -I -S -B and R9 overlay.
Only the subscriber belongs to this validation harness, not to M6's registry.
"""
import json,os,signal,sys,time,traceback
from pathlib import Path
C=Path(__file__).resolve().parents[2];A=C.parent
script=C/'install/ag_network_tools/lib/ag_network_tools/ag_strict_isolated'
namespace={'__name__':'r9_verified_api_loader','__file__':str(script)}
exec(compile(script.read_bytes(),str(script),'exec'),namespace)
verified=namespace['load_verified_package']()
from ag_network_tools.isolated_runner import RuntimePolicy
policy=RuntimePolicy(ros=True,deployment=True)
# These are the backend-verified root Jazzy paths plus this candidate's own
# generated interface prefix, solely for the external validation subscriber.
for path in policy.paths:
    if path not in sys.path:sys.path.append(path)
interface=C/'install/ag_interfaces/lib/python3.12/site-packages';assert interface.is_dir();sys.path.insert(0,str(interface))
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions,get_current_signal_handlers_options
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from ag_interfaces.msg import Heartbeat
from ag_network_tools import m6_fixed_heartbeat as production,m6_owned_session as registry_module,strict_entry
from ag_network_tools.isolated_probe import ActionReader
assert registry_module.create_session is strict_entry.create_session
assert type(production.__loader__).__name__=='VerifiedSources' and type(registry_module.__loader__).__name__=='VerifiedSources'
assert Path(production.__file__).resolve().is_relative_to(C) and Path(registry_module.__file__).resolve().is_relative_to(C)
root=Path(sys.argv[1]);root.mkdir(mode=0o700,parents=True,exist_ok=False);messages=[];context=None;node=None;executor=None;adapter=None;primary=None;cleanup_errors=[];started=time.monotonic()
reader=ActionReader(verified['package']/'strict_assets/probe.so')
def parent_state():
    return {'context_id':id(context),'context_ok':context.ok(),'executor_context_id':id(executor.context),'node_context_id':id(node.context),'handlers':{str(n):repr(signal.getsignal(n)) for n in (2,15)},'native_options':str(get_current_signal_handlers_options()),'actions':reader.actions(),'mask':reader.mask(),'domain':os.environ.get('ROS_DOMAIN_ID'),'rmw':os.environ.get('RMW_IMPLEMENTATION'),'discovery':os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')}
def message(message):
    messages.append({'type':'ag_interfaces/msg/Heartbeat','node_name':message.node_name,'role':message.role,'status':message.status,'detail':message.detail,'frame_id':message.header.frame_id,'stamp_ns':message.header.stamp.sec*10**9+message.header.stamp.nanosec})
try:
    assert os.environ['ROS_DOMAIN_ID']=='42' and os.environ['RMW_IMPLEMENTATION']=='rmw_fastrtps_cpp' and os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']=='LOCALHOST'
    context=Context();rclpy.init(context=context,signal_handler_options=SignalHandlerOptions.NO)
    node=Node('r9_mvp_external_subscriber',context=context);executor=SingleThreadedExecutor(context=context);executor.add_node(node)
    qos=QoSProfile(depth=20,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)
    node.create_subscription(Heartbeat,'/system/heartbeat',message,qos)
    before=parent_state();adapter=production.FixedHeartbeatAdapter(root/'owned',verified['manifest_sha256'],borrowed_context=context)
    acquired=adapter.acquire_fixed_heartbeat();assert acquired['ready_verified'] and acquired['registration_count']==1 and not acquired['user_started']
    adapter.start();deadline=time.monotonic()+10
    while len(messages)<2:
        if time.monotonic()>=deadline:raise TimeoutError('actual heartbeat DDS evidence missing at declared10s')
        executor.spin_once(timeout_sec=0.05);adapter.observe()
    assert all(m['node_name']=='r7_strict_heartbeat' and m['role']=='r7-isolated' and m['status']==1 and m['frame_id']=='' and m['stamp_ns']>0 and m['detail'].startswith('alive; seq=') for m in messages)
    seq=[int(m['detail'].split('=')[-1]) for m in messages];assert seq==sorted(set(seq))
    adapter.request_stop();assert adapter.wait()==0
    report=adapter.close();assert report['accepted'] and report['cleanup_complete'] and report['state']=='CLOSED' and report['raw_wait_status']==0 and report['returncode']==0
    assert not report['outstanding_responsibilities'] and not report['single_slot_retained'] and report['owned']['journal']['closed_proven']
    assert report['borrowed_release_actions']==[] and report['borrowed']['parent_context']['object_id']==id(context) and not report['borrowed']['ros_domain_id']['released']
    strict=report['strict_report'];assert strict['accepted'] and strict['raw_wait_status']==0 and not strict['recovery'] and strict['references_closed']
    facts=strict['result']['facts'];assert facts['callbacks_entered']==facts['callbacks_finished']>=len(messages)
    assert all(facts['cleanup'].get(n) for n in ['executor','node','context_shutdown','context_destroy']) and all(v=='retired' for v in facts['native_handle_states'].values())
    pub=next(p for p in facts['publishers'] if p['topic']=='/system/heartbeat');assert (pub['depth'],pub['reliability'],pub['durability'])==(20,'1','2')
    assert facts['business_state']['frequency_hz']==5.0 and 200000000 in facts['timer_periods_ns']
    sent=[e for e in strict['signals'] if e['event']=='SIGNAL'];assert len(sent)==1 and sent[0]['number']==2
    assert report['child_identity']['birth']['ppid']==os.getpid() and report['child_identity']['release']==verified['manifest_sha256']
    after=parent_state();assert before==after
    with node.handle:pass
    (root/'parent-borrowed-state.json').write_text(json.dumps({'before':before,'after':after,'unchanged':True,'parent_context_cleanup_owner':'this external validation harness, never the MVP registry'},indent=2)+'\n')
    (root/'heartbeat-wire.json').write_text(json.dumps({'topic':'/system/heartbeat','messages':messages,'requested_qos':{'depth':20,'reliability':'RELIABLE','durability':'VOLATILE'},'publisher_observed_qos':pub},indent=2)+'\n')
    (root/'production-path.json').write_text(json.dumps({'actual_adapter_module':production.__file__,'actual_registry_module':registry_module.__file__,'loader':type(production.__loader__).__name__,'factory_is_real_unpatched_facade':registry_module.create_session is strict_entry.create_session,'release_manifest':verified['manifest_sha256'],'single_factory_registration':report['registration_count'],'generation':report['generation'],'raw_wait_status':report['raw_wait_status'],'child_identity':report['child_identity'],'no_test_extension':strict['launch']['profile']=='production','container_validation_parent_pid':os.getpid()},indent=2)+'\n')
except BaseException as error:
    primary=error
    if adapter is not None:
        try:adapter.close(primary_error=error)
        except BaseException as cleanup:
            if cleanup is not error:cleanup_errors.append(cleanup)
finally:
    if adapter is not None:
        try:(root/'cleanup-report.json').write_text(json.dumps(adapter.get_cleanup_report(),indent=2)+'\n')
        except BaseException as error:cleanup_errors.append(error)
    for function in ([executor.shutdown] if executor is not None else [])+([node.destroy_node] if node is not None else [])+([context.try_shutdown,context.destroy] if context is not None else []):
        try:function()
        except BaseException as error:cleanup_errors.append(error)
error=BaseExceptionGroup('native production trial and owned fixture cleanup failed',([primary] if primary is not None else [])+cleanup_errors) if cleanup_errors else primary
row={'id':'R9-NATIVE-production-heartbeat','status':'PASS' if error is None else 'FAIL','seconds':time.monotonic()-started,'scope':'actual unpatched M6 production adapter/registry/facade and real on-wire heartbeat','release_manifest':verified['manifest_sha256'],'real_ros':True,'wire_messages':len(messages),'test_extension':False}
if error is not None:row.update(exception=repr(error),traceback=''.join(traceback.format_exception(error)))
(root/'results.json').write_text(json.dumps([row],indent=2)+'\n');(root/'summary.json').write_text(json.dumps({'pass':error is None,'actual':1,'passed':int(error is None),'failed':int(error is not None),'production_path':True},indent=2)+'\n');print(row['id'],row['status']);print('ARTIFACTS',root);raise SystemExit(0 if error is None else 1)
