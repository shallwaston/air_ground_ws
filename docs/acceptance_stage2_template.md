# Acceptance Stage 2 Template

## 测试目的

记录 stage2 双机通信、Discovery Server、rosbag 录制/回放和短时验收采样的实际结果，并明确区分：

- 哪些结论来自真实双机现场
- 哪些结论只来自单机或离线回放
- 哪些内容还不能声称已验证

## 本次测试范围

- [ ] 默认发现双机冒烟
- [ ] Discovery Server 双机冒烟
- [ ] stage2 rosbag 录制
- [ ] stage2 rosbag 回放
- [ ] `stage2_acceptance_check.sh` 短时采样

## 测试环境

- 测试日期：
- 测试人员：
- workspace 路径：
- workspace 版本或 commit：
- ROS 版本：
- 是否真实双机环境：
- 网络类型：
- 交换机 / 路由 / 直连说明：
- 其他说明：

## 机器 A 信息

- 角色：UGV / server
- hostname：
- IP：
- Ubuntu 版本：
- `ROS_DOMAIN_ID`：
- `RMW_IMPLEMENTATION`：
- `ROS_LOCALHOST_ONLY`：
- `ROS_DISCOVERY_SERVER`：
- `fastdds` CLI 是否存在：

## 机器 B 信息

- 角色：UAV / client
- hostname：
- IP：
- Ubuntu 版本：
- `ROS_DOMAIN_ID`：
- `RMW_IMPLEMENTATION`：
- `ROS_LOCALHOST_ONLY`：
- `ROS_DISCOVERY_SERVER`：
- `fastdds` CLI 是否存在：

## 预检查记录

- `./scripts/build_ws.sh`：
- `./scripts/prepare_dual_machine_env.sh`：
- `./scripts/net_baseline_check.sh <peer_ip>`：
- `ping -c 4 <peer_ip>`：
- `iperf3` TCP 基线：
- `iperf3` UDP 基线：

## 执行命令

请按实际执行顺序填写，不要写成计划命令。

### 机器 A

```bash
# 例如：
# ./scripts/dual_machine_server_smoke.sh
# ./scripts/run_server_discovery.sh 192.168.0.10 11811
```

### 机器 B

```bash
# 例如：
# ./scripts/dual_machine_client_smoke.sh
# ./scripts/run_client_discovery.sh 192.168.0.10 11811
```

### 观测与验收命令

```bash
# 例如：
# ./scripts/validate_dual_machine_topics.sh
# CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
# ./scripts/rosbag_record_stage2.sh bags/stage2_run_01
# ./scripts/rosbag_play_stage2.sh bags/stage2_run_01
```

## 预期现象

- 两台机器都能正常 source ROS 和 workspace
- 默认发现或 Discovery Server 模式下，关键 stage2 topics 可见
- `validate_dual_machine_topics.sh` 返回成功
- `stage2_acceptance_check.sh` 能采到 `list`、`hz`、`bw`、`echo`、`delay`
- 如果做了 rosbag 录制，bag 目录会成功生成
- 如果做了 rosbag 回放，关键 topics 在回放期间可再次被观测

## 实际结果

请只记录现场实测结果，不要填写推测值。

- 默认发现双机冒烟：
- Discovery Server 双机冒烟：
- `validate_dual_machine_topics.sh`：
- `stage2_acceptance_check.sh`：
- `/uav/odom` 频率观测：
- `/uav/map/tile` 带宽观测：
- `/system/delay_probe` 时延观测：
- `ros2 topic echo /uav/targets/current --once`：
- rosbag 输出目录：
- rosbag 回放结果：

## 证据留档

- 命令行日志路径：
- 截图或终端录屏：
- bag 路径：
- 其他附件：

## 当前还不能声称已验证的内容

如果本次不是完整真实双机现场，必须在这里明确写出未验证项。

- 真实双机默认发现稳定性：
- 真实双机 Discovery Server 运行状态：
- 实际跨机带宽 / 丢包 / 时延：
- 长时间稳定运行：
- 多机扩展场景：

## 失败排查点

- 网络是否互通
- 两边 `ROS_DOMAIN_ID` 是否一致
- `ROS_LOCALHOST_ONLY` 是否误设成 `1`
- build 是否最新
- 关键 launch 是否成功启动
- `fastdds` CLI 是否存在并成功运行
- `ROS_DISCOVERY_SERVER` 是否写成真实 UGV IP
- topic / tf / delay 是否符合预期

## 是否通过

- 结论：通过 / 部分通过 / 未通过
- 结论依据：
- 后续待办：
