# Ablation study and component comparisons

## Reporting rule

The available evidence is a mixture of a four-patch Bayer smoke test, a four-patch gate check, and a 928-block sRGB benchmark. These datasets and tasks are not pooled. Metrics are recorded values from the checked-in run JSONs; this report does not add statistical significance claims.

## Bayer path comparison

Four held-out patches from one different SIDD-CC source capture, macOS 15.7.7 arm64. Values below are arithmetic means over those four patches. Latency is reported per method from the original run file, and is not a controlled benchmark with confidence intervals.

| Path | PSNR ↑ dB | SSIM ↑ | Delta E 2000 ↓ | LPIPS ↓ | Latency ms |
|---|---:|---:|---:|---:|---:|
| Classical | 10.355 | 0.5483 | 29.1825 | 0.2853 | 17.83 |
| Learned Bayer student | 12.095 | 0.4042 | 28.9325 | 0.7248 | 23.93 |
| Hybrid tile-gated | 12.005 | 0.2722 | 27.4000 | 0.8068 | 43.21 |
| 2023 MetaISP teacher (reference only) | 17.630 | 0.6939 | 13.6800 | 0.1884 | 234.18 |

The student improves mean PSNR over Classical by 1.74 dB and mean Delta E by 0.25, while SSIM is 0.1441 lower and LPIPS 0.4395 higher. Hybrid has the lowest mean Delta E and is only 0.09 dB below Learned in PSNR, but has lower SSIM and higher LPIPS and the longest local method time. The teacher row is not a student ablation: it uses a distinct model/context path and is shown as an upper reference for these four patches only.

## Gate ablation: all-neural hybrid vs calibrated routing

The calibrated gate was checked against all-neural hybrid on the same four Bayer test patches. It routes a mean 96% of tiles. Paired mean PSNR change is **−0.2336 dB**; worst patch change is **−0.5516 dB**. Median warm local CPU times were 40.752 ms (all-neural) and 40.401 ms (calibrated), a 0.351 ms / 0.86% difference in this small run. This does not show a reliable speedup or MAC reduction; timing noise and model loading dominate this small measurement.

| Patch | All-neural PSNR dB | Gate PSNR dB | Δ PSNR dB | Routed tiles | All-neural ms | Gate ms |
|---|---:|---:|---:|---:|---:|---:|
| test_000 | 14.637 | 14.407 | −0.230 | 96% | 40.932 | 40.164 |
| test_001 | 9.923 | 9.894 | −0.029 | 96% | 39.211 | 38.763 |
| test_002 | 13.426 | 12.875 | −0.552 | 96% | 41.576 | 41.732 |
| test_003 | 10.970 | 10.846 | −0.124 | 96% | 41.291 | 40.947 |

## sRGB denoiser comparison

SIDD-CC sRGB test split, 928 blocks. The fine-tuned model is compared with the noisy input and its upstream Samsung generic-lite initialization. This is a separate task/domain from Bayer restoration.

| Model/input | Mean block PSNR ↑ dB | Mean block SSIM ↑ |
|---|---:|---:|
| Noisy input | 26.119 | 0.4251 |
| Samsung generic-lite initialization | 29.303 | 0.5738 |
| Fine-tuned SIDD-CC sRGB model | 33.776 | 0.7762 |

The fine-tuned result is +4.474 dB and +0.2024 SSIM over the initialization on this benchmark test split. It is not official leaderboard scoring, and these numbers must not be presented as Bayer RAW results.

## INT8 export comparison

Eight held-out tiles compared PyTorch float32 with full-int8 LiteRT on CPU. Input clipping was 0% across the eight tiles; mean output absolute error was 0.01737. One tile (`test_002`, `[0,0]`) had mean absolute error 0.1012 and maximum absolute error 1.3072. The other seven tiles had mean absolute errors from 0.0050 to 0.0061. This outlier requires investigation; average error alone is misleading. This does not establish phone compatibility, NPU execution, or end-to-end speed.

## Limitations

These are descriptive ablations over existing runs, not repeated-seed experiments. The four-patch Bayer test and same-source calibration cannot support generalization claims or significance tests. Perceptual metrics disagree, so no single aggregate winner is claimed. Full per-image rows remain in the JSON artifacts and `eval_probID_TeamID.md`.
