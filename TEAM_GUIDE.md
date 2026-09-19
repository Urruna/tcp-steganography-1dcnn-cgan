# TEAM GUIDE

## Get the project

```bash
git clone <repository-url>
cd <repository>
```

Read first:

1. `README.md`
2. `PROJECT_STATUS.md`
3. `docs/architecture/network-topology.md`
4. `TEAM_GUIDE.md`

## Docker requirements

- Docker 26.x
- Docker Compose v2
- Python 3.11 containers
- Network access for image pulls (registry mirror may be required)

## Run the base chain

```bash
cd src/tcp_lab
docker compose up
```

Expected:

```text
[client] received: hello network
[client] PASS: returned payload matches sent payload
```

## Run the normal file-transfer chain

```bash
cd src/normal_file_transfer
docker compose up --abort-on-container-exit --exit-code-from client
```

## Run protocol_stego tests

```bash
cd src/protocol_stego
docker compose build
docker compose run --rm tests python -m unittest discover -s tests -v
```

Expected: 20 tests OK.

## Run the end-to-end demo

```bash
cd src/protocol_stego
docker compose run --rm tests python examples/demo_secret_transfer.py
```

Expected: `PASS=True`, BER=0, CRC failures=0.

## Where things are

| Topic | Location |
| --- | --- |
| Base Docker chain | `src/tcp_lab/` |
| Normal file-transfer chain | `src/normal_file_transfer/` |
| AES-256-GCM | `src/crypto/crypto.py` |
| Frame protocol | `src/protocol_stego/core/framing.py`, `src/newtry97/framing.py` |
| Basic stego | `src/protocol_stego/core/modulation.py`, `src/protocol_stego/proxy/` |
| Current dataset | `src/protocol_stego/dataset/` |
| Released dataset | `releases/dataset_release_v1/` |
| Experiment reports | `docs/experiments/` |
| Planning documents | `docs/planning/` |

## Do not modify without explicit agreement

- AES-256-GCM implementation;
- frame field layout and CRC definition;
- Docker network topology and port mapping;
- 800/1200 baseline modulation;
- raw experiment data (`dataset/raw/**`, historical CSV files);
- released dataset contents.

If a bug is found:

1. write down the exact symptom and evidence;
2. do not silently rewrite results;
3. create a separate branch/experiment;
4. record the change in `CHANGELOG.md`.

## Where to add new work

- New experiment report: `docs/experiments/`
- New dataset release: `releases/`
- New code experiment: a new subdirectory under `src/`
- New analysis script: `src/protocol_stego/scripts/`
- New notebook or temporary exploration: not committed; use `scratch/`
  (ignored by Git)

## How to submit new experiment results

1. Keep raw logs unchanged.
2. Add a short Markdown report with:
   - purpose;
   - command;
   - environment;
   - sample count;
   - metrics;
   - known limitations.
3. Put large `.npz` / `.npy` / `.zip` files in Git LFS or a Release.
4. Never commit keys, tokens, passwords, or private credentials.
