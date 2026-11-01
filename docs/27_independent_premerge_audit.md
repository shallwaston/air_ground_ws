# 第一轮运行时优化：只读合并前审查

## 结论与审查边界

**当前不建议合并 PR #2。应先修复 HIGH H1 的 SIGTERM 退出竞态，并补充相关时序测试。**

未发现 CRITICAL；发现 1 项 HIGH、8 项 MEDIUM、4 项 LOW。MEDIUM/LOW 不全部构成本轮合并阻断，具体安排见末节。未发现不等于证明不存在；本报告不能保证没有其他未知高风险问题。

- 实际比较：`e129564eb5de9125209600f63e4112a85338c02f`（master）到 `0143ffbcf5a78e55cde9d963fcf244084e7cb555`（优化分支）。通过 `git ls-remote` 只读确认远程 master、优化分支及 `refs/pull/2/head` 与这些提交一致。
- 依据：上述提交的实际 diff、当前源文件、安装版 Jazzy/rclpy/Launch 实现，以及本轮独立运行的反例。上一轮报告中的“98 passed”和性能数据视为历史记录，不直接作为本轮通过依据。
- 环境：Ubuntu 24.04 / ROS 2 Jazzy / Fast DDS 容器。复现使用独立子进程和 ROS domain；故障注入仅在子进程内包装函数，没有修改项目代码。
- 仓库内仅新增本报告；没有修改源文件、测试、配置、历史或分支，没有格式化、提交、推送、合并或变更 PR #2。

## 本轮实际执行结果

| 检查 | 本轮结果 | 解释 |
| --- | --- | --- |
| 原样运行现有 pytest，domain 64，禁用 pytest 缓存 | **97 passed, 1 failed，退出码 1，47.14 秒** | SIGTERM 用例 `ag_mock_nodes.uav_mock_odom_tf_pub` 自然触发 H1；没有修改测试来制造此失败 |
| 清除旧 overlay 影响，在仓库外全新构建 | **7 packages finished，退出码 0** | 新 build/install/log 均在 `/workspace/.air-ground-audit/fresh/`；没有复用原工作空间构建输出 |
| 新安装的 ament 注册与 `ros2 interface show ag_interfaces/msg/MapTile` | **通过** | 包前缀为新的 `/workspace/.air-ground-audit/fresh/install/ag_interfaces`，不是旧 overlay |
| 地图独立逐元素比较 | **100 组通过** | 固定随机种子；不同矩形尺寸及正负大相位；高程和通行性与原始标量表达式完全相等 |
| 四元数范数检查 | **100 组通过** | 有限欧拉角输入，范数误差小于 `1e-12`；同时核对提取前后的公式一致 |
| 里程计独立有限差分 | **9 个速度分量通过** | 非默认半径 3、速度 5、垂直振幅 0.4，三个采样时刻；按实际消息时间戳差分，误差小于 `1e-7` |
| SIGTERM 确定性时序注入 | **复现两个退出码 1 的反例** | 地图正常回调和静态 TF 构造阶段均出现 context-invalid 发布异常 |
| 部分构造失败的资源检查 | **发现延迟释放** | context 已关闭，但节点仍存活、C++ handle 可进入、`destroy_node` 调用次数为 0；显式 GC 后才消失 |
| QoS 输入/缓存边界 | **复现问题** | 同 mtime/size 替换文件仍读旧值；拼错字段被接受；字符串深度不再兼容 |
| 验收入口负向探针 | **复现假阳性** | heartbeat smoke 的进程换成 `/bin/false` 仍通过；无 TF 的 one-shot 命令返回 0 |

本轮未重新执行 `colcon test`、性能基准或完整 rosbag 录制回放。回放问题的证据是实际旧时间戳输入、QoS 兼容性 API 和 Launch 静态路径；没有将这些检查表述成已重跑 rosbag 集成测试。未执行双机、硬件、弱网、时钟同步或其他 RMW 测试。

主要命令（先加载 Jazzy 和当前 overlay；云端可使用现有容器包装器）：

```bash
/workspace/.air-ground-env/ros env ROS_DOMAIN_ID=64 \
  python3 -m pytest -q -p no:cacheprovider src/ag_system_tests/test
```

全新构建先在子 shell 清除旧 `AMENT_PREFIX_PATH`、`COLCON_PREFIX_PATH`、`CMAKE_PREFIX_PATH`、`PYTHONPATH`、`LD_LIBRARY_PATH`、`ROS_PACKAGE_PATH`、`PKG_CONFIG_PATH`，再 source `/opt/ros/jazzy/setup.bash`，执行：

```bash
colcon --log-base /workspace/.air-ground-audit/fresh/log build \
  --base-paths /workspace/air_ground_ws/src \
  --build-base /workspace/.air-ground-audit/fresh/build \
  --install-base /workspace/.air-ground-audit/fresh/install \
  --symlink-install --parallel-workers 2
```

本轮日志保留于当前机器的 `/workspace/.air-ground-audit/` 和 `/workspace/.air-ground-audit-fresh.log`，不属于已提交仓库内容。

## CRITICAL

本轮未确认此级别问题。未执行的双机/硬件场景不能据此认定安全。

## HIGH

### H1：SIGTERM 关闭上下文后，执行器创建和活动回调仍可能操作该上下文

- **位置**：`src/ag_network_tools/ag_network_tools/node_runner.py` 第 19、22、23、26、32、39 行；`src/ag_mock_nodes/ag_mock_nodes/uav_mock_map_tile_pub.py` 第 69、85 行；`src/ag_tf_tools/ag_tf_tools/static_tf_loader.py` 第 35、38 行。所有 21 个 main 均委托该入口。
- **性质**：核心退出缺陷没有完整修复；新增的异常过滤只覆盖一个窗口，不是 21 个节点已实现无竞态退出的证明。
- **原因**：Jazzy 的原生信号处理可异步关闭 context。过滤仅接受最末 traceback 函数名为 `_wait_for_ready_callbacks` 的 RCLError。创建全局执行器的 guard condition、发布地图或发送静态 TF 时发生的相同关闭竞争会被重新抛出。`try_shutdown()` 只解决重复关闭，不能解决继续使用已关闭上下文。
- **实际证据**：原样 pytest 的 SIGTERM/odom 用例失败。栈为 `rclpy.spin -> get_global_executor -> SingleThreadedExecutor -> GuardCondition`，错误为 `failed to create guard_condition: ... context is not valid`，进程退出 1；随后还出现部分构造执行器析构的 `_sigint_gc` AttributeError。
- **确定性复现条件**：在子进程中，临时包装地图模块的 `build_mock_tile_layers`：进入正常 timer 回调后向本进程发送 SIGTERM，等待 `rclpy.ok()` 为 false，再继续原计算。随后第 85 行报 `Failed to publish: publisher's context is invalid`，退出 1。对 `StaticTfLoader.load_transforms` 在构造阶段做相同包装，第 38 行同样失败。包装不修改仓库文件，模拟实际计算或配置 I/O 期间收到停止信号。
- **建议**：明确管理 context、executor 和停止请求的顺序，避免 context 先关闭、回调仍发布；覆盖初始化、构造、回调和等待阶段的取消路径。不要简单吞掉所有 context 已关闭时的 RCLError，否则会隐藏真实回调缺陷。保留已有真实异常传播测试，新增各阶段 SIGINT/SIGTERM 注入、真实发布及析构清理测试，并在负载下重复验证。
- **合并要求**：修复并验证后再重新审查；不能通过延长测试 sleep、跳过 SIGTERM 或只重跑到绿色来解除阻断。

## MEDIUM

### M1：factory 部分构造失败后，节点没有被入口显式销毁

- **位置**：`node_runner.py` 第 20、22、36 行；`src/ag_system_tests/test/test_node_shutdown.py` 第 61–67 行；`static_tf_loader.py` 第 29–35 行。
- **原因/性质**：`node = factory()` 只有返回后才赋值。子类在 `super().__init__()`、创建实体之后抛错时，入口看到的 node 仍是 None。当前安装版 `Context.try_shutdown()` 不会遍历并销毁这些节点。现有构造失败测试在创建 Node 前就抛错，只证明 context 被关闭。
- **复现**：构造器创建 Node 和绑定实例方法的 timer，再抛 ValueError；仅保留 weakref 并临时关闭自动 GC。本轮得到 `partial_node_alive=true, node_handle_open=true, destroy_calls=0, context_ok=false`；显式 GC 后节点消失。
- **影响边界**：这是依赖 GC 的延迟资源释放，不是已证明的永久泄漏。独立 CLI 退出时 OS 会回收；同进程重试、测试或未来复杂适配器更容易受影响。文档声称启动失败时也会销毁节点，范围过宽。
- **建议**：在可能失败的子类初始化路径提供异常清理，或采用可显式持有已分配节点的构建/资源管理设计。测试应覆盖“创建实体之后失败”，同时检查实体销毁，而不是只检查 `rclpy.ok()`。

### M2：Launch 的 QoS 环境设置没有限制在本 Launch 的节点范围内

- **位置**：`src/ag_bringup/launch/single_machine_mock.launch.py` 第 32 行；同类设置位于 `dual_machine_client.launch.py:26`、`dual_machine_server.launch.py:33`、`qos_stress_test.launch.py:32`、`rosbag_replay_test.launch.py:47`。
- **原因/性质**：本轮新增的 `SetEnvironmentVariable` 修改共享 LaunchContext，没有本地环境作用域或恢复动作。独立启动这些文件时传播有效；组合到上层 Launch 时会影响随后启动的其他消费者。
- **复现条件**：上层先 include 此 Launch，之后在同一个未隔离 context 启动读取 `AG_QOS_CONFIG_PATH` 的节点；后者继承前一 Launch 的配置。本轮直接检查 action 执行前后，context 中值由未设置变成子 Launch 的路径且保留。安装版 `Executable.prepare()` 在执行动作时复制环境，所以不是“所有先启动节点都会被后来配置追溯改变”。
- **建议**：给目标 Node 使用明确的 `additional_env`，或对动作使用合适的环境作用域并恢复父环境。增加父子 Launch 使用不同 QoS 文件的组合测试；同时说明 Launch 参数与进程环境的优先级。

### M3：回放播放器没有进入 `qos_config` 的配置闭环

- **位置**：`src/ag_bringup/launch/rosbag_replay_test.launch.py` 第 42–49 行。
- **原因/性质**：已有回放缺口仍存在。播放器先于环境 action 启动，而且 rosbag 播放器本身不读取项目的 `AG_QOS_CONFIG_PATH` 格式。实际 sinks 使用 helper 配置，播放器采用 bag 的记录 QoS/自身设置；没有传入播放器 QoS override 文件。
- **复现条件**：使用记录为 BEST_EFFORT 的地图 bag，以默认 RELIABLE 地图订阅策略运行 replay launch。播放器可能正常播放，但 sink 没有数据。本轮 `qos_check_compatible` 对这组策略实际返回 `QoSCompatibility.ERROR: Best effort publisher and reliable subscription`。没有在本轮额外录制这种特殊 bag，播放器与 sink 的完整反例仍需集成验证。
- **建议**：明确两种配置的边界；提供格式适配后的 `--qos-profile-overrides-path`，或依据记录 QoS 配置 sinks，并检测不兼容。测试至少覆盖不同 reliability/durability 的录制与回放。不能将环境传播测试解读为已覆盖播放器。

### M4：回放时间戳不能解释为实时网络延迟，`--clock` 也没有配置接收节点的时钟

- **位置**：`rosbag_replay_test.launch.py` 第 44、49、56 行；`src/ag_mock_nodes/ag_mock_nodes/ugv_map_tile_sub.py` 第 51–56 行；`src/ag_monitor/ag_monitor/delay_probe_sub.py` 第 47–56 行。
- **原因/性质**：旧问题，上一轮文档已提示，但代码仍会输出貌似正常的 latency。`--clock` 发布回放时钟，接收/TF 节点却没有统一启用 `use_sim_time`。默认系统时钟减去原始 source_stamp，得到的是消息年龄；即使统一使用回放时钟，也不等于本次回放的传输延迟。ROS 时间跳变还会污染 `rx_hz`。
- **实际复现**：向真实 `UgvMapTileSub.on_tile` 传入一天前的合法 source_stamp，报告约 `86,400,070 ms` 的 latency，而不是本次传输耗时。此项没有被冒充为重新执行 rosbag 录回测试。
- **建议**：区分 live 延迟、记录时间与回放时间；回放模式明确标记/禁用网络延迟指标，统一需要仿真时间的节点，并使用单调到达时间计算接收频率。补充暂停、跳时、倒序和循环回放测试；不要直接改写记录消息来掩盖时间语义。

### M5：两个验收入口存在实际假阳性

- **位置**：`src/ag_system_tests/test/test_launch_smoke.py` 第 64–85 行；`src/ag_tf_tools/ag_tf_tools/tf_healthcheck.py` 第 50–65 行。
- **原因/性质**：两处弱点均由旧实现继承。`LaunchService.run()==0` 不代表子进程成功；one-shot TF 检查记录缺失却仍正常关闭，不向调用方传递失败状态。
- **实际复现**：仅在测试进程内将 heartbeat 测试的 Node 替换为 `/bin/false`，日志显示进程退出 1，但原测试函数正常返回。另在没有任何 TF 的隔离 domain 执行 `ros2 run ag_tf_tools tf_healthcheck --ros-args -p one_shot:=true -p check_period_sec:=0.5`，三条 TF 都报告缺失，命令仍退出 0。
- **建议**：Launch 测试同时断言进程退出状态和实际消息行为；TF one-shot 将检查结果明确传递到命令退出状态。新增“节点启动即失败”和“TF 缺失”的负向用例。当前完整图集成测试直接查询 TF，不能因此否认上述两个入口的缺口。

### M6：新增测试尚不具备可靠的并发和失败后状态隔离

- **位置**：`test_single_machine_integration.py` 第 24–42、89–101 行；`test_node_shutdown.py` 第 30–38 行；`test_runtime_regressions.py` 第 41、69–70 行；`test_launch_smoke.py` 第 22–28 行。
- **原因**：测试共用继承的 ROS domain 和固定业务 Topic；只有 shutdown 节点名做了 UUID 隔离。Launch 日志 helper 直接改全局 ROS_HOME/ROS_LOG_DIR 而不恢复。一些构造和资源分配在 try/finally 之前，setup 失败时清理不完整。
- **复现条件/证据等级**：静态确认这些共享状态和清理边界；开发 mock 与 pytest 共用 domain、两个测试 worker 共用业务 Topic，可能造成额外发布者导致假失败，或无来源校验的 late-joiner 消息导致假阳性。第 69 行列表中后面的构造失败，也会跳过已创建节点的显式清理。本轮未运行 xdist，因此不声称已实际重现并发故障。
- **建议**：为测试图隔离 domain 或 namespace/Topic，恢复环境变量，把资源创建放入可靠的 context/ExitStack 清理范围；需要时断言消息来源。给 entrypoint 参数化补充非空/预期集合断言。不要依赖固定 `sleep(0.2)` 作为全部生命周期阶段的覆盖证明。

### M7：静态 TF 的有限值校验没有覆盖动态 TF 参数

- **位置**：`src/ag_tf_tools/ag_tf_tools/frame_alignment_stub.py` 第 31–44、58–62 行。
- **原因/性质**：旧输入边界问题；本轮只在静态 YAML 加入了有限值检查。动态节点将用户提供的平移直接写入 TF，NaN 角度也能生成 NaN 四元数。
- **实际复现**：以 `--ros-args -p x:=.nan` 构造真实节点，在进程内捕获 `sendTransform`，得到 `nan_dynamic_tf_accepted=True`。探针没有向 DDS 广播无效 TF；实际未拦截路径会将该消息传给广播器。
- **建议**：在启动时对动态平移、欧拉角和相关数值参数统一执行有限值检查，失败时给出参数名。增加 NaN、正负无穷等边界测试；不要将“静态 TF 已校验”推广为全部 TF 输入都已校验。

### M8：QoS 配置字段拼写错误仍会静默回退

- **位置**：`src/ag_network_tools/ag_network_tools/qos_profiles.py` 第 119–130、175–178 行。
- **原因/性质**：旧宽松解析的缺口未被本轮的严格枚举校验覆盖。未知字段被合并保存，但 `profile_from_dict` 只读取四个已知字段，不拒绝多余键。
- **实际复现**：加载 `topics: {"/uav/map/tile": {reliabilty: best_effort}}`，配置被接受，实际 reliability 仍为 RELIABLE。拼写错误没有得到警告。
- **建议**：明确允许的 schema，拒绝或警告未知字段，并在错误中给出 Topic/字段/文件位置。保留已有的部分默认值合并语义；为错字段名和错根键补充测试。

## LOW

### L1：QoS 缓存无法识别元数据相同的文件替换

- **位置**：`qos_profiles.py` 第 157–161、187–189 行。
- **原因**：cache key 仅为解析后路径、mtime_ns 和 size，不包含 inode、ctime 或内容版本。上一轮文档已经限定为这类缓存策略，因此不作为未披露的合并阻断。
- **实际复现**：先加载 depth 17，再用同长度 depth 18 的新文件原子替换，并保留 mtime；再次查询仍返回 17。
- **建议**：需要可靠的进程内重新加载时，加入适当的文件身份/版本或显式 cache reset；保留“已有端点需重启”的说明。不要把缓存失效等同于动态重建 DDS 端点。

### L2：深度参数存在额外的向后兼容变化

- **位置**：`qos_profiles.py` 第 121–123 行；与 master 中的 `int(data.get("depth", 10))` 对比。
- **原因**：以前接受的 `depth: "5"` 现在被拒绝。严格整数类型可以是合理选择，但这是配置输入兼容性变化，不是消息接口保持不变就能涵盖的事项。
- **实际复现**：`profile_from_dict({'depth': '5'})` 当前抛 ValueError；master 的转换可接受该值。
- **建议**：明确 schema/迁移说明，或兼容无歧义整数字符串。不要为追求兼容而继续接受会静默截断的非整数浮点值。

### L3：地图发布器有重复导入

- **位置**：`src/ag_mock_nodes/ag_mock_nodes/uav_mock_map_tile_pub.py` 第 5、6 行。
- **原因/复现条件**：同一 `run_node` 导入连续出现两次；直接读取文件即可确认。没有功能影响。
- **建议**：后续维护时移除重复项；本轮没有执行格式化或修改该文件。

### L4：单个 QoS 查询仍会复制整份配置

- **位置**：`qos_profiles.py` 第 189、194、202 行；`src/ag_monitor/ag_monitor/qos_inspector.py` 第 27–32 行。
- **原因/复现条件**：每次单 Topic 查询都对全部 Topic 做 deepcopy；inspector 先取得全部配置，再逐 Topic 调用 describe，又重复复制和 stat。N 个 Topic 的完整展示具有重复的 O(N²) 配置项复制成本。
- **影响边界**：通常发生在初始化或低频检查，不是每条地图消息的热路径；不能据此否定已有地图计算优化，也没有测得这是当前性能瓶颈。
- **建议**：保持公共 load 返回私有副本的安全性；内部单项查询只复制所需条目，inspector 复用一次配置快照。没有必要为此增加 NumPy 等依赖。

## 十项重点的综合判断

| 审查项 | 判断 |
| --- | --- |
| 21 个节点生命周期 | AST 确认 21 个 main 都委托 run_node；真实业务异常通常保留，但 H1 和 M1 使无竞态/完整清理承诺不能成立 |
| QoS 加载、缓存、合并和覆盖 | 正常字段和部分默认值合并正确；公共返回值 deepcopy 隔离成立；M8/L1/L2 是边界或兼容问题 |
| Launch QoS 端点 | 独立 Launch 下自定义应用端点和 TF 都调用 helper；安装版 Launch 在执行动作时复制环境。组合环境作用域和 rosbag 播放器有 M2/M3 缺口；不应要求项目 QoS 文件控制 `/rosout` 等 ROS 内部端点 |
| TF 四元数与静态校验 | 有限输入公式与旧实现一致；局部环检测逐次维持无环关系，未发现漏掉局部环或死循环；非有限静态值被拒绝。外部广播冲突无法靠单文件检查排除，动态输入见 M7 |
| 里程计 | yaw 为轨迹切向，机体系前向速度为 speed、侧向为 0；垂直导数为 `0.5 * omega * amplitude * cos(0.5*omega*t)`，角速度为 omega。有限差分验证通过 |
| 心跳 | 接收与汇总都用 monotonic_ns，steady timer 不随 `/clock` 暂停；默认单线程 executor/互斥回调下未发现字典读写竞争。没有预期节点注册表，失联节点只在删除当次告警，持续“角色缺失”状态应在第二阶段设计；不能把 Topic 仍活跃解释为所有预期节点健康 |
| 地图数学等价 | 先算行/列三角项没有改变每格乘法与加法顺序；默认有效整数尺寸、有限相位下逐元素等价。额外 O(width+height) 临时项换取减少 O(width*height) 次重复三角计算，合理且无新重型依赖 |
| ament 注册 | 显式 ament_cmake 声明正确；独立全新构建及 CLI 注册验证通过；已有修复后 overlay 的注册测试也通过。对旧 catkin 产物需按 docs/26 清理该包生成目录，本轮没有删除或独立重演当前工作空间的旧产物迁移，不能声称无缝增量兼容 |
| rosbag | 注册修复支持类型发现，但不等于回放时钟或 QoS 闭环正确，见 M3/M4；上一轮 30 消息录回计数不是本轮重新执行的结果 |
| 新增测试 | 回归覆盖明显增加，但本轮原样 98 项中有真实失败；还存在 M5/M6 的假阳性和隔离缺口，不能以历史绿色结果替代负向/并发审查 |

依赖方面：新加 `geometry_msgs` 被共享四元数工具实际使用；新增测试依赖与直接导入相符，未发现不必要的重型依赖。三个四元数实现已集中，原模块仍保留导入符号。`.msg`、Topic 常量和默认 QoS YAML 相对 master 没有改动；数值语义修正与配置严格化不等于所有旧行为完全不变。

文档方面：`docs/26_runtime_optimization_review.md` 对性能范围、真实硬件未验证、缓存元数据策略及回放时间限制的说明基本准确；其中“启动失败也销毁节点”和整体退出安全的表述需要结合 H1/M1 收窄。98 项通过是上一轮最终运行的历史事实，不能覆盖本轮发现的竞态。源码中重复 import 仍存在，未自动修正。

## 合并决定及第二阶段顺序

1. **是否建议合并 PR #2：目前不建议。** 先修复 H1，补全信号时序矩阵和真实异常不被吞噬的回归，再重新执行 pytest、colcon 和代表性完整图退出测试。保留现有 PR，不必重写其历史。
2. **是否存在此前遗漏的高风险：有，H1 已被自然失败和确定性时序注入共同确认。** 未发现 CRITICAL；没有证据能够保证其他平台、双机或硬件场景不存在未知高风险。
3. **可放到第二阶段的问题：** M1–M8、L1–L4 可按支持场景排期；若本轮要承诺组合 Launch 或可靠回放验收，M2–M5 应提前完成，不能先宣称这些场景已就绪。默认单机 mock 的合并门槛仍首先是 H1。
4. **第二阶段优先级：** 先改进失败判定与测试隔离，再做显式 QoS schema/Launch 作用域与回放 QoS 配置，随后统一 live/replay 时间语义和指标。补充资源清理、动态 TF 输入校验与持续心跳健康模型。最后在真实双机 Discovery Server、同步时钟、断连重连/弱网及目标硬件上验证延迟、吞吐与安全退出，不能用当前本机结果外推。

本轮未修复上述问题，报告未提交、未推送；建议和合并决定不代表已实施变更。
