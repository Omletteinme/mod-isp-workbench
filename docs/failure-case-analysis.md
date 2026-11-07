# Failure-case analysis

The examples below are actual held-out Bayer patches from the four-patch report. They expose disagreement among pixel, structural, color, and perceptual metrics. They are diagnostic examples, not a complete error taxonomy.

## Bayer restoration regressions

### `test_001`: both learned paths damage structure/perceptual similarity

| Path | PSNR dB | SSIM | Delta E 2000 | LPIPS |
|---|---:|---:|---:|---:|
| Classical | 9.67 | 0.5731 | 34.36 | 0.4298 |
| Learned | 9.73 | 0.1631 | 38.19 | 0.9002 |
| Hybrid | 9.89 | 0.0996 | 33.99 | 1.0113 |

Learned and Hybrid slightly improve PSNR, but SSIM and LPIPS worsen sharply. The small PSNR increase does not imply a visually better result. This scene/patch should be inspected for texture/edge hallucination and tile boundary effects before any model claim is made.

### `test_003`: Learned is worse on every listed quality metric

| Path | PSNR dB | SSIM | Delta E 2000 | LPIPS |
|---|---:|---:|---:|---:|
| Classical | 10.60 | 0.5497 | 29.52 | 0.1939 |
| Learned | 10.10 | 0.3677 | 35.61 | 0.7292 |
| Hybrid | 10.85 | 0.2486 | 29.07 | 0.7557 |

Learned is worse than Classical in all four metrics. Hybrid recovers PSNR and slightly reduces Delta E but has lower SSIM and much worse LPIPS. This is a concrete example of the route/model improving some scalar measurements while losing perceptual similarity.

### `test_002`: high PSNR does not protect perceptual quality

Learned reaches 13.10 dB PSNR versus 9.77 dB Classical, while SSIM falls from 0.6180 to 0.5054 and LPIPS rises from 0.1918 to 0.6613. Hybrid is similar: 12.87 dB PSNR, 0.3539 SSIM, and 0.6965 LPIPS. This motivates reporting multiple metrics and image crops rather than selecting a model from PSNR alone.

## Quantized tile outlier

On INT8 comparison tile `test_002` at `[0,0]`, input clipping remained 0%, but mean absolute output error reached 0.1012 and max absolute error reached 1.3072. The other seven checked tiles had mean error around 0.0050–0.0061. The rare outlier is not represented well by the overall mean and should be traced to activation range/quantization behavior and retested with more tiles.

## Generalization and coverage risks

- Bayer test coverage is four crops from one unseen capture; the calibration crops are from the training capture. Camera and scene variation remain unmeasured.
- sRGB test performance is evaluated on benchmark blocks but may not transfer to arbitrary cameras, Bayer RAW, or other noise distributions.
- Camera RAW rendering relies on LibRaw metadata; a successful decode does not certify restoration quality for that camera.
- The hybrid gate routes 96% of tiles in this validation and loses up to 0.552 dB PSNR on one patch. Its route fraction is not a noise estimate or hardware cost measurement.
- No downstream recognition accuracy, mobile NPU delegate, or broad camera matrix has been tested.

## Recommended next diagnostics

1. Save aligned input, target, Classical, Learned, and Hybrid crops for `test_001`–`test_003`, with fixed display range and no hidden postprocessing.
2. Log per-tile gate scores, selected mask, output residual, and crop-level metric deltas to identify whether regressions are localized or global.
3. Re-run INT8-vs-float comparison on a stratified set of tiles and report median, 95th percentile, maximum, and spatial maps.
4. Expand Bayer train/calibration/test splits by source scene and camera before changing thresholds or reporting a quality claim.
