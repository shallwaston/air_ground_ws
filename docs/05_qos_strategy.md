# 05 QoS Strategy

## 设计原则

QoS 在这个项目里不是散落在节点代码里的临时参数，而是一个集中管理的系统策略。

我们把 QoS 分成两层：

- YAML：给人看、给 launch 配置
- `ag_network_tools/qos_profiles.py`：给代码统一构造 `QoSProfile`

## 当前关键策略

- `/uav/map/tile`
  - Reliable + Transient Local
- `/uav/targets/current`
  - Reliable + Transient Local
- `/uav/odom`
  - Best Effort + Volatile
- `/tf`
  - Best Effort + Volatile
- `/tf_static`
  - Reliable + Transient Local
- `/system/delay_probe`
  - Reliable + Volatile

## 为什么这样分

### `/uav/map/tile`

地图切片体积大、对接收可靠性敏感，因此优先：

- Reliable
- Transient Local

这样晚启动的接收端也更容易拿到最近一份有效切片。

### `/uav/targets/current`

目标列表通常频率不高，但对“最新一条状态”有意义，因此也采用：

- Reliable
- Transient Local

### `/uav/odom` 和 `/tf`

定位和 TF 通常频率高、更新快，旧数据价值低，因此采用：

- Best Effort
- Volatile

## QoS 文件关系

- `config/qos/qos_profiles.yaml`
  - 根目录人工编辑版
- `src/ag_bringup/config/qos_profiles.yaml`
  - build 后随 `ag_bringup` 安装的运行版

## 代码入口

统一入口：

- `ag_network_tools/topic_names.py`
- `ag_network_tools/qos_profiles.py`

任何新节点都应优先调用：

- `get_qos_profile_for_topic(...)`

不建议在节点内部手写重复 QoS。

## 调试建议

### 想看当前策略

```bash
ros2 run ag_monitor qos_inspector
```

### 想做压力测试

```bash
ros2 launch ag_bringup qos_stress_test.launch.py
```

### 想修改策略

先改 YAML，再看：

```bash
ros2 run ag_monitor qos_inspector
```

确认输出与你预期一致。
