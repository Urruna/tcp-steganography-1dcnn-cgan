# Network Topology

## Base Docker TCP Chain

Location: `src/tcp_lab/`

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

| Container | Listens | Upstream | Role |
| --- | ---: | --- | --- |
| `client` | – | `proxy_a:9001` | sends `hello network` |
| `proxy_a` | 9001 | `proxy_b:9002` | transparent TCP relay |
| `proxy_b` | 9002 | `server:9003` | transparent TCP relay |
| `server` | 9003 | – | echo server |

Networks (all `internal: true`):

```text
client_net
backbone_net
server_net
```

Client behavior: `src/tcp_lab/client.py`
Proxy behavior: `src/tcp_lab/proxy.py`
Server behavior: `src/tcp_lab/echo_server.py`

## Normal File-Transfer Chain

Location: `src/normal_file_transfer/`

Same port convention:

```text
client → proxy_a:9001 → proxy_b:9002 → server:9003
```

Server provides:

```text
report_small.txt   64 KiB
report_medium.txt  256 KiB
report_large.bin   1 MiB
```

Client performs 8 downloads and validates SHA-256.

## protocol_stego Experiment

Location: `src/protocol_stego/`

The compose file defines one service:

```text
tests
```

Four-node flow is simulated by threads:

```text
client → proxy_a:9101 → proxy_b:9102 → server:9103
```

Code:

- `examples/demo_secret_transfer.py`
- `scripts/session_runner.py`

It is **not** a four-container Docker network in the current implementation.

## newtry97 Container Demo

Location: `src/newtry97/`

```text
newtry97-917: client → proxy_a → proxy_b → server
```

This is a separate v0.2 protocol + write-splitting experiment, not the
800/1200 baseline strategy.
