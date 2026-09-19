import torch
from torch import nn


class CNNDetector(nn.Module):
    def __init__(self, dropout=0.3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(4, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.classifier = nn.Sequential(nn.Dropout(dropout), nn.Linear(64, 2))

    def forward(self, x):
        if x.ndim != 3 or tuple(x.shape[1:]) != (4, 128):
            raise ValueError(f"Expected [N,4,128], got {tuple(x.shape)}")
        return self.classifier(self.features(x).squeeze(-1))
