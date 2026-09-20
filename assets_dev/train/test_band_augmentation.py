"""Run: python -m unittest test_band_augmentation -v (no extra packages)."""
import json
import random
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import torch

from train_band import CocoBand


class AugmentationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "annotations").mkdir()
        (self.root / "train2017").mkdir()
        # Non-square image, near-edge target: reveals rounded-scale drift and
        # cropped-target labels which centered rectangular fixtures can miss.
        self.box = [1, 2, 68, 41]
        im = np.zeros((47, 71), np.uint8)
        im[2:43, 1:69] = 255
        cv2.imwrite(str(self.root / "train2017" / "sample.png"), im)
        data = {"images": [{"id": 1, "file_name": "sample.png"}],
                "annotations": [{"image_id": 1, "bbox": self.box}]}
        (self.root / "annotations" / "train.json").write_text(json.dumps(data))

    def dataset(self, aug=True):
        return CocoBand(self.root, "train.json", size=96, aug=aug)

    def test_repeated_visits_vary_but_seeded_run_replays(self):
        ds = self.dataset()
        random.seed(42)
        first = [ds[0] for _ in range(8)]
        self.assertTrue(any(not torch.equal(first[0][1], b) for _, b in first[1:]))
        random.seed(42)
        for (x, b), (xx, bb) in zip(first, [ds[0] for _ in range(8)]):
            self.assertTrue(torch.equal(x, xx))
            self.assertTrue(torch.equal(b, bb))

    def test_full_target_stays_visible_and_label_tracks_pixels(self):
        ds = self.dataset()
        ds._photo = lambda im, rng: im
        random.seed(7)
        for _ in range(100):
            x, b = ds[0]
            self.assertGreaterEqual(float(b.min()), 0)
            self.assertLessEqual(float(b.max()), 96)
            yy, xx = np.where(x[0].numpy() > .8)
            self.assertGreater(len(xx), 0)
            actual = np.array([xx.min(), yy.min(), xx.max()+1, yy.max()+1])
            self.assertLessEqual(float(np.abs(actual-b.numpy()).max()), 2.5)

    def test_no_aug_does_not_consume_randomness_or_change_on_revisit(self):
        ds = self.dataset(False)
        before = random.getstate()
        x, b = ds[0]
        xx, bb = ds[0]
        self.assertEqual(before, random.getstate())
        self.assertTrue(torch.equal(x, xx))
        self.assertTrue(torch.equal(b, bb))


if __name__ == "__main__":
    unittest.main()
