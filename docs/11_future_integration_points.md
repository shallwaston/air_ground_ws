# 11 Future Integration Points

## 总原则

未来接入真实模块时，优先保留已有 topic / message / frame / launch 接口，减少对整套系统的冲击。

## 1. FAST-LIO2 adapter

替换节点：

- `ag_mock_nodes/uav_mock_odom_tf_pub.py`

建议保持：

- `/uav/odom`
- `map` 或兼容的上层参考系
- `uav/base_link`

## 2. 2.5D map builder adapter

替换节点：

- `ag_mock_nodes/uav_mock_map_tile_pub.py`

建议保持：

- `/uav/map/tile`
- `MapTile.msg`
- `source_stamp`
- `seq`

## 3. EKF adapter

替换节点：

- `ag_tf_tools/frame_alignment_stub.py`

建议保持：

- `map -> ugv/odom`

## 4. Nav2 adapter

替换节点：

- `ag_mock_nodes/ugv_nav_sink_stub.py`

建议保持：

- 输入仍消费 `/uav/map/tile`
- 需要时可扩展本地 costmap / planner 桥接

## 5. target detector adapter

替换节点：

- `ag_mock_nodes/uav_mock_target_pub.py`

建议保持：

- `/uav/targets/current`
- `TargetInfo.msg`

## 6. arm target adapter

替换节点：

- `ag_mock_nodes/arm_target_sink_stub.py`

建议保持：

- 继续订阅 `TargetInfo`

## 7. hardware bridge

建议新增位置：

- 独立桥接包，或在现有 bringup 中单独 launch

职责建议：

- 与真实底盘、机械臂、传感器驱动对接
- 向 ROS 2 世界暴露稳定 topic / service / action 接口

## 当前阶段刻意不做的事

- 不伪造真实驱动
- 不猜真实端口号
- 不猜控制器型号
- 不猜 CAN / USB / 串口参数

这样做的目的，是让这个 MVP 真正成为“未来可替换的骨架”，而不是一堆看似完整但无法落地的假配置。
