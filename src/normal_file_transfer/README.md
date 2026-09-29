# normal_file_transfer

用于采集正常流量的 Docker 文件传输链。

```text
client → proxy_a → proxy_b → server
```

服务端提供：

- `report_small.txt` 64 KiB
- `report_medium.txt` 256 KiB
- `report_large.bin` 1 MiB

客户端执行 8 次下载并用 SHA-256 校验。

生成的数据副本归档在：

```text
datasets/normal_v1/
```

`normal_proxy.py` 是当前 compose 文件使用的多线程代理；
`proxy.py` 是更早的 asyncio 版本，作为历史参考保留。
