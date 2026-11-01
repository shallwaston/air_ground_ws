# H1 第二轮验证证据

源代码基线：`0143ffbcf5a78e55cde9d963fcf244084e7cb555`；
精确被测源文件与日志的 SHA-256 见 `lifecycle-summary.json`。
当前版本：Ubuntu 24.04、ROS 2 Jazzy / Fast DDS、rclpy
`7.1.12-1noble.20260912.162354`、Python 3.12.3。

| 顺序 | 日志 | 实际结果 |
| --- | --- | --- |
| 1 | pytest.log | 完整套件 194 passed；domain 72 |
| 2 | colcon-build.log | 7 packages finished；domain 73 |
| 3 | colcon-test.log | 全工作区测试，194 passed；domain 73 |
| 4 | test-result.log | 194 tests, 0 errors, 0 failures, 0 skipped |
| 5 | mock-smoke.log / mock-launch.log | 实际消息和三条 TF 链、16 个正常节点退出、Launch 退出 0；domain 74 |
| 6–8 | stress.log | 含真实 Timer/MapTile/StaticTfLoader 信号测试，十轮矩阵及连续/混合信号，共 238 passed；domain 75 |
| 9 | foreign-executor.log | 额外调用方 Executor 的 NO/ALL 两种处理器模式均正常；domain 76 |

压力检查命令：

```bash
AG_SHUTDOWN_STRESS_REPEATS=10 python3 -m pytest -vv -p no:cacheprovider \
  src/ag_system_tests/test/test_node_shutdown.py \
  -k 'signal_timing_matrix or repeated_signals'
```

压力日志中的 57 deselected 是此次未重复的其他生命周期测试，均已在完整套件执行。
没有跳过 SIGTERM，没有 xfail。真实故障用例的子进程按预期非零退出，父测试同时检查
指定异常仍可见且实体已释放；它们不是被吞掉的测试失败。

`lifecycle-summary.json` 来自完整 pytest 的 136 份及压力测试的 238 份逐进程记录。
其中正常信号退出 364 份，真实故障退出 10 份，剩余句柄全部为零。汇总不重复计入
colcon 测试中的同类记录。包含 21 个安装入口两种信号的逐项结果及源文件清单。
逐进程明细与 stderr 在当前环境 `/workspace/.air-ground-round2/verified-pytest/`
和 `/workspace/.air-ground-round2/verified-stress/` 保留；该环境路径不是远程仓库附件。

详见 `../../28_sigterm_lifecycle_round2.md`。未进行双机、硬件、其他 RMW 或其他 ROS
发行版验证。日志和摘要提供回归证据，不替代新的独立合并审查。
