# 16 Stage2 Real Execution Order

这份清单只面向真实双机 stage2 执行。按顺序做，不要跳步。

## 1. 先准备实际 env 文件

在两台机器各自的 workspace 根目录执行：

```bash
cp env/machine_a_default.env.example env/machine_a_default.env
cp env/machine_b_default.env.example env/machine_b_default.env
cp env/discovery_server.env.example env/machine_a_discovery.env
cp env/discovery_server.env.example env/machine_b_discovery.env
```

然后按真实环境修改：

- `env/machine_a_default.env`
- `env/machine_b_default.env`
- `env/machine_a_discovery.env`
- `env/machine_b_discovery.env`

至少改这些字段：

- `WORKSPACE_PATH`
- `ROS_DOMAIN_ID`
- `STAGE2_MACHINE_ROLE`
- `DISCOVERY_SERVER_IP`
- `DISCOVERY_SERVER_PORT`
- `ROS_DISCOVERY_SERVER`

说明：

- `env/*.env.example` 只是示例文件
- 实际使用时请传 `env/*.env`
- `env/*.env` 已被 `.gitignore` 忽略，不会污染版本库

## 2. 机器 A / 机器 B 先做前置检查

机器 A：

```bash
./scripts/prepare_dual_machine_env.sh --env-file env/machine_a_default.env
```

机器 B：

```bash
./scripts/prepare_dual_machine_env.sh --env-file env/machine_b_default.env
```

先确认输出里没有明显问题，再继续：

- `ROS_DISTRO=jazzy`
- `ROS_DOMAIN_ID` 两边一致
- `ROS_LOCALHOST_ONLY` 不是 `1`
- `hostname -I` 能看到真实测试网卡 IP

## 3. 先做网络检查

机器 A 对机器 B：

```bash
./scripts/net_baseline_check.sh <machine_b_ip>
ping -c 4 <machine_b_ip>
```

机器 B 对机器 A：

```bash
./scripts/net_baseline_check.sh <machine_a_ip>
ping -c 4 <machine_a_ip>
```

如果 `iperf3` 已安装，再补做：

```bash
iperf3 -s
iperf3 -c <peer_ip>
./scripts/iperf_udp_server.sh
./scripts/iperf_udp_client.sh <peer_ip> 50M 30 5201
```

## 4. 先做默认发现双机 smoke

先用 check-only 看配置是否读对：

机器 A：

```bash
./scripts/dual_machine_server_smoke.sh --env-file env/machine_a_default.env --check-only
```

机器 B：

```bash
./scripts/dual_machine_client_smoke.sh --env-file env/machine_b_default.env --check-only
```

确认无误后正式启动：

机器 A：

```bash
./scripts/dual_machine_server_smoke.sh --env-file env/machine_a_default.env
```

机器 B：

```bash
./scripts/dual_machine_client_smoke.sh --env-file env/machine_b_default.env
```

启动后在能观察全局图的一侧执行：

```bash
./scripts/validate_dual_machine_topics.sh
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

## 5. 再做 Discovery Server smoke

只有默认发现 smoke 通过后再做这一步。

机器 A：

```bash
./scripts/run_server_discovery.sh --env-file env/machine_a_discovery.env
```

机器 B：

```bash
./scripts/run_client_discovery.sh --env-file env/machine_b_discovery.env
```

如果机器 A 上已经有单独的 Discovery Server 终端在运行，就改成：

```bash
START_DISCOVERY_SERVER=0 ./scripts/run_server_discovery.sh --env-file env/machine_a_discovery.env
```

启动后再次执行：

```bash
./scripts/validate_dual_machine_topics.sh
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

## 6. 录制 rosbag

在能看到完整 stage2 topics 的那一侧执行：

```bash
./scripts/rosbag_record_stage2.sh bags/stage2_$(date +%Y%m%d_%H%M%S)
```

录到需要的时长后按 `Ctrl+C` 停止。

## 7. 采集 stage2 证据

建议机器 A 和机器 B 都各自执行一次：

机器 A：

```bash
./scripts/collect_stage2_evidence.sh \
  --env-file env/machine_a_default.env \
  --collect-target-once \
  --collect-odom-hz \
  --collect-map-bw
```

机器 B：

```bash
./scripts/collect_stage2_evidence.sh \
  --env-file env/machine_b_default.env \
  --collect-target-once \
  --collect-odom-hz \
  --collect-map-bw
```

如果是 Discovery Server 模式，也可以把 env 文件换成：

```bash
env/machine_a_discovery.env
env/machine_b_discovery.env
```

证据目录默认会生成在：

```bash
artifacts/stage2_runs/<timestamp>_<hostname>_<role>/
```

## 8. 回放 rosbag

如果需要离线复盘，再执行：

```bash
./scripts/rosbag_play_stage2.sh bags/<stage2_bag_dir>
```

回放期间可再次执行：

```bash
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

## 9. 填写验收模板

把现场命令、证据目录、bag 路径和实际观察结果填进：

```bash
docs/acceptance_stage2_template.md
```

填写时只写现场实测结果，不要把“计划要测的内容”写成“已完成”。

## 10. 最后一起归档

至少保留下面这些内容：

- 终端输出
- `bags/<stage2_bag_dir>`
- `artifacts/stage2_runs/<timestamp>_<hostname>_<role>/`
- `docs/acceptance_stage2_template.md` 的填写结果

归档细则见：

- `docs/17_stage2_evidence_submission.md`
