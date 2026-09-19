import numpy as np
import torch

from cnn_model import CNNDetector
from data_utils import WindowScaler, resolve_path, sha256, validate_x


class Detector:
    def __init__(self, model_path="models/best_model.pt", scaler_path="data/scaler_params.npz", device="cpu", num_threads=1):
        self.device = torch.device(device)
        if self.device.type == "cpu":
            torch.set_num_threads(num_threads)
        checkpoint = torch.load(resolve_path(model_path), map_location="cpu", weights_only=True)
        if checkpoint["scaler_sha256"] != sha256(resolve_path(scaler_path)):
            raise ValueError("Scaler does not match the model checkpoint")
        self.model = CNNDetector(checkpoint["dropout"]).to(self.device)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        self.model.requires_grad_(False)
        self.scaler = WindowScaler(scaler_path)
        self.threshold = float(checkpoint["threshold"])
        self.metadata = {k: v for k, v in checkpoint.items() if k != "state_dict"}

    @torch.inference_mode()
    def predict_proba(self, x, *, input_space, batch_size=256):
        if input_space not in ["raw", "standardized"]:
            raise ValueError("input_space must be 'raw' or 'standardized'")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        x = validate_x(x)
        if input_space == "raw":
            x = self.scaler.transform(x)
        if len(x) == 0:
            return np.empty((0, 2), dtype=np.float32)
        self.model.eval()
        return np.concatenate([self.model(torch.from_numpy(x[i:i+batch_size]).to(self.device))
                               .softmax(1).cpu().numpy()
                               for i in range(0, len(x), batch_size)])

    def predict(self, x, *, input_space, batch_size=256):
        p = self.predict_proba(x, input_space=input_space, batch_size=batch_size)
        return (p[:, 1] >= self.threshold).astype(np.int64)
