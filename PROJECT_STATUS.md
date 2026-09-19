# PROJECT STATUS

Status values: `Completed` / `Partial` / `Design` / `Not Implemented` / `Unknown`.

| Module | Status | Location | Description |
| --- | --- | --- | --- |
| Network | Completed | `src/tcp_lab/`, `src/normal_file_transfer/`, `src/protocol_stego/examples/` | Client → Proxy-A → Proxy-B → Server chains exist and were executed |
| Docker | Completed | `src/tcp_lab/docker-compose.yml`, `src/normal_file_transfer/compose.yaml`, `src/protocol_stego/compose.yaml` | Docker/Compose environments build and run; protocol_stego is a single test container, not a 4-container chain |
| Encryption | Completed | `src/crypto/` | AES-256-GCM with keygen, PBKDF2 derivation, nonce, tag, fixed 30 B overhead, self-test passed |
| Protocol | Completed | `src/newtry97/framing.py`, `src/protocol_stego/core/framing.py`, `core/reassembly.py` | Preamble/Version/Frame ID/Length/Payload/CRC implemented; tests pass |
| Steganography | Completed | `src/protocol_stego/core/modulation.py`, `src/protocol_stego/proxy/` | 800/1200 application-layer write-length modulation implemented and validated |
| Dataset | Partial | `src/protocol_stego/dataset/`, `datasets/`, `releases/dataset_release_v1/` | 23 Normal + 23 Stego sessions, 138 windows; recommended 50/class not reached; Normal diversity limited |
| 1D-CNN | Not Implemented | none | No CNN model code, training script, or weights |
| cGAN | Design | `docs/planning/new_727.md` | Only design discussed; no GAN code, no GAN-Stego data |

Additional status:

| Item | Status | Evidence |
| --- | --- | --- |
| Rule-based baseline | Completed | `docs/experiments/baseline-analysis.md` |
| Logistic Regression baseline | Completed | same report |
| Historical Docker Normal | Partial | small early Docker smoke data, 2 proxy sessions / 4 events |
| `normal_v1` file-transfer dataset | Completed (code+data) | `datasets/normal_v1/`, 8 downloads, 3,082,890 bytes |
| pcap capture | Not Implemented | no `.pcap` files found |
| FEC / retransmission | Not Implemented | not present in protocol code |
| GAN-Stego data | Not Implemented | no generator and no dataset |
