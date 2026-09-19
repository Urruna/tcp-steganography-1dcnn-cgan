# tcp_lab

Original Docker 4-container TCP echo chain.

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

- `client.py`: sends `hello network`
- `proxy.py`: transparent TCP relay with CSV event logging
- `echo_server.py`: byte echo server
- `batch_client.py`: earlier batch traffic generator
- `docker-compose.yml`: 4-service Docker chain

Run:

```bash
docker compose up
```
