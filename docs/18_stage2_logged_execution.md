# 18 Stage2 Logged Execution

这份文档只讲如何把 stage2 执行过程自动落盘到 `artifacts/`。

## 1. 先决定这次运行的 artifact 根目录

先在机器 A 和机器 B 约定同一个 run 目录名，例如：

```bash
RUN_ROOT="artifacts/stage2_runs/20260315_run01"
```

后面的命令都把日志落到这个目录下面。

## 2. 机器 A 运行默认发现 server 侧并自动落盘

```bash
./scripts/dual_machine_server_logged.sh \
  --env-file env/machine_a_default.env \
  --artifact-dir "${RUN_ROOT}/machine_a"
```

默认会生成：

- `${RUN_ROOT}/machine_a/server_stdout.log`
- `${RUN_ROOT}/machine_a/command.txt`
- `${RUN_ROOT}/machine_a/exit_code.txt`

## 3. 机器 B 运行默认发现 client 侧并自动落盘

```bash
./scripts/dual_machine_client_logged.sh \
  --env-file env/machine_b_default.env \
  --artifact-dir "${RUN_ROOT}/machine_b"
```

默认会生成：

- `${RUN_ROOT}/machine_b/client_stdout.log`
- `${RUN_ROOT}/machine_b/command.txt`
- `${RUN_ROOT}/machine_b/exit_code.txt`

## 4. 如果切到 Discovery Server 模式

机器 A：

```bash
./scripts/dual_machine_server_logged.sh \
  --mode discovery \
  --env-file env/machine_a_discovery.env \
  --artifact-dir "${RUN_ROOT}/machine_a"
```

机器 B：

```bash
./scripts/dual_machine_client_logged.sh \
  --mode discovery \
  --env-file env/machine_b_discovery.env \
  --artifact-dir "${RUN_ROOT}/machine_b"
```

这两个脚本本质上还是包装现有入口：

- `dual_machine_server_smoke.sh` / `run_server_discovery.sh`
- `dual_machine_client_smoke.sh` / `run_client_discovery.sh`

不会重写其核心逻辑。

## 5. 运行验收检查并自动落盘

在能观察全局图的一侧执行：

```bash
./scripts/stage2_acceptance_logged.sh \
  --env-file env/machine_a_default.env \
  --artifact-dir "${RUN_ROOT}/acceptance"
```

如果当前是在 Discovery Server 模式，也可以把 env 文件换成：

```bash
env/machine_a_discovery.env
```

默认会生成：

- `${RUN_ROOT}/acceptance/stage2_acceptance.log`
- `${RUN_ROOT}/acceptance/command.txt`
- `${RUN_ROOT}/acceptance/exit_code.txt`

## 6. 如果你还想采集结构化证据

日志落盘和证据采集可以同时使用：

```bash
./scripts/collect_stage2_evidence.sh \
  --env-file env/machine_a_default.env \
  --output-dir "${RUN_ROOT}/machine_a/evidence" \
  --collect-target-once \
  --collect-odom-hz \
  --collect-map-bw
```

机器 B 同理，只需要把 env 文件和输出目录换掉。

## 7. 失败后先看哪些日志

建议按这个顺序看：

1. `${RUN_ROOT}/machine_a/exit_code.txt`
2. `${RUN_ROOT}/machine_a/command.txt`
3. `${RUN_ROOT}/machine_a/server_stdout.log`
4. `${RUN_ROOT}/machine_b/exit_code.txt`
5. `${RUN_ROOT}/machine_b/command.txt`
6. `${RUN_ROOT}/machine_b/client_stdout.log`
7. `${RUN_ROOT}/acceptance/stage2_acceptance.log`

## 8. 这些日志能说明什么

这些日志能说明：

- 实际运行了什么命令
- 命令输出是什么
- 退出码是多少

这些日志不能单独说明：

- 真正完成了真实双机验证
- Discovery Server 一定在真实机器上成功工作
- 真实网络质量一定满足要求

所以日志要和 `collect_stage2_evidence.sh` 的输出、rosbag 路径、验收文档一起保存。
