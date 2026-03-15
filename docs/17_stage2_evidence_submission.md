# 17 Stage2 Evidence Submission

stage2 结束后，不要只说“跑过了”。请把证据一起保存。

## 必留证据

### 1. 终端输出

至少保留下面这些命令对应的终端输出或日志：

- `./scripts/prepare_dual_machine_env.sh --env-file ...`
- `./scripts/net_baseline_check.sh <peer_ip>`
- `ping -c 4 <peer_ip>`
- `./scripts/dual_machine_server_smoke.sh --env-file ...`
- `./scripts/dual_machine_client_smoke.sh --env-file ...`
- `./scripts/run_server_discovery.sh --env-file ...`
- `./scripts/run_client_discovery.sh --env-file ...`
- `./scripts/validate_dual_machine_topics.sh`
- `CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh`

这些终端输出能证明：

- 当时实际执行了哪些命令
- 环境变量是否读对
- 关键 topic 是否出现
- `hz` / `bw` / `delay` 是否被实际观测

这些终端输出不能单独证明：

- Discovery Server 长时间稳定运行
- 弱网或复杂网络环境已经验证
- 多机扩展已经验证

## 2. rosbag 目录

如果现场录了 bag，请保留完整目录，例如：

```bash
bags/stage2_20260315_221500
```

它能证明：

- 当时至少录下了 stage2 关键 topic 数据
- 后续可以离线回放和复盘

它不能单独证明：

- 真实双机网络链路一定稳定
- Discovery Server 一定真实运行过
- 现场 `hz` / `bw` / `delay` 一定满足要求

## 3. collect_stage2_evidence 生成目录

请保留 `collect_stage2_evidence.sh` 的输出目录，例如：

```bash
artifacts/stage2_runs/<timestamp>_<hostname>_<role>/
```

建议至少保留这些文件：

- `acceptance_snippet.md`
- `capture_status.txt`
- `ros_env_summary.txt`
- `hostname.txt`
- `date.txt`
- `uname_a.txt`
- `ip_a.txt`
- `ros2_node_list.txt`
- `ros2_topic_list.txt`
- 可选的 `uav_targets_current_once.txt`
- 可选的 `uav_odom_hz.txt`
- 可选的 `uav_map_tile_bw.txt`

这些文件能证明：

- 测试时主机是谁
- 当时 ROS 关键环境变量是什么
- 当时 ROS graph 里有哪些 node / topic
- 是否真的执行过目标回显、频率采样、带宽采样

这些文件不能单独证明：

- 跨机 topic 一定来自真实对端，而不是本机假设环境
- 网络吞吐、丢包、发现稳定性已经完整验证

## 4. 关键截图建议

建议至少保留下面这些截图：

- 机器 A 执行 `prepare_dual_machine_env.sh --env-file ...` 的输出
- 机器 B 执行 `prepare_dual_machine_env.sh --env-file ...` 的输出
- 默认发现 smoke 同时运行时的两个终端窗口
- Discovery Server smoke 同时运行时的两个终端窗口
- `validate_dual_machine_topics.sh` 成功输出
- `stage2_acceptance_check.sh` 的 `hz` / `bw` / `delay` 采样结果
- rosbag 录制目录生成后的终端输出

截图的作用是帮助快速对照现场状态，但截图仍然不能替代原始命令输出和原始证据目录。

## 5. 验收模板填写结果

请把现场结果补全到：

```bash
docs/acceptance_stage2_template.md
```

建议填写完成后另存一份测试记录，例如：

```bash
docs/acceptance_stage2_20260315.md
```

这份填写结果能证明：

- 测试范围是什么
- 实际跑了什么
- 结论是什么
- 还缺什么

它不能代替：

- 原始终端输出
- rosbag 原始目录
- `artifacts/stage2_runs/...` 原始证据目录

## 最小提交清单

一次 stage2 真实执行结束后，最少建议归档：

- 1 份已填写的验收文档
- 1 份 machine A 的证据目录
- 1 份 machine B 的证据目录
- 1 份 rosbag 目录
- 关键终端截图

## 明确不要过度声称

如果这次没有真实双机、没有真实网络、没有真实 Discovery Server 现场，请明确写成：

- 工具已准备
- 文档已准备
- 单机基线已回归
- 真实双机结果待补测

不要把工具准备完成，写成真实双机验证完成。
