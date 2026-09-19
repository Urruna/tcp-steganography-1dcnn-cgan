import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_utils import ROOT, WindowScaler, load_split, validate_x
from detector import Detector
from gan_interface import evaluate_windows
from metrics import calculate_metrics


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = Detector()
        cls.x, cls.y = load_split("data", "test")

    def test_raw_and_standardized_paths_agree(self):
        raw = self.detector.scaler.inverse_transform(self.x)
        a = self.detector.predict_proba(self.x, input_space="standardized")
        b = self.detector.predict_proba(raw, input_space="raw")
        np.testing.assert_allclose(a, b, atol=3e-6, rtol=1e-5)

    def test_batch_size_does_not_change_predictions(self):
        a = self.detector.predict_proba(self.x, input_space="standardized", batch_size=1)
        b = self.detector.predict_proba(self.x, input_space="standardized", batch_size=25)
        np.testing.assert_allclose(a, b, atol=3e-6, rtol=1e-5)
        np.testing.assert_allclose(a.sum(1), 1, atol=1e-6)

    def test_gan_interface_matches_detector(self):
        r = evaluate_windows(self.x, input_space="standardized", y=self.y, detector=self.detector)
        np.testing.assert_array_equal(r["labels"], self.detector.predict(self.x, input_space="standardized"))
        self.assertEqual(r["metrics"]["samples"], len(self.y))

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            validate_x(np.zeros((2, 128, 4)))
        bad = self.x[:1].copy()
        bad[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            validate_x(bad)
        with self.assertRaises(ValueError):
            self.detector.predict_proba(self.x, input_space="guess")

    def test_empty_batch_and_single_class_auc(self):
        p = self.detector.predict_proba(np.empty((0, 4, 128)), input_space="standardized")
        self.assertEqual(p.shape, (0, 2))
        self.assertIsNone(calculate_metrics(np.ones(2), np.array([0.7, 0.8]))["roc_auc"])

    def test_saved_result_matches_reloaded_model(self):
        import json
        expected = json.loads((ROOT / "results" / "cnn_metrics.json").read_text())["test"]
        p = self.detector.predict_proba(self.x, input_space="standardized")[:, 1]
        actual = calculate_metrics(self.y, p, self.detector.threshold)
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
