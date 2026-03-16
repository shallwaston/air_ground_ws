# 22 新人第一周上手计划（ROS 2 空地协同 MVP）

> 目标：让新人在 5~7 天内，从“能跑”到“能定位问题”，再到“能做小改动并验证不破坏骨架”。

---

## Day 0（入场准备，0.5 天）

### 目标
- 搭好本地环境并确认依赖。
- 对仓库定位有整体感。

### 要做什么
1. 阅读 `README.md`（重点看工程目标、目录、单机/双机启动、QoS、诊断脚本）。
2. 核对环境：Ubuntu 24.04 + ROS 2 Jazzy + colcon。
3. 浏览顶层目录：`src/`、`config/`、`docs/`、`scripts/`。

### 建议命令
```bash
cd /workspace/air_ground_ws
./scripts/build_ws.sh
source scripts/source_ws.sh
```

### 完成标准
- 能说清项目不是“真实硬件驱动工程”，而是“可替换通信骨架 MVP”。
- 能说清 7 个核心包各做什么。

---

## Day 1（单机闭环跑通，1 天）

### 目标
- 在单机上跑通完整 mock 系统。
- 熟悉关键 topic 与基础检查手段。

### 要做什么
1. 启动单机 launch：`single_machine_mock.launch.py`。
2. 检查关键 topic：`/uav/odom`、`/uav/map/tile`、`/uav/targets/current`、`/system/heartbeat`、`/system/delay_probe`。
3. 跑一次频率/带宽/延迟/TF 检查。

### 建议命令
```bash
./scripts/run_single_machine.sh
./scripts/check_topics.sh
./scripts/check_hz.sh /uav/odom
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
./scripts/check_tf.sh
```

### 完成标准
- 能确认系统确实在持续发布数据。
- 能解释检查脚本各自在看什么指标。

---

## Day 2（读懂数据合同与边界，1 天）

### 目标
- 建立“接口合同优先”的意识。
- 知道哪些字段与 topic 不能随意改。

### 要做什么
1. 阅读 `docs/04_interface_contracts.md`。
2. 重点理解：
   - `MapTile.msg` 的 `source_stamp` 与 `seq` 的用途；
   - `DelayProbe.msg` 在 `ros2 topic delay` 不可用时的价值；
   - `Heartbeat.msg` 的状态语义。
3. 打开 `src/ag_interfaces/msg/*.msg` 与测试文件对照。

### 建议命令
```bash
# 阅读消息定义
sed -n '1,200p' src/ag_interfaces/msg/MapTile.msg
sed -n '1,200p' src/ag_interfaces/msg/TargetInfo.msg
sed -n '1,200p' src/ag_interfaces/msg/Heartbeat.msg
sed -n '1,200p' src/ag_interfaces/msg/DelayProbe.msg

# 阅读合同测试
sed -n '1,220p' src/ag_system_tests/test/test_message_contracts.py
```

### 完成标准
- 能说出“真实模块接入时，优先保持 topic/message/frame/launch 不变”的原因。
- 能描述至少 3 个关键字段的工程意义。

---

## Day 3（QoS 与通信策略，1 天）

### 目标
- 理解 QoS 为什么集中管理。
- 会从 YAML 到代码追踪 QoS 生效路径。

### 要做什么
1. 阅读 `docs/05_qos_strategy.md`。
2. 对照 `config/qos/qos_profiles.yaml` 与 `src/ag_bringup/config/qos_profiles.yaml`。
3. 阅读 `ag_network_tools/qos_profiles.py` 和 `topic_names.py`。
4. 运行 `qos_inspector` 观察输出。

### 建议命令
```bash
ros2 run ag_monitor qos_inspector
```

### 完成标准
- 能说明 `/uav/map/tile` 与 `/uav/odom` QoS 的差异及动机。
- 能定位“某 topic QoS 是从哪份配置来的”。

---

## Day 4（排障演练，1 天）

### 目标
- 按标准流程定位常见问题。
- 建立“先环境、再 launch、再合同、再 QoS/TF”的排查顺序。

### 要做什么
1. 阅读 `docs/03_debug_playbook.md`。
2. 做两次故障演练：
   - 演练 A：不 source 环境直接启动，观察报错后修复；
   - 演练 B：故意停掉一个关键节点（如 `frame_alignment_stub`），再用 `check_tf.sh` 定位问题。
3. 记录你的“最短排障路径”。

### 完成标准
- 能在 10 分钟内定位“有 topic 但无数据”类问题的大方向。
- 能给出 TF 缺失时的优先检查清单。

---

## Day 5（小改动 + 验证 + 复盘，1~2 天）

### 目标
- 完成一次安全的小改动并自证不破坏系统。

### 推荐小改动（任选其一）
- 修改某个 mock 节点发布频率/日志文本；
- 为 `topic_watchdog` 增加一个关注 topic；
- 调整一个非关键 QoS depth，并验证系统行为。

### 验证建议
```bash
# 代码改动后至少执行
./scripts/build_ws.sh
source scripts/source_ws.sh
./scripts/run_single_machine.sh
./scripts/check_topics.sh
./scripts/check_hz.sh /uav/odom
./scripts/check_tf.sh
```

并补跑：
```bash
# 如果环境已满足 ROS 测试依赖，建议执行
colcon test --packages-select ag_system_tests
colcon test-result --verbose
```

### 完成标准
- 能提交一条有意义的小改动并解释影响范围。
- 能展示“改动前后”的观测结果（至少 topic 与 tf）。

---

## 第 2 周建议（进阶）

1. 进入双机 Discovery Server：先按文档做最小联调，再做日志留存。
2. 练习 rosbag 录制/回放与回归对比。
3. 按 `docs/11_future_integration_points.md` 选 1 个 adapter stub，做“真实模块替换设计草案”（不改合同）。

---

## 新人常见误区（请避开）

- 误区 1：先改接口再改实现。  
  正解：先守住合同（topic/message/frame），实现逐步替换。

- 误区 2：在节点里到处散写 QoS。  
  正解：统一走 `ag_network_tools/qos_profiles.py`。

- 误区 3：双机问题先怀疑代码。  
  正解：先检查 `RMW_IMPLEMENTATION`、`ROS_DISCOVERY_SERVER`、网络联通、时钟同步。

---

## 建议的学习产出（交付物）

到第一周结束时，请新人提交以下 4 个文档或记录：
1. 一张系统数据流图（UAV 侧 -> 传输 -> UGV 侧）。
2. 一份“关键 topic 与消息字段语义”清单。
3. 一份“我的排障流程”清单（含命令）。
4. 一次小改动 PR（附运行与检查结果）。
