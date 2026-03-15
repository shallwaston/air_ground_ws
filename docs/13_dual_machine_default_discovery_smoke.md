# 13 Dual Machine Default Discovery Smoke

## 目标

这份文档用于做 stage2 的双机默认发现冒烟测试，也就是先不引入 Discovery Server，只确认下面这些基础条件已经成立：

- 两台机器网络互通
- 两台机器 ROS 环境一致
- 默认发现模式下能看到关键 stage2 topics
- 后续切到 Discovery Server 之前，单机基线之外的最小双机链路已经打通

推荐把这一步当成 Discovery Server 之前的必经基线。

## 角色约定

- 机器 A：UGV / server 侧
- 机器 B：UAV / client 侧

对应脚本：

- 机器 A：`./scripts/dual_machine_server_smoke.sh`
- 机器 B：`./scripts/dual_machine_client_smoke.sh`

## 前提条件

- 两台机器都能访问同一份工程，或者至少代码版本一致
- 两台机器都已安装 ROS 2 Jazzy
- 两台机器都已执行过 `./scripts/build_ws.sh`
- 两台机器都能互相 `ping`
- 两台机器使用相同的 `ROS_DOMAIN_ID`
- 两台机器不能设置 `ROS_LOCALHOST_ONLY=1`

说明：

- 当前默认发现脚本会主动 `unset ROS_DISCOVERY_SERVER`
- 当前默认发现脚本也会主动 `unset ROS_LOCALHOST_ONLY`
- 当前默认发现脚本会把 `RMW_IMPLEMENTATION` 默认设成 `rmw_fastrtps_cpp`，主要是为了后续切换 Discovery Server 时减少变量

## 推荐执行顺序

### 1. 两边先做环境自检

在机器 A 和机器 B 上分别执行：

```bash
./scripts/prepare_dual_machine_env.sh
```

重点确认输出里这些值没有明显问题：

- `ROS_DISTRO=jazzy`
- `ROS_LOCALHOST_ONLY` 不是 `1`
- `ROS_DOMAIN_ID` 两边一致
- `hostname -I` 能看到当前测试网卡 IP

如果当前 shell 已经手动 source 过 ROS 和 workspace，也可以使用：

```bash
./scripts/prepare_dual_machine_env.sh --skip-source
```

### 2. 先确认网络基线

在任意一侧执行：

```bash
./scripts/net_baseline_check.sh <peer_ip>
```

这个脚本不会修改系统配置，只会打印建议命令。至少建议现场完成：

```bash
ping -c 4 <peer_ip>
```

如果 `iperf3` 已安装，再补做 TCP / UDP 基线。

### 3. 先用 check-only 确认脚本准备无误

机器 A：

```bash
./scripts/dual_machine_server_smoke.sh --check-only
```

机器 B：

```bash
./scripts/dual_machine_client_smoke.sh --check-only
```

这一步不会启动 launch，只会打印角色、IP、ROS 环境和下一步命令。

### 4. 启动默认发现双机链路

机器 A：

```bash
./scripts/dual_machine_server_smoke.sh
```

机器 B：

```bash
./scripts/dual_machine_client_smoke.sh
```

如果需要向 launch 额外传参，可以直接附在脚本后面：

```bash
./scripts/dual_machine_server_smoke.sh key:=value
./scripts/dual_machine_client_smoke.sh key:=value
```

## 如何验证链路已经打通

推荐在能够观察全局 topic 的那一侧执行：

```bash
./scripts/validate_dual_machine_topics.sh
```

期望至少能看到这些 stage2 关键 topics：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/system/delay_probe`
- `/tf`

如果想继续做一个短时验收采样，可以执行：

```bash
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

这个脚本会依次做：

- `ros2 topic list`
- `ros2 topic hz /uav/odom`
- `ros2 topic bw /uav/map/tile`
- `ros2 topic echo /uav/targets/current --once`
- `ros2 topic delay /system/delay_probe`

如果当前环境没有 `ros2 topic delay`，脚本会自动回退到 `ag_monitor` 的 delay probe subscriber。

## 失败时优先排查

按优先级建议这样查：

1. 两台机器是否真的能互相 `ping`
2. 两边 `ROS_DOMAIN_ID` 是否一致
3. 是否有 shell 启动脚本把 `ROS_LOCALHOST_ONLY=1` 又写回来了
4. 两边是否都成功 source 了 `/opt/ros/jazzy/setup.bash` 和 `install/setup.bash`
5. 防火墙或网段策略是否阻断了默认发现
6. 机器 B 是否真的启动了 `dual_machine_client.launch.py`
7. 机器 A 是否真的启动了 `dual_machine_server.launch.py`

## 通过标准

最小通过标准建议定义为：

- 环境检查脚本输出正常
- 网络基线检查通过
- 双机 launch 能同时启动
- `validate_dual_machine_topics.sh` 返回成功
- `stage2_acceptance_check.sh` 能采到 topic list、hz、bw、echo、delay 信息

## 这一步不能替代什么

默认发现冒烟通过，并不等于下面这些内容已经被验证：

- Discovery Server 模式稳定可用
- 弱网下的发现稳定性已经验证
- 长时间运行下的带宽和时延指标已经验证
- 多 UAV / 多 UGV 拓扑已经验证

这些内容需要在真实双机环境里继续补测，并记录到 `docs/acceptance_stage2_template.md`。
