# 数据生成

## 当前 protocol_stego 管线

注意：入口必须用模块方式 `python -m` 运行，直接写 `python scripts/xxx.py`
会因 `sys.path` 不含项目根目录而报 `ModuleNotFoundError`。

```bash
cd src/protocol_stego
docker compose build

docker compose run --rm tests python -m scripts.run_experiment \
  --mode both --normal 20 --stego 20 \
  --seed 42 --secret-size 16 --block-gap-ms 20 --window-size 128

docker compose run --rm tests python -m scripts.dataset_builder --window-size 128
docker compose run --rm tests python -m scripts.split_dataset \
  --val-ratio 0.1 --test-ratio 0.1 --seed 42
docker compose run --rm tests python -m scripts.dataset_stats
docker compose run --rm tests python -m scripts.data_quality_report
docker compose run --rm tests python -m scripts.baseline_analysis
```

## Session 生成

`scripts/session_runner.py`：

1. 为 Stego 生成确定性的秘密数据；
2. 用 AES-256-GCM 加密；
3. 把密文切成多个帧；
4. 帧编码并转换为比特流；
5. Proxy-A 写入 800/1200 字节的数据块；
6. Proxy-B 恢复比特、解码帧、重组并解密；
7. 写出原始 JSONL 与 metadata。

Normal session 跳过调制，直接使用正常的 1024 字节分块。

## 数据集构建

`scripts/dataset_builder.py`：

- 读取 `receiver.jsonl`；
- 使用 `observed_length` 作为 `length` 特征；
- 每个 session 切成互不重叠的 128 事件窗口；
- 绝不跨 session 边界；
- 写出 `windows.npz`、`index.jsonl`、`build_summary.json`。

## 划分

`scripts/split_dataset.py`：

- 按 `session_id` 划分，而不是按窗口划分；
- 默认比例 80/10/10；
- 检查是否重叠；
- 写出 train/val/test 的 npz 与索引文件。

## 质量检查与基线

- `scripts/data_quality_report.py` → `docs/experiments/data-quality-report.md`；
- `scripts/baseline_analysis.py` → `docs/experiments/baseline-analysis.md`。

## 历史数据

历史 Docker Normal 与 `baseline_lenmix_v1` 由更早的实验产生，以 CSV 形式
保存在 `datasets/historical/` 下。

它们不会由当前 protocol_stego 管线重新生成。
