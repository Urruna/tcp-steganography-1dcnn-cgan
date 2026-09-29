# 网络拓扑

## 基础 Docker TCP 链

位置：`src/tcp_lab/`

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

| 容器 | 监听端口 | 上游 | 角色 |
| --- | ---: | --- | --- |
| `client` | – | `proxy_a:9001` | 发送 `hello network` |
| `proxy_a` | 9001 | `proxy_b:9002` | 透明 TCP 中继 |
| `proxy_b` | 9002 | `server:9003` | 透明 TCP 中继 |
| `server` | 9003 | – | echo 服务器 |

网络（均为 `internal: true`）：

```text
client_net
backbone_net
server_net
```

客户端行为：`src/tcp_lab/client.py`
代理行为：`src/tcp_lab/proxy.py`
服务端行为：`src/tcp_lab/echo_server.py`

## 正常文件下载链

位置：`src/normal_file_transfer/`

端口约定与基础链相同：

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

服务端提供：

```text
report_small.txt   64 KiB
report_medium.txt  256 KiB
report_large.bin   1 MiB
```

客户端执行 8 次下载并用 SHA-256 校验。

## protocol_stego 实验

位置：`src/protocol_stego/`

compose 文件只定义了一个服务：

```text
tests
```

四节点流程由线程在进程内模拟：

```text
client → proxy_a:9101 → proxy_b:9102 → server:9103
```

相关代码：

- `examples/demo_secret_transfer.py`
- `scripts/session_runner.py`

在当前实现中，它**不是**四容器 Docker 网络。

## newtry97 容器演示

位置：`src/newtry97/`

```text
newtry97-917: client → proxy_a → proxy_b → server
```

这是另一条独立的 v0.2 协议 + 写拆分实验，不是 800/1200 基线策略。
