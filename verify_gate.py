"""Check calibrated Bayer tile routing on an untouched scene-disjoint split."""
import argparse
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from train import pairs, read_pair
import app


def center_crop(mosaic, target, size):
    if not size: return mosaic, target
    h, w = mosaic.shape
    size = min(size, h, w); size -= size % 2
    y = max(0, ((h - size) // 2) // 2 * 2)
    x = max(0, ((w - size) // 2) // 2 * 2)
    return mosaic[y:y+size, x:x+size], target[y:y+size, x:x+size]


def scores(image, target):
    pred = np.asarray(image, dtype=np.float32) / 255
    ref = np.asarray(Image.fromarray(np.uint8(np.clip(target, 0, 1) * 255), 'RGB'), dtype=np.float32) / 255
    mse = float(np.mean((pred - ref) ** 2))
    psnr = float('inf') if mse == 0 else float(-10 * np.log10(mse))
    ssim = float(structural_similarity(ref, pred, channel_axis=2, data_range=1.0))
    return psnr, ssim


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--gate', default='models/gate.json')
    p.add_argument('--checkpoint', default='models/mod_isp.pt')
    p.add_argument('--patch-size', type=int, default=256)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--out', default='gate_validation.json')
    a = p.parse_args()
    config = json.loads(Path(a.gate).read_text())
    app.CHECKPOINT = Path(a.checkpoint)
    rows = []
    for src, tgt in pairs(Path(a.data)):
        mosaic, target = center_crop(*read_pair(src, tgt), a.patch_size)
        results = {}
        for name, fraction in [('all_neural', 1.0), ('calibrated', float(config['route_fraction']))]:
            app.learned(mosaic, hybrid=True, route_fraction=fraction)
            timings, output = [], None
            for _ in range(a.repeats):
                start = time.perf_counter()
                output, routed = app.learned(mosaic, hybrid=True, route_fraction=fraction)
                timings.append((time.perf_counter() - start) * 1000)
            psnr, ssim = scores(output, target)
            results[name] = {'psnr_db': psnr, 'ssim': ssim, 'routed_percent': routed,
                             'latency_median_ms': statistics.median(timings)}
        rows.append({'image': src.name, **results,
                     'quality_change_db': results['calibrated']['psnr_db'] - results['all_neural']['psnr_db']})
        print(f'checked {src.name}', flush=True)
    report = {'gate': config, 'dataset': str(Path(a.data).resolve()),
              'checkpoint': str(Path(a.checkpoint).resolve()), 'environment': platform.platform(),
              'patch_size': a.patch_size, 'repeats': a.repeats,
              'timing': 'Median warm local wall time; not mobile latency or measured MAC reduction.',
              'rows': rows,
              'mean_psnr_change_db': statistics.mean(x['quality_change_db'] for x in rows),
              'worst_psnr_change_db': min(x['quality_change_db'] for x in rows),
              'mean_routed_percent': statistics.mean(x['calibrated']['routed_percent'] for x in rows),
              'mean_latency_all_ms': statistics.mean(x['all_neural']['latency_median_ms'] for x in rows),
              'mean_latency_calibrated_ms': statistics.mean(x['calibrated']['latency_median_ms'] for x in rows)}
    Path(a.out).write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))


if __name__ == '__main__': main()
