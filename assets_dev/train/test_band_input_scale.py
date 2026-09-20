"""Regression tests for the letterbox-scale ruler, without photo corpora."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from measure_panel_stats import cmd_input_scale


class InputScaleTest(unittest.TestCase):
    def test_different_original_sizes_map_to_same_input_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "coco.json"
            path.write_text(json.dumps({
                "images": [{"id": 1, "width": 832, "height": 416},
                           {"id": 2, "width": 416, "height": 832}],
                "annotations": [{"image_id": 1, "bbox": [0, 0, 200, 100]},
                                {"image_id": 2, "bbox": [0, 0, 100, 200]}]}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_input_scale(coco=path)
            self.assertIn("50.00/50.00/50.00/50.00/50.00", out.getvalue())
            self.assertIn("[32,64) n=2", out.getvalue())

    def test_gate_counts_missed_detection_and_oversized_boxes_as_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pred.jsonl"
            base = {"ow": 416, "oh": 416, "gt": [100, 100, 200, 150],
                    "pred": [100, 100, 200, 150], "det": True}
            rows = [base, dict(base, det=False),
                    dict(base, pred=[0, 0, 400, 400]),
                    dict(base, pred=[0, 0, 20, 20]),
                    dict(base, pred=[130, 100, 200, 150])]
            path.write_text("\n".join(json.dumps(r) for r in rows))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_input_scale(predictions=path)
            self.assertIn("n=5 detected=0.8000 deployed_label_gate=0.2000", out.getvalue())
            self.assertIn('"missed":1,"disjoint":1,"partial_label":1,"oversized":1,"passed":1',
                          out.getvalue())


if __name__ == "__main__":
    unittest.main()
