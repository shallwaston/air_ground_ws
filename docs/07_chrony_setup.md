# 07 Chrony Setup

## 角色划分

建议固定如下：

- UGV 作为 Chrony server
- UAV 和其他 ground 计算节点作为 Chrony client

这样更符合“地面端集中管理时间”的常见工程模式。

## 示例配置文件

- `config/chrony/chrony_server.conf`
- `config/chrony/chrony_client.conf`

这些都是示例配置，不是最终实机参数。

必须替换：

- 示例网段
- 示例 IP
- 任何与你真实网络不匹配的值

## 先检查是否安装了 chrony

推荐先执行：

```bash
which chronyc
./scripts/check_chrony.sh
```

如果 `which chronyc` 没有输出，说明本机还没有 Chrony 命令行工具。

此时的保守处理方式是：

- 先安装 `chrony`
- 或者先记录“当前未启用时钟同步”，后续双机测试时再补做

不要在没有 `chronyc` 的情况下假设时钟已经同步。

## Server 侧

将 server 配置部署到 UGV 后，重启 Chrony。

然后检查：

```bash
chronyc tracking
chronyc sources
```

也可以直接执行：

```bash
./scripts/check_chrony.sh
```

## Client 侧

将 client 配置部署到 UAV 或其他从节点后，先把配置中的示例 IP 改成真实 UGV IP，再重启 Chrony。

然后检查：

```bash
chronyc tracking
chronyc sources
```

也可以直接执行：

```bash
./scripts/check_chrony.sh
```

## 为什么这个 MVP 也需要时间同步

虽然现在是 mock 系统，但消息里已经开始使用：

- `source_stamp`
- 延迟统计
- rosbag 回放比较

如果双机时钟差太大，你会看到：

- 延迟结果不可信
- 时间排序混乱
- 弱网测试结论偏差

所以 Chrony 应该在 MVP 阶段就先纳入流程。
