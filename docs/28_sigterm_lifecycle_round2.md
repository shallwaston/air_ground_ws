# 第二轮：H1 协作式停止与生命周期验证

## 范围与实现

本轮以 `0143ffbcf5a78e55cde9d963fcf244084e7cb555` 为代码基线，继续使用
`optimize/jazzy-runtime-safety`，处理审查报告 H1 及构造失败所需的资源清理路径。
不处理 M2–M8，不改变 Topic、`.msg`、Frame、Launch 参数或默认 QoS。
原始独立审查证据先保存为提交 `cb5f328`，随后仅追加处理状态。

### 实际研究的 Jazzy 版本

在当前容器内读取了以下已安装实现，而不是引用其他 ROS 发行版的实现：

- `ros-jazzy-rclpy 7.1.12-1noble.20260912.162354`，Ubuntu 24.04 / Python 3.12.3。
- `rclpy.init` 接受 `context=` 和 `signal_handler_options=`；默认 Context 默认
  安装 SIGINT/SIGTERM 原生处理器。显式传入 `SignalHandlerOptions.NO` 可禁止该层关闭。
- `Context.shutdown/try_shutdown` 关闭 Context、调用 Python shutdown callbacks 并结束
  logging，不会替调用方销毁 Node 或全部实体。
- `SingleThreadedExecutor.spin_once` 在调用线程执行同步回调；返回后没有另一个执行器
  线程继续执行这些回调。本轮在其返回之后才调用 `Executor.shutdown`。
- `Node.destroy_node` 释放各实体，但假设基础构造已完成；基础构造中途失败需要按实际
  已分配实体清理。`Executor.__del__` 也会访问构造期字段，需要避免部分构造遗留。
- 当前原生信号关闭 C++ Context 不会自动调用 Python `Context.on_shutdown` 列表；
  处理器恢复测试检查真实 Context 状态，不以 Python 回调通知代替。

### 关闭顺序

```text
SIGINT / SIGTERM
  -> Python handler 仅设置 stop_requested
  -> 初始化/同步回调返回（Context 始终有效）
  -> 主循环不再调度下一轮 spin_once
  -> Executor.shutdown，释放其 guard conditions
  -> 销毁 Node / Publisher / Subscription / Timer / Service 等实体
  -> Context.try_shutdown
  -> 恢复调用方 Python 处理器、原生 rclpy 处理器选项与信号 mask
```

`node_runner.py` 显式持有独立 Context 和 SingleThreadedExecutor，不创建全局默认
executor，也不关闭调用方默认 Context。信号安装/恢复窗口用 POSIX signal mask
保护。处理器不调用 ROS、日志、锁、shutdown 或 raise；重复信号仅重复记录同一请求。
等待阶段使用 `spin_once(timeout_sec=0.1)` 观察停止请求，不是增加测试 sleep。

21 个 Node 构造器只增加可选 `context=`，无参构造仍可用于原有直接实例化代码。
内部 `run_node` 接受 Node 类；先保留分配出的对象，再执行 `__init__`，因此基础构造
或子类构造抛错时仍有可清理的对象。少量部分构造清理使用了本次已核对的 Jazzy 字段，
包括 `_Node__node`、`_type_description_service`、`_guard` 和 `_sigint_gc`。
升级 ROS/rclpy 时必须重新核对这些分支并运行矩阵。

不再用 RCLError 文本或 traceback 函数名判断正常停止，也没有忽略 RCLError。
真实初始化/业务异常继续传播；若清理本身也失败，会继续尝试释放其余资源，并用
ExceptionGroup 保留业务错误和清理错误。已销毁句柄的 InvalidHandle 仅在幂等清理
分支识别。Python 包装对象仍可等待 GC，但被测 ROS 实体的句柄必须已经失效。

TF one-shot 改为对 runner 请求停止，不在其活动回调中关闭 Context。
直接实例化、未使用 runner 的旧调用方式保留原行为，默认 Context 仍通过
`rclpy.try_shutdown()` 重置以支持同进程再次初始化（新增兼容回归用例）；one-shot 缺 TF 时返回成功的
M5 语义没有在本轮修改。

## 确定性测试矩阵

`shutdown_probe.py` 只用于测试子进程。每个受控阶段通过 stdout/pipe 发出阶段事件，
父进程发送真实 OS 信号后才释放屏障；子进程断言 stop_requested 已设置而 Context
仍有效，然后继续真实 ROS 操作。没有用固定 sleep 延长窗口。

| 阶段 | 覆盖 |
| --- | --- |
| Context 初始化前、初始化后 | SIGINT / SIGTERM；每种三轮 |
| Executor guard 创建期间 | SIGINT / SIGTERM；每种三轮 |
| Node 基础初始化前、完成后 | SIGINT / SIGTERM；每种三轮 |
| 原生 WaitSet.wait 入口/有界等待 | SIGINT / SIGTERM；每种三轮；避开 add_node 的首次 guard 通知，不用 pipe 阻塞替代原生等待 |
| 普通 Timer 回调 | 信号到达后实际发布 String，Context 有效 |
| UAV MapTile 计算函数期间 | 信号到达后继续原始计算和实际 MapTile 发布 |
| StaticTfLoader 加载/构造期间 | 信号到达后继续 YAML 加载和实际 `/tf_static` 发布 |
| Node 清理前、Context 最后关闭前 | SIGINT / SIGTERM；每种三轮 |
| 连续与混合信号 | 六个受控阶段，五次同类或混合信号；每次独立 ACK 后再发送下一次 |
| 全部 21 个已安装入口 | 执行安装后的 console script，分别检查 SIGINT / SIGTERM |

每个正常信号用例检查：退出码 0；无 Context invalid、guard condition 创建错误、
Traceback 或部分执行器析构错误；executor 已停止后才清理 Node；Context 最后关闭；
所有保留的 Node/实体/guard 句柄失效；节点实体列表为空；原 Python 处理器和 mask 恢复。
探针刻意保留对象及句柄的强引用，避免 GC 恰好回收资源造成假通过。

负向用例覆盖：Context 初始化前/后失败、Executor 部分构造失败、Node 基础构造失败、
实体分配后子类构造失败、普通业务异常、真实 RCLError、手动关闭 Context 后的真实
RCLError，以及清理前/后抛错。此类子进程必须非零退出、保留指定真实错误，且释放资源。
另有独立测试验证调用方其他 Context、Publisher、Python 处理器和原生信号处理层仍可用。

## 回归结果与日志

当前结果以 `validation/round2/` 中的最终日志和资源清理摘要为准。

- 完整 pytest：**194 passed**，domain 72。
- colcon build：**7 packages finished**，domain 73。
- colcon test / test-result：**194 tests, 0 errors, 0 failures, 0 skipped**，domain 73。
- 完整 Mock Launch：五类关键消息、地图载荷、三条 TF 链验证通过；**16 个节点正常
  退出，Launch 退出码 0**，domain 74。
- 额外调用方 Executor 检查：domain 76，NO/ALL 两种原生处理器选项均可继续发布、
  spin 和正常 shutdown，见 `foreign-executor.log`；不计入 pytest 数量。
- 十轮加强测试：**238 passed, 57 deselected**，domain 75。57 项是此次未重复的入口和
  异常用例，已在完整 pytest/colcon 中执行，不是跳过 SIGTERM。
- 完整 pytest 和独立压力测试共保留 **374 份**清理记录摘要：**364 个正常信号子进程
  均退出 0**，10 个真实故障子进程按预期非零退出；所有记录的剩余实体句柄数为 **0**，
  Context 已关闭，原 Python 处理器已恢复。colcon 的同类检查不重复计入此汇总。

`validation/round2/lifecycle-summary.json` 包含逐入口 SIGINT/SIGTERM 结果、各阶段重复
次数、真实故障清理结果、24 个修改代码文件的 SHA-256 和原始日志 SHA-256。
这些摘要由实际逐进程 JSON 记录生成并验证，不是仅从退出码推断资源状态。

本轮要求的执行顺序是 pytest -> build -> colcon test -> test-result -> Mock Launch，
随后对 Timer/MapTile/StaticTfLoader 等阶段做十轮加强检查。后者使用独立 domain 75，
通过环境变量只增加重复次数，不能将默认重复次数降到三轮以下。

```bash
python3 -m pytest -q -p no:cacheprovider src/ag_system_tests/test
./scripts/build_ws.sh --parallel-workers 2
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
ros2 launch ag_bringup single_machine_mock.launch.py
AG_SHUTDOWN_STRESS_REPEATS=10 python3 -m pytest -vv -p no:cacheprovider \
  src/ag_system_tests/test/test_node_shutdown.py \
  -k 'signal_timing_matrix or repeated_signals'
```

云端通过 `/workspace/.air-ground-env/ros env ROS_DOMAIN_ID=<独立域> ...` 执行。
常规故障回归中的子进程非零退出是测试断言的期望结果，不是被跳过或标为 xfail。

## 修改文件

- `ag_network_tools/node_runner.py`：停止请求、独立 Context/Executor、部分构造和异常清理。
- `ag_mock_nodes` 的 12 个、`ag_monitor` 的 5 个、`ag_tf_tools` 的 4 个节点模块：仅注入
  可选 Context；`tf_healthcheck.py` 另外将 one-shot 关闭改为协作请求。
- `ag_system_tests/test/test_node_shutdown.py` 和新增 `shutdown_probe.py`：生命周期矩阵、
  实际安装入口、真实故障、资源句柄与调用方状态恢复检查。
- `docs/27_independent_premerge_audit.md`：保留原始审查并追加 H1/M1 处理状态。
- 本报告以及 `docs/validation/round2/`：单独保存本轮原始日志和汇总。

未修改 QoS 实现、Launch 环境作用域、rosbag、动态 TF 参数、消息定义和默认 QoS。

## 适用边界与复审

本实现针对当前 21 个同步控制台入口。绕过 `run_node` 直接使用 `rclpy.spin` 的代码
仍服从调用方/发行版的信号协议，不属于此次接管路径。本实现不强制中断永不返回的构造/回调、阻塞 I/O 或
业务自行创建的发布线程；它们需要自己的可取消协议。未来引入 async 回调或其他
执行器时必须扩展生命周期设计与测试，不能直接外推当前结果。SIGKILL 不提供清理机会。

本轮没有双机、真实硬件、其他 ROS 发行版或其他 RMW 验证。M2–M8 等后续问题未修复。
本轮最终验证已完成，可以重新进入独立合并审查；这不是合并批准，也不会自动合并 PR。
