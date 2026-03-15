# 20 Stage2 Run Initialization

这份文档只讲如何先初始化一轮 stage2 run，再开始执行。

## 1. `run_id` 是什么

`run_id` 就是这一轮 stage2 测试的名字。

推荐让它能看出：

- 日期
- 轮次
- 模式

例如：

```bash
20260315_run01
20260315_default_smoke
20260315_discovery_smoke
```

如果你不手动传 `--run-id`，脚本会自动用时间戳。

## 2. 先初始化一轮 default 模式 run

```bash
./scripts/init_stage2_run.sh \
  --run-id 20260315_default_run01 \
  --mode default \
  --machine-a-env env/machine_a_default.env \
  --machine-b-env env/machine_b_default.env
```

执行后脚本会打印：

- 本次 run 根目录
- machine A 建议命令
- machine B 建议命令
- acceptance 建议命令
- bundle 建议命令

同时会创建：

```bash
artifacts/stage2_runs/20260315_default_run01/
```

## 3. 如果要初始化 discovery 模式 run

```bash
./scripts/init_stage2_run.sh \
  --run-id 20260315_discovery_run01 \
  --mode discovery \
  --machine-a-env env/machine_a_discovery.env \
  --machine-b-env env/machine_b_discovery.env \
  --discovery-env env/discovery_server.env
```

这里的 `--mode` 决定推荐命令会走哪一套 logged wrapper：

- `default`
  对应默认发现 smoke
- `discovery`
  对应 Discovery Server smoke

## 4. 目录结构分别做什么

初始化后至少会有这些目录：

- `machine_a/`
  放 machine A 的日志和证据
- `machine_b/`
  放 machine B 的日志和证据
- `acceptance/`
  放验收检查输出
- `bundle/`
  放 bundle 汇总结果
- `notes/`
  放手工备注、截图文件名、验收文档副本

## 5. 生成后先看哪两个文件

先看：

```bash
cat artifacts/stage2_runs/<run_id>/README.txt
cat artifacts/stage2_runs/<run_id>/command_plan.txt
```

其中：

- `README.txt`
  说明这轮 run 的模式、目录和 env 文件建议
- `command_plan.txt`
  给出可以直接复制的 machine A / machine B / acceptance / bundle 命令

## 6. 初始化后怎么继续

先按 `command_plan.txt` 里的顺序执行：

1. machine A logged 命令
2. machine B logged 命令
3. 两侧 evidence 采集命令
4. acceptance 命令
5. bundle 创建命令
6. bundle 校验命令

## 7. 如果 env 文件还没准备好

脚本不会因为 env 文件不存在而直接崩掉。

它会给出 warning，并继续把 run 目录和命令计划建好。你需要在真正执行前补齐 env 文件。

## 8. 这一步能证明什么

初始化 run 目录能证明：

- 本轮 stage2 的目录结构已经准备好
- 后续命令已经被组织成一个清单

它不能证明：

- 真实双机已经联通
- Discovery Server 已经成功运行
- 真实 stage2 已经通过
