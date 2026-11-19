"""Replay the logged warning window without modifying the corpus or renderer.

Run with sugartrain Python: python assets_dev/train/audit_uniform_warning.py
"""
import json
import random
import traceback
import warnings
from pathlib import Path

import cv2
import numpy as np
import synth_panel as sp

HERE = Path(__file__).resolve().parent
RUN = HERE / '_diag' / 'uniform_20261031'
CORPUS = HERE / 'synth_coco' / 'UNIFORM_20261031'


def main():
    plan = [json.loads(s) for s in (RUN / 'plan.jsonl').read_text(encoding='utf-8').splitlines()]
    manifest = [json.loads(s) for s in (CORPUS / 'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    original = np.nanmedian
    calls = []

    def observed(a, *args, **kwargs):
        if not np.isfinite(a).any():
            calls.append(dict(shape=list(a.shape), size=int(a.size),
                              stack=traceback.format_stack(limit=5)))
        return original(a, *args, **kwargs)

    report = dict(manifest_n=len(manifest), nonfinite_gpc_ids=[r['id'] for r in manifest
                  if not np.isfinite(r['glyph_plane_check'])], replay=None)
    np.nanmedian = observed
    try:
        # Warning was logged after rendered 5750 and before rendered 6000.
        for i in range(5750, 6000):
            row = plan[i]
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', RuntimeWarning)
                sample = sp.render_panel(row['value'], random.Random(f'20261031:{i}'),
                    profile=sp.TRAIN_PROFILES[row['profile_idx']], scene='panel', trait=row)
            if calls:
                stored = cv2.imread(str(CORPUS / 'train2017' / (row['id'] + '.png')),
                                    cv2.IMREAD_GRAYSCALE)
                report['replay'] = dict(id=row['id'], value=row['value'], calls=calls,
                    warnings=[str(w.message) for w in caught],
                    pixels_equal=bool(np.array_equal(sample['panel'], stored)),
                    label_equal=sample['label'] == manifest[i]['label'],
                    gpc=sample['glyph_plane_check'], saved_gpc=manifest[i]['glyph_plane_check'])
                break
    finally:
        np.nanmedian = original
    path = RUN / 'warning_audit.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    if report['replay'] is None or not report['replay']['pixels_equal'] or not report['replay']['label_equal'] or report['nonfinite_gpc_ids']:
        raise SystemExit('Warning audit did not establish safe diagnostic fallback')


if __name__ == '__main__':
    main()
