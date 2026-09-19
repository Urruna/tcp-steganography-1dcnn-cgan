# DATASET CARD

## Dataset A: Historical Docker Normal Dataset

- Name: `historical_normal/raw/docker_chain_smoke`
- Source: `/home/urruna/docker/tcp-lab/logs/proxy_a_events.csv` and
  `proxy_b_events.csv`
- Purpose: early proof that the Docker TCP chain
  `Client → Proxy-A → Proxy-B → Server` could carry normal traffic.
- Environment: Ubuntu6.21 VM + Docker Compose TCP chain
- Traffic type: normal application-layer TCP traffic, no modulation
- Collection method: early Docker chain smoke test; payload `hello network`
  (13 bytes)
- Time period: 2026-07-29 14:02:06 (recorded epoch timestamp)
- Sessions: 2 proxy-side sessions (one Proxy-A session, one Proxy-B session)
- Events: 4 application-layer events total (2 forward/reverse pairs)
- Available fields: timestamp, proxy_name, session_id, direction,
  event_index, byte_length, inter_event_gap_ms
- Known limitations:
  - Very small early smoke-test dataset;
  - No client/server CSV log from that exact early run;
  - No pcap;
  - Original CSV later received rows written by a different schema; the
    early rows are preserved in `raw/` and a normalized view is provided in
    `processed/early_docker_normal_events.csv`.

### Supplementary: earlier `baseline_lenmix_v1`

- Location: `historical_normal/raw/baseline_lenmix_v1`
- Source: earlier TCP-lab baseline experiment logs.
- Environment: documented as Ubuntu 20.04 VMware native multi-process
  experiment, not the current protocol_stego Docker control group.
- Sessions: 1 experiment/session
- Events: 256 client events; 512 Proxy-A events; 512 Proxy-B events
- Lengths: 64, 128, 256, 512, 1024 bytes cycling
- Client status: 256 / 256 passed
- No modulation, no secret payload
- No pcap

This supplementary source is clearly separated from Dataset A; it must not be
silently merged with the current protocol_stego data.

## Dataset B-Normal: Current Protocol-Stego Normal

- Name: `protocol_stego/raw/normal`
- Source: current protocol_stego experiment, `run_experiment.py --mode normal`
- Purpose: current experimental control group for the 800/1200 modulation
  detector experiment
- Environment: protocol_stego Docker-like process chain
  `Client → Proxy-A → Proxy-B → Server`
- Traffic type: normal application-layer forwarding, **no** 800/1200
  modulation
- Collection method: 1024-byte normal cover writes; same session length and
  data-scale targets as Stego
- Sessions: 23
- Events: 10258
- Total bytes: 10,488,000
- Duration mean: 9.3986 s
- Available fields: timestamp, session_id, direction, observed_length,
  actual_write_length, inter_arrival_time, cumulative_bytes
- Known limitations:
  - Length is mostly constant 1024 B;
  - `direction` is currently constant +1;
  - Normal business variety is still limited.

## Dataset B-Stego: Current Protocol-Stego

- Name: `protocol_stego/raw/stego`
- Source: current protocol_stego experiment with 800/1200 modulation
- Purpose: current experimental group for baseline modulation detection
- Traffic type: normal cover traffic carrying a secret bitstream through
  application-layer write-length modulation
- Collection method:
  - bit 0 → target 800 bytes
  - bit 1 → target 1200 bytes
  - measurement is application-layer write/recv length, not TCP packet length
- Sessions: 23
- Events: 10488
- Total bytes: 10,324,000
- Duration mean: 9.4216 s
- Fields:
  - `target_length`
  - `actual_write_length`
  - `observed_length`
  - `bit`
  - `recovered_bit`
  - `frame_id`
  - `crc_status`
- Validation:
  - actual == target ratio = 1.0
  - actual == observed ratio = 1.0 (in this lab run)
  - BER = 0.0
  - frame error rate = 0.0
  - CRC failure rate = 0.0
- Known limitations:
  - The detector task is dominated by the explicit 800/1200 signature;
  - `direction` is currently constant +1;
  - This does not represent general steganography detection.
