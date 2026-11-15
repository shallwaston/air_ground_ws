# STRICT ISOLATED S1 — 限定生产接口合同 v1

本合同只覆盖 R7 明确批准的三个固定入口及其部署封装。它不是把原21个入口自动迁移，也不代表 M6 已获准实施。legacy in-process S1 仍为 BLOCKED/UNCHANGED。

## 平台与信任根

支持受控 Linux/amd64、具备 sealed memfd、pidfd 和完整可见 `/proc` 的固定 Jazzy 环境。验收镜像 ID 为 `sha256:3e1ba97a2cda53301c6ba7e831e2c8506e54631f911c0bd26cfbc976479810c7`，digest 为 `ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617`；使用镜像内 Python 3.12.3 和该固定 Jazzy/rclpy ABI。外层部署门禁负责验证容器/镜像/UID/挂载/CA/环境，包本身不声称能在容器内独立证明宿主镜像身份。

父进程是受授权、可信的直接监督者。它可以已有 Python/C handler、自己的 Context、Python/native 线程；不得有竞争的 wait-any reaper，不得忽略 SIGCHLD、窃取/破坏监督 FD 或并发修改部署包。一个 Session 仅由创建它的 Python 线程管理。root/ptrace/恶意包所有者不属于此 Python API 的安全隔离对手。

## 唯一公开入口

使用 `ag_network_tools.strict_entry.create_session(entry, output)`，或安装的固定脚本：

```bash
ros2 run ag_network_tools ag_strict_isolated \
  --entry heartbeat_pub --output /new/owned/empty-output --run-for 30
```

`output` 必须是调用者明确拥有、此前不存在的新目录。公开接口不接受任意 Node 类、probe 路径、bootstrap 扩展、ROS 参数、domain、RMW 或外部插件。CLI 的 `--run-for` 是主动计划停止时间，触发已绑定子进程 SIGINT，不是用延长失败超时取得成功。无此参数时长期节点持续受监督；调用者负责显式请求停止。CLI 尊重原父 Python SIGINT 语义，不安装父 handler；它不能替任意 foreign 父 handler 解释信号。突然杀死父进程不是已证明的完整生产生命周期；需要另行监督恢复政策。

许可清单及完整参数元组在 `isolated_entries.py`，不得在调用时扩张：

| 入口 | 类/回调 | 固定配置 |
|---|---|---|
| tf_healthcheck | TfHealthcheck / run_check | one_shot=true，check_period_sec=0.5 |
| heartbeat_pub | HeartbeatPub / on_timer | frequency_hz=5.0，node_name=r7_strict_heartbeat，role=r7-isolated，status=1，detail=alive |
| ugv_map_tile_sub | UgvMapTileSub / on_tile | log_every_n=1 |

这些是限定配置，不是现有单机 launch 的系统角色/required_nodes 替代方案。业务源码、Topic、QoS、Frame、消息定义未改。尚未证明完整系统拓扑、吞吐、双机或硬件等价性。新增参数/入口须先审查、生成新封装并独立验证。

## 受控出生与 READY

子进程必须是可信 `Popen + exec`、`-I -S` 全新地址空间，不继承父 ROS 对象、Python handler 缓存或默认 Executor。禁止 preexec_fn、Node pickle、fork 后执行父 Python ROS 对象。

父保留原 `/proc` 锚点和 pidfd。第一次观察只绑定出生身份，不授信号权；私有 pipe、不可猜测 nonce、序列号及 challenge/ACK 后，在原锚点复核 PID/starttime/PPID/UID/namespace/exe/argv/SID/PGID 才授予信号能力。只可经同一 pidfd 向拥有的子进程发送 INT/TERM，无数字 PID/PGID 回退。

ROS/第三方加载之前，子进程必须是实际一个内核任务、主线程、INT/TERM 不被屏蔽、没有继承 IGN、Python/native 动作与可信 fresh-exec 最早指纹一致。拒绝发生在 mask/handler 修改前。该初始快照不适用于任意已有进程，也不是进程级原子共存证明。

唯一 owner 在可信出生窗口安装自己的 handler，只恢复自己进入前的线程 mask；不在退出时写回旧 Python/native sigaction。随后只从明确验证路径/封装加载 Jazzy。private Context、明确 SingleThreadedExecutor、实际许可 Node 及注册、真实 handler 和依赖状态全部通过后才 ROS_READY；父 START 才开始同步回调。

owner 建立之前的早期退出采用真实 OS/Python 语义，可能非零。managed 但尚未 READY 时可协作取消，退出0也不能假装 READY 验收成功。不声称任意时点 SIGINT 都干净退出。

## 资源、信号与异常

只拥有本次创建的 Context/Executor/Node、直接子进程和监督引用。父/foreign Context 永不由子进程 shutdown。同步、有界回调返回之前不得破坏性关闭 Context。只支持固定 single-threaded Python 回调；固定 Jazzy/RMW 内部已核验线程不是任意业务线程的许可。

信号 handler 只设置停止标志。正常顺序为 Executor shutdown、Node/实体销毁、同一 private Context try_shutdown/destroy、直接 waitpid、监督 FD 退役。部分初始化 guard 各自独立清理。清理错误不遮盖业务错误，BaseExceptionGroup 保留原对象、traceback 和阶段；没有业务错误也不能丢弃清理错误。

动态 native owner 接管不属于安全共存范围。观测冲突后保留实际动作，不恢复覆盖第三方；尽可能关闭仍拥有的资源并真实失败退出。不能保证观察到任意短暂竞争写入。清理 API 生效前故障造成未关闭对象时，必须保留 still-valid/UNKNOWN 证据；进程退出不等于 ROS 优雅清理证明。

原始 `waitpid` 状态、Python returncode、CLI 自己的 shell code 分开记录。超时、丢 READY、恢复 TERM、清理错误或未知残留都不能报告正常 PASS。无 SIGKILL 成功兜底、无生产重试；不能安全终止时保留责任和证据。

## 来源和部署

只读 C 探针使用系统头文件的真实 sigaction/pthread API，无 ctypes struct 猜测。构建记录 C_SOURCE、编译器/flags、probe.so、生成接口库及源码 SHA；部署从安装包的 `strict_assets` 读取，拒绝可写/符号链接/校验不符资产。`_strict_asset_pin.py` 绑定该次 manifest，不接受测试目录临时 probe。

应用源码和生成接口 Python 放入受核验 source.zip；必要接口原生库以 sealed memfd 加载，ROOT ROS/stdlib 路径需 root 所有且组/其他不可写。本次接口库以 CMAKE_SKIP_RPATH=ON 构建，不通过旧 overlay、任意 PYTHONPATH 或扩大 native 搜索路径恢复依赖。每次重新构建可生成新发布 pin；源码 SHA 不是二进制 SHA，移动同一发行包与重新构建是两种验证。

严格资源逻辑由 R4 的 `_RunContext`、`_destroy_node` 精确提取为独立内部模块。strict 子封装不包含真实 legacy node_runner；仅为许可业务 main 提供严格桥接的 run_node/request_stop，旧 manager 属性和任意 Node 类被拒绝。21个旧入口仍为兼容路径，不获得新模式的安全结论。

## M6 约束

未来 M6 如需使用此范围，必须只通过上述 facade、固定许可配置和部署门禁，不能导入 legacy run_node/_stop_signals 或内部测试扩展。M6 的具体入口集合、资源/Domain 规则和调用图尚未确定，强制 CI/导入政策尚待实施，18个入口未迁移。因此 **M6 G1 仍 BLOCKED**。这不是 ResourceScope、DomainPool 或通用 ProcessProof 的实现授权。
