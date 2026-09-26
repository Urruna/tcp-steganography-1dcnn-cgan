# PROJECT STATUS

Status values: `Completed` / `Partial` / `Design` / `Not Implemented` / `Unknown`.

| Module | Status | Location | Description |
| --- | --- | --- | --- |
| Network | Completed | `src/tcp_lab/`, `src/normal_file_transfer/`, `src/protocol_stego/examples/` | Client → Proxy-A → Proxy-B → Server chains exist and were executed |
| Docker | Completed | `src/tcp_lab/docker-compose.yml`, `src/normal_file_transfer/compose.yaml`, `src/protocol_stego/compose.yaml` | Docker/Compose environments build and run; protocol_stego is a single test container, not a 4-container chain |
| Encryption | Completed | `src/crypto/` | AES-256-GCM with keygen, PBKDF2 derivation, nonce, tag, fixed 30 B overhead, self-test passed |
| Protocol | Completed | `src/newtry97/framing.py`, `src/protocol_stego/core/framing.py`, `core/reassembly.py` | Preamble/Version/Frame ID/Length/Payload/CRC implemented; tests pass |
| Steganography | Completed | `src/protocol_stego/core/modulation.py`, `src/protocol_stego/proxy/` | 800/1200 application-layer write-length modulation implemented and validated |
| Dataset | Partial | `datasets/protocol_stego/` | After the 2026-09-26 scale-up: 233 Normal + 233 Stego sessions, all successful, 1398 windows (699/699); session-level split 374/46/46 sessions = 1122/138/138 windows; BER = FER = CRC failures = 0. Normal is still a fixed 1024 B write, so detection remains an 800/1200-signature test. See `docs/experiments/dataset-scaleup-20260926.md` |
| 1D-CNN | Partial | `src/1dcnn/` | CNN code, trained checkpoint, interface, tests and result files exist; metrics use a separate 168-window dataset with no session index, so session isolation and cross-session generalization are not verified |
| cGAN | Partial | `src/cWGAN-GP/` | Conditional WGAN-GP implemented (generator outputs the length channel only, projected onto two non-overlapping length bands); training is blocked by data volume (114 train windows vs the ≥1000 the module requires), so there is no checkpoint, no synthetic data and no GAN-Stego result. See `docs/experiments/cwgan-results.md` |

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
| cWGAN-GP data interface | Partial | `src/cWGAN-GP/cWGAN-GP.py` expects `real_train_X.npy` / `real_train_y.npy` under `datasets/protocol_stego/`; only `processed/windows.npz` is present, and the length band constants assume a standardized length channel |
| Failed stego sessions | Recorded | 8 sessions failed with `length_out_of_range` during the scale-up, were moved to the VM's `protocol_stego/raw_failed/stego/` (not deleted, not part of the dataset) and were replaced |
| Released dataset package | Partial | `releases/dataset_release_v1/` still describes the previous 46-session snapshot and was not regenerated after the scale-up |
