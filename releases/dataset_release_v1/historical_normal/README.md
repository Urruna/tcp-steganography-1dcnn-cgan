# Historical Normal Data

This directory is **not** part of the current protocol_stego control group.

It contains two clearly separated historical sources.

## 1. `raw/docker_chain_smoke`

Early Docker chain normal traffic:

```text
Client → Proxy-A → Proxy-B → Server
```

Files:

- `proxy_a_events.csv`
- `proxy_b_events.csv`

Original files are preserved byte-for-byte.

The original CSV later also collected rows written by a different schema.
The early Docker session is therefore also provided as a normalized view:

```text
processed/early_docker_normal_events.csv
```

Early Docker session facts:

- time: 2026-07-29 14:02:06 (epoch timestamps in CSV)
- payload: `hello network` (13 bytes)
- Proxy-A events: 2 (forward + reverse)
- Proxy-B events: 2 (forward + reverse)
- no pcap
- no feature extraction in the original run

## 2. `raw/baseline_lenmix_v1`

Earlier normal-traffic baseline:

- 1 experiment/session
- 256 client events, all `passed`
- 512 Proxy-A events (256 forward + 256 reverse)
- 512 Proxy-B events (256 forward + 256 reverse)
- lengths: 64, 128, 256, 512, 1024 bytes cycling
- no modulation and no hidden payload
- no pcap

Per the project notes, this source came from an earlier Ubuntu 20.04 VMware
native multi-process experiment, not from the current protocol_stego Docker
control group.

The parsed summary is at:

```text
processed/baseline_lenmix_v1_summary.json
```
