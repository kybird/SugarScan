"""Geometry and paired-background checks through the real renderer."""
import random
import unittest
from pathlib import Path

import cv2
import numpy as np

import synth_panel as sp
from device_scene import compose


class DeviceSceneTest(unittest.TestCase):
    def test_default_panel_still_matches_existing_corpus(self):
        root = Path(__file__).parent / "synth_coco/TB/train2017"
        if not root.exists():
            self.skipTest("optional local TB corpus not present")
        old = sp.PROCEDURAL_BG
        self.addCleanup(setattr, sp, "PROCEDURAL_BG", old)
        sp.PROCEDURAL_BG = True
        rng = random.Random(20261001)
        for i in range(3):
            sample = sp.render_panel(sp.sample_value(rng), rng)
            expected = cv2.imread(str(root/f"panel_20261001_{i}.png"), 0)
            np.testing.assert_array_equal(sample["panel"], expected)

    def test_panel_pixels_and_glyph_are_translated_without_resampling(self):
        panel = np.arange(80*120, dtype=np.uint8).reshape(80, 120)
        mask = np.full_like(panel, 255)
        glyph = np.zeros_like(panel)
        glyph[25:55, 20:90] = 255
        out, cover, moved, (x, y) = compose(panel, mask, glyph, random.Random(2), 130, 40)
        np.testing.assert_array_equal(out[y:y+80, x:x+120], panel)
        np.testing.assert_array_equal(moved[y:y+80, x:x+120], glyph)
        self.assertTrue(np.all(cover[y:y+80, x:x+120] == 255))

    def test_camera_geometry_and_background_parity(self):
        old = sp.PROCEDURAL_BG
        self.addCleanup(setattr, sp, "PROCEDURAL_BG", old)
        cv2.setNumThreads(1)
        for seed in range(12):
            sp.PROCEDURAL_BG = False
            a = sp.render_panel(123, random.Random(seed), scene="device")
            sp.PROCEDURAL_BG = True
            b = sp.render_panel(123, random.Random(seed), scene="device")
            for key in ("quad", "digit_box", "glass_quad", "cover", "glyph_warped"):
                np.testing.assert_array_equal(a[key], b[key], err_msg=key)
            inner = a["cover"] == 255
            np.testing.assert_array_equal(a["panel"][inner], b["panel"][inner])
            box = np.r_[b["quad"].min(0), b["quad"].max(0)]
            digit = b["digit_box"]
            self.assertTrue(all(box[i] <= digit[i]+1 for i in (0, 1)))
            self.assertTrue(all(box[i] >= digit[i]-1 for i in (2, 3)))
            self.assertGreaterEqual(min(digit), 0)
            self.assertLessEqual(digit[2], b["W"])
            self.assertLessEqual(digit[3], b["H"])
            self.assertEqual(max(b["W"], b["H"]), sp.LONG_SIDE)

    def test_scene_does_not_change_parent_rng_or_value_sequence(self):
        a, b = random.Random(71), random.Random(71)
        for _ in range(5):
            va, vb = sp.sample_value(a), sp.sample_value(b)
            self.assertEqual(va, vb)
            x = sp.render_panel(va, a)
            y = sp.render_panel(vb, b, scene="mixed")
            self.assertEqual(a.getstate(), b.getstate())
            self.assertEqual(x["profile"], y["profile"])


if __name__ == "__main__":
    unittest.main()
