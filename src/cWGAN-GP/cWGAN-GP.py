"""Conditional WGAN-GP for generating stego length sequences.

Data format:
    real_train_X.npy : [N, 4, 128]  (channel 0=direction, 1=length,
                                     2=interval, 3=cumulative)
    real_train_y.npy : [N]          (0=Normal, 1=Stego)

Design:
    - Generator outputs [B, 128] continuous values in [0, 1].
    - Values are projected onto two non-overlapping length intervals
      (in normalized length space):
          v in [0, 0.5) -> bit 0 -> length in BIT0_RANGE
          v in [0.5, 1] -> bit 1 -> length in BIT1_RANGE
    - Critic operates on normalized length sequences [B, 128].
    - WGAN-GP training with gradient penalty.

Why this design:
    - Proxy can only control the length channel; other channels are
      determined by the underlying traffic.
    - Lower output dimension -> trainable with hundreds of windows.
    - Projection to two bands is simple and lossless for decoding.
    - Evaluation chain stays intact: cGAN -> proxy -> GAN-Stego -> 1D-CNN.

Scale:
    Designed for ~300-1000 training windows. If you have ~100 windows,
    reduce z_dim to 16 and lower lr to 2e-5. If you have >2000,
    you can increase z_dim to 64 and hidden sizes to 512.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.autograd import grad
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
# Length intervals in normalized length space.
# If your data is per-channel standardized, length channel has mean 0, std 1.
# Two non-overlapping bands, centered roughly at -1 and +1.
BIT0_RANGE = (-1.5, -0.5)   # bit 0 -> lower length band
BIT1_RANGE = ( 0.5,  1.5)   # bit 1 -> upper length band

# If your data is NOT standardized and length channel is in raw bytes,
# change these to (780, 820) and (1180, 1220) instead.


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------
class Generator(nn.Module):
    """Conditional generator. Output: [B, 128] in [0, 1].

    Sized for ~300-1000 training windows. Parameter count ~180K.
    """

    def __init__(self, z_dim: int = 32, num_classes: int = 2):
        super().__init__()
        self.z_dim = z_dim
        self.label_embedding = nn.Embedding(num_classes, 16)
        self.net = nn.Sequential(
            nn.Linear(z_dim + 16, 256),
            nn.ReLU(True),
            nn.Linear(256, 256),
            nn.ReLU(True),
            nn.Linear(256, 128),
            nn.Sigmoid(),
        )

    def forward(self, noise: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        cond = self.label_embedding(labels)
        return self.net(torch.cat([noise, cond], dim=1))


class Critic(nn.Module):
    """Critic on length sequences. Input: [B, 128] lengths + labels.

    Parameter count ~100K.
    """

    def __init__(self, num_classes: int = 2):
        super().__init__()
        self.label_embedding = nn.Embedding(num_classes, 16)
        self.net = nn.Sequential(
            nn.Linear(128 + 16, 256),
            nn.LeakyReLU(0.2, True),
            nn.Linear(256, 256),
            nn.LeakyReLU(0.2, True),
            nn.Linear(256, 1),
        )

    def forward(self, lengths: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        cond = self.label_embedding(labels)
        return self.net(torch.cat([lengths, cond], dim=1))


# ----------------------------------------------------------------------
# Projection: [0, 1] -> two non-overlapping normalized length bands
# ----------------------------------------------------------------------
def project(v: torch.Tensor) -> torch.Tensor:
    """v: [B, 128] in [0, 1] -> lengths: [B, 128] in two bands."""
    low_mask = v < 0.5
    b0_low, b0_high = BIT0_RANGE
    b1_low, b1_high = BIT1_RANGE
    # v in [0, 0.5) -> [b0_low, b0_high)
    len_low = b0_low + v * (b0_high - b0_low) / 0.5
    # v in [0.5, 1] -> [b1_low, b1_high]
    len_high = b1_low + (v - 0.5) * (b1_high - b1_low) / 0.5
    return torch.where(low_mask, len_low, len_high)


# ----------------------------------------------------------------------
# Gradient penalty
# ----------------------------------------------------------------------
def compute_gradient_penalty(
    critic: Critic,
    real: torch.Tensor,
    fake: torch.Tensor,
    labels: torch.Tensor,
) -> torch.Tensor:
    alpha = torch.rand(real.size(0), 1, device=real.device)
    interpolated = (alpha * real + (1 - alpha) * fake).requires_grad_(True)
    scores = critic(interpolated, labels)
    gradients = grad(
        outputs=scores,
        inputs=interpolated,
        grad_outputs=torch.ones_like(scores),
        create_graph=True,
        retain_graph=True,
    )[0]
    gradients = gradients.flatten(1)
    return (gradients.norm(2, dim=1).sub(1).pow(2)).mean()


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------
def load_length_channel(data_dir: Path) -> tuple[torch.Tensor, torch.Tensor]:
    """Load [N, 4, 128] windows and return only the length channel [N, 128]."""
    X = np.load(data_dir / "real_train_X.npy")
    y = np.load(data_dir / "real_train_y.npy")
    if X.shape[1:] != (4, 128):
        raise ValueError(
            f"Expected [N, 4, 128], got {X.shape}. "
            "This cWGAN-GP expects 4-channel 128-length windows."
        )
    if len(X) != len(y):
        raise ValueError(f"X and y length mismatch: {len(X)} vs {len(y)}")
    if not set(np.unique(y)).issubset({0, 1}):
        raise ValueError(f"Labels must be 0/1, got {np.unique(y)}")

    lengths = X[:, 1, :].astype(np.float32)  # channel 1 = block length
    return torch.from_numpy(lengths), torch.from_numpy(y.astype(np.int64))


# ----------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------
def train(
    data_dir: Path,
    output_path: Path,
    epochs: int = 500,
    batch_size: int = 32,
    z_dim: int = 32,
    critic_steps: int = 2,
    learning_rate: float = 1e-4,
    lambda_gp: float = 10.0,
    seed: int = 42,
) -> tuple[Generator, dict]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    lengths, labels = load_length_channel(data_dir)
    print(f"Loaded {len(lengths)} windows | labels: {torch.bincount(labels).tolist()}")
    print(
        f"Length channel stats: min={lengths.min():.4f}, max={lengths.max():.4f}, "
        f"mean={lengths.mean():.4f}, std={lengths.std():.4f}"
    )

    dataset = TensorDataset(lengths, labels)
    counts = torch.bincount(labels, minlength=2).float()
    weights = 1.0 / counts.clamp_min(1)
    sampler = WeightedRandomSampler(weights[labels], len(labels), replacement=True)
    loader = DataLoader(dataset, batch_size=batch_size, sampler=sampler, drop_last=True)

    generator = Generator(z_dim=z_dim).to(device)
    critic = Critic().to(device)
    g_optimizer = torch.optim.Adam(generator.parameters(), lr=learning_rate, betas=(0.0, 0.9))
    d_optimizer = torch.optim.Adam(critic.parameters(), lr=learning_rate, betas=(0.0, 0.9))

    g_params = sum(p.numel() for p in generator.parameters())
    c_params = sum(p.numel() for p in critic.parameters())
    print(f"Generator params: {g_params:,} | Critic params: {c_params:,}")

    history = {"critic": [], "generator": []}

    for epoch in range(1, epochs + 1):
        for real_len, real_lab in loader:
            real_len = real_len.to(device)
            real_lab = real_lab.to(device)
            bsz = real_len.size(0)

            # ----- Critic update -----
            for _ in range(critic_steps):
                noise = torch.randn(bsz, z_dim, device=device)
                with torch.no_grad():
                    fake_v = generator(noise, real_lab)
                    fake_len = project(fake_v)

                d_loss = (
                    critic(fake_len, real_lab).mean()
                    - critic(real_len, real_lab).mean()
                    + lambda_gp * compute_gradient_penalty(
                        critic, real_len, fake_len, real_lab
                    )
                )
                d_optimizer.zero_grad(set_to_none=True)
                d_loss.backward()
                d_optimizer.step()

            # ----- Generator update -----
            noise = torch.randn(bsz, z_dim, device=device)
            fake_v = generator(noise, real_lab)
            fake_len = project(fake_v)
            g_loss = -critic(fake_len, real_lab).mean()

            g_optimizer.zero_grad(set_to_none=True)
            g_loss.backward()
            g_optimizer.step()

            history["critic"].append(float(d_loss.detach().cpu()))
            history["generator"].append(float(g_loss.detach().cpu()))

        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(
                f"Epoch {epoch:4d}/{epochs} | "
                f"Critic: {history['critic'][-1]:.4f} | "
                f"Generator: {history['generator'][-1]:.4f}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "generator_state_dict": generator.state_dict(),
            "z_dim": z_dim,
            "num_classes": 2,
            "length_shape": [128],
            "bit0_range": list(BIT0_RANGE),
            "bit1_range": list(BIT1_RANGE),
            "history": history,
        },
        output_path,
    )
    print(f"Saved checkpoint to {output_path}")
    return generator, history


# ----------------------------------------------------------------------
# Generation
# ----------------------------------------------------------------------
def generate(
    checkpoint: Path,
    output_dir: Path,
    count_per_class: int = 300,
    seed: int = 42,
) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(checkpoint, map_location=device)
    generator = Generator(z_dim=int(ckpt["z_dim"])).to(device)
    generator.load_state_dict(ckpt["generator_state_dict"])
    generator.eval()

    rng = torch.Generator().manual_seed(seed)
    all_lengths, all_labels = [], []
    with torch.no_grad():
        for label in range(2):
            labels = torch.full((count_per_class,), label, device=device, dtype=torch.long)
            noise = torch.randn(count_per_class, generator.z_dim, generator=rng).to(device)
            v = generator(noise, labels)
            lengths = project(v)
            all_lengths.append(lengths.cpu().numpy())
            all_labels.append(labels.cpu().numpy())

    output_dir.mkdir(parents=True, exist_ok=True)
    lengths_arr = np.concatenate(all_lengths).astype(np.float32)
    labels_arr = np.concatenate(all_labels).astype(np.int64)

    np.save(output_dir / "synthetic_lengths.npy", lengths_arr)
    np.save(output_dir / "synthetic_y.npy", labels_arr)

    print(f"Saved {len(lengths_arr)} length sequences to {output_dir}")
    print(f"  synthetic_lengths.npy : {lengths_arr.shape}")
    print(f"  synthetic_y.npy       : {labels_arr.shape}")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=project_dir / "datasets" / "protocol_stego",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=project_dir / "models" / "cgan_protocol.pth",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "models" / "generated_protocol",
    )
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--count-per-class", type=int, default=300)
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()

    if args.generate_only:
        generate(args.checkpoint, args.output_dir, args.count_per_class)
    else:
        train(
            args.data_dir,
            args.checkpoint,
            epochs=args.epochs,
            batch_size=args.batch_size,
        )


if __name__ == "__main__":
    main()