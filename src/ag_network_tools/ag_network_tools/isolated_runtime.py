"""Private Jazzy resource core for a single pre-owned exec address space.

This module imports ROS only inside run_ros, after the bootstrap owns signals.
There is no signal installation, uninstallation, previous-handler write, or
forced exit here. Legacy runner and console source files are unchanged.
"""
import sys
import time
import json


def run_ros(reporter,config,verifier,native_maps,tasks,serialize):
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions,get_current_signal_handlers_options
    from rclpy.exceptions import InvalidHandle
    from ag_network_tools.isolated_resources import _RunContext,_destroy_node,request_stop as strict_request_stop
    from ag_network_tools.isolated_entries import ENTRIES
    import ctypes,importlib,types,importlib.machinery
    reporter.check_actions('ros-import')
    loaded_native=[]
    if config['entry'] in ENTRIES and ENTRIES[config['entry']]['needs_interfaces']:
        if not config.get('native_assets'):raise RuntimeError('verified native interface capsule required')
        for asset in config['native_assets']:
            if asset['kind']=='preload':
                loaded_native.append(ctypes.CDLL('/proc/self/fd/'+str(asset['fd']),mode=ctypes.RTLD_GLOBAL))
        reporter.check_actions('native-capsule-loaded')
        reporter.checkpoint('native-capsule-loaded',manifest=config.get('deployment_manifest_sha256'),libraries=[a['file'] for a in config['native_assets']])
    if get_current_signal_handlers_options()!=SignalHandlerOptions.NO:
        raise RuntimeError('unexpected native handler options after controlled import')
    reporter.checkpoint('ros-imported',origins=dict(verifier.origins),native_maps=native_maps(config),tasks=tasks(),native_options=str(get_current_signal_handlers_options()))
    context=None;executor=None;node=None;executor_ready=False;primary=None;cleanup_errors=[];handles={}
    facts={'callbacks_entered':0,'callbacks_finished':0,'callback_active':False,'cleanup':{},'restore_attempted':False,'api_actions':[]}
    def phase(name,**values):
        current=reporter.check_actions(name)
        facts['api_actions'].append({'phase':name,'actions':current,'tasks':tasks()})
        reporter.checkpoint(name,**values)
    def callback_body():
        facts['callbacks_entered']+=1;facts['callback_active']=True
        callback_error=None
        try:
            reporter.checkpoint('callback-enter',context_ok=context.ok(),active=True)
        except BaseException as error:callback_error=error
        finally:
            facts['callbacks_finished']+=1;facts['callback_active']=False
            try:reporter.checkpoint('callback-return',context_ok=context.ok(),active=False)
            except BaseException as observation_error:
                if callback_error is not None:raise BaseExceptionGroup('callback and observation failed',[callback_error,observation_error])
                raise
        if callback_error is not None:raise callback_error.with_traceback(callback_error.__traceback__)
    class MinimalNode(Node):
        def __init__(self,*,context):
            super().__init__('r6_isolated_minimal',context=context)
            self.create_timer(0.02,callback_body)
    def cleanup_checkpoint(name):
        try:reporter.checkpoint(name)
        except OSError as error:cleanup_errors.append(error)  # retain telemetry failure, still clean owned resources
    def run_resources(node_type,args):
        nonlocal context,executor,node,executor_ready,primary
        try:
            context=_RunContext();reporter.context=context
            context.stop_requested=reporter.stop
            phase('context-init-before')
            if reporter.stop:
                facts['cancelled_before_init']=True;return
            rclpy.init(args=args,context=context,signal_handler_options=SignalHandlerOptions.NO)
            if context.handle is not None:handles['context']=context.handle
            phase('context-initialized',context_id=id(context),context_ok=context.ok(),native_options=str(get_current_signal_handlers_options()))
            if reporter.stop:return
            executor=SingleThreadedExecutor.__new__(SingleThreadedExecutor);executor._guard=None;executor._sigint_gc=None
            phase('executor-init-before')
            SingleThreadedExecutor.__init__(executor,context=context);executor_ready=True
            for name in ('_guard','_sigint_gc'):
                guard=getattr(executor,name,None)
                if guard is not None:handles['executor'+name]=guard.handle
            phase('executor-created',executor_id=id(executor),context_id=id(executor.context))
            node=node_type.__new__(node_type);node._Node__executor_weakref=None
            phase('node-init-before')
            node_type.__init__(node,context=context)
            handles['node']=node.handle
            if node.context is not context or executor.context is not context:raise RuntimeError('resource context identity mismatch')
            facts['subscriptions']=[{'topic':s.topic_name,'depth':s.qos_profile.depth,'reliability':str(s.qos_profile.reliability),'durability':str(s.qos_profile.durability)} for s in node.subscriptions]
            facts['publishers']=[{'topic':p.topic_name,'depth':p.qos_profile.depth,'reliability':str(p.qos_profile.reliability),'durability':str(p.qos_profile.durability)} for p in node.publishers]
            facts['timer_periods_ns']=[t.timer_period_ns for t in node.timers]
            phase('node-created',node_id=id(node),context_id=id(node.context),node_class=node_type.__module__+'.'+node_type.__name__)
            executor.add_node(node);phase('node-added')
            if reporter.stop or context.stop_requested:
                facts['cancelled_before_ready']=True;return
            phase('ros-ready-verified',origins=dict(verifier.origins),native_maps=native_maps(config),tasks=tasks())
            reporter.ready(ros=True,private_context=True,node_owned=True,executor_owned=True,context_ok=context.ok(),callbacks_entered=facts['callbacks_entered'],tasks=tasks())
            while not reporter.stop and not context.stop_requested and context.ok():
                reporter.poll_commands();reporter.check_actions('spin-before')
                executor.spin_once(timeout_sec=0.05)
                reporter.check_actions('spin-after')
        except BaseException as error:
            primary=error
        finally:
            if node is not None:
                provisional=getattr(node,'_Node__node',None)
                if provisional is not None:handles.setdefault('node',provisional)
            if executor is not None:
                for name in ('_guard','_sigint_gc'):
                    guard=getattr(executor,name,None)
                    if guard is not None:handles.setdefault('executor'+name,guard.handle)
            if node is not None:
                fields={'heartbeat_pub':['sequence','frequency_hz','reported_node_name','role','status','detail'],'ugv_map_tile_sub':['message_count','last_seq','last_receive_ns','log_every_n'],'tf_healthcheck':['one_shot']}.get(config['entry'],[])
                facts['business_state']={name:getattr(node,name) for name in fields if hasattr(node,name)}
            if facts['callback_active']:
                # Synchronous callback return is required before this point.
                cleanup_errors.append(RuntimeError('callback still active: destructive cleanup forbidden'))
            else:
                if executor is not None:
                    try:
                        cleanup_checkpoint('executor-shutdown-before')
                        if executor_ready:
                            if not executor.shutdown():raise RuntimeError('executor shutdown not complete')
                        else:
                            partial=[]
                            for name in ('_guard','_sigint_gc'):
                                guard=getattr(executor,name,None)
                                if guard is not None:
                                    try:guard.destroy();setattr(executor,name,None)
                                    except BaseException as error:partial.append(error)
                            if partial:raise BaseExceptionGroup('partial executor cleanup failed',partial)
                        facts['cleanup']['executor']=True
                        reporter.checkpoint('executor-shutdown-after')
                    except BaseException as error:cleanup_errors.append(error)
                if node is not None:
                    try:
                        cleanup_checkpoint('node-destroy-before')
                        _destroy_node(node);facts['cleanup']['node']=True
                        reporter.checkpoint('node-destroy-after')
                    except BaseException as error:cleanup_errors.append(error)
                if context is not None:
                    try:
                        cleanup_checkpoint('context-shutdown-before')
                        context.try_shutdown();facts['cleanup']['context_shutdown']=not context.ok()
                        reporter.checkpoint('context-shutdown-after')
                    except BaseException as error:cleanup_errors.append(error)
                    try:
                        if not context.ok():
                            context.destroy();facts['cleanup']['context_destroy']=True
                    except BaseException as error:cleanup_errors.append(error)
            # Read observations only. A foreign action is recorded, never repaired.
            current=reporter.reader.actions();facts['native_actions_final']=current
            if current!=reporter.managed_actions:
                conflict=RuntimeError('native owner conflict remains; no handler restoration attempted')
                cleanup_errors.append(conflict)
            handle_states={}
            for label,handle in handles.items():
                try:
                    with handle:handle_states[label]='still-valid'
                except InvalidHandle:handle_states[label]='retired'
                except BaseException as error:handle_states[label]=type(error).__name__
            facts['native_handle_states']=handle_states
            facts['context_ok_final']=context.ok() if context is not None and not facts['cleanup'].get('context_destroy') else False
            facts['tasks_final']=tasks();facts['resource_ids']={'context':id(context) if context else None,'executor':id(executor) if executor else None,'node':id(node) if node else None}
    try:
        if config['entry']=='minimal':run_resources(MinimalNode,config['ros_args'])
        elif config['entry'] in ENTRIES:
            spec=ENTRIES[config['entry']];calls=[];approved_class=None
            # The original business main imports this explicit strict bridge.
            # The legacy file is absent from the sealed child bundle and its
            # signal manager must never be imported/executed in this process.
            def strict_driver(node_type,args=None):
                if node_type is not approved_class:raise RuntimeError('unapproved strict Node class')
                calls.append(node_type.__name__)
                if len(calls)!=1:raise RuntimeError('strict entry reentry refused')
                target=getattr(approved_class,spec['callback']).__code__
                def profile(frame,event,arg):
                    if frame.f_code is target:
                        if event=='call':
                            facts['callbacks_entered']+=1;facts['callback_active']=True
                            try:
                                if config['entry']=='ugv_map_tile_sub':
                                    message=frame.f_locals['msg']
                                    facts['last_callback_input']={'seq':int(message.seq),'width':int(message.width),'height':int(message.height),'elevation_length':len(message.elevation),'traversability_length':len(message.traversability),'elevation_sample':list(message.elevation[:16]),'traversability_sample':list(message.traversability[:16]),'frame_id':message.header.frame_id[:64]}
                                reporter.checkpoint('callback-enter',context_ok=context.ok(),active=True)
                            except BaseException:
                                facts['callbacks_finished']+=1;facts['callback_active']=False
                                raise
                        if event=='return':
                            facts['callbacks_finished']+=1;facts['callback_active']=False
                            reporter.checkpoint('callback-return',context_ok=context.ok(),active=False)
                sys.setprofile(profile)
                try:return run_resources(node_type,args)
                finally:sys.setprofile(None)
            bridge=types.ModuleType('ag_network_tools.node_runner')
            bridge.__spec__=importlib.machinery.ModuleSpec(bridge.__name__,loader=None,origin='strict-approved-entry-bridge')
            bridge.run_node=strict_driver;bridge.request_stop=strict_request_stop
            def forbidden(name):
                if name.startswith('__'):raise AttributeError(name)
                raise RuntimeError('legacy signal API is unavailable in strict mode: '+name)
            bridge.__getattr__=forbidden
            if bridge.__name__ in sys.modules:raise RuntimeError('legacy runner was loaded before strict bridge')
            sys.modules[bridge.__name__]=bridge
            entry=importlib.import_module(spec['module']);approved_class=getattr(entry,spec['class'])
            if entry.run_node is not strict_driver:raise RuntimeError('entry did not use the strict-only bridge')
            if hasattr(entry,'request_stop') and entry.request_stop is not strict_request_stop:raise RuntimeError('entry uses foreign stop authority')
            entry.main(config['ros_args'])
            if calls!=[spec['class']]:raise RuntimeError('actual main did not call the approved factory exactly once')
            facts['actual_console_main']=spec['module']+':main'
            facts['strict_bridge_only']=True
        else:raise RuntimeError('unapproved ROS entry')
    except BaseException as error:
        if primary is None:primary=error
        else:cleanup_errors.append(error)
    errors=([primary] if primary is not None else [])+cleanup_errors
    error=BaseExceptionGroup('isolated ROS lifecycle failed',errors) if cleanup_errors else primary
    facts['primary_id']=id(primary) if primary else None;facts['cleanup_error_ids']=[id(e) for e in cleanup_errors]
    facts['exception']=serialize(error) if error else None
    facts['source_origins']=dict(verifier.origins)
    try:
        reporter.send('RESULT',ok=not errors,facts=facts,signals=reporter.signal_count,restore_attempted=False)
        reporter.result_sent=True
    except BaseException as delivery_error:
        error=BaseExceptionGroup('lifecycle and result delivery failed',[error,delivery_error]) if error is not None else delivery_error
        sys.stderr.write('R6_UNDELIVERED_RESULT '+json.dumps({'facts':facts,'exception':serialize(error)})+'\n')
    if error is not None:raise error.with_traceback(error.__traceback__)
    return 0
