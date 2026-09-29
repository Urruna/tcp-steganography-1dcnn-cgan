# tcp_lab

最早的 Docker 四容器 TCP echo 链。

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

- `client.py`：发送 `hello network`
- `proxy.py`：透明 TCP 中继，并把事件记录成 CSV
- `echo_server.py`：字节回显服务器
- `batch_client.py`：更早的批量流量生成器
- `docker-compose.yml`：四服务 Docker 链

运行：

```bash
docker compose up
```
