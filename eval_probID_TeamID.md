# Comparative Evaluation — `probID` / `TeamID`

> **Filename note:** The contest/problem ID and team ID were not present in the workspace. This requested filename is retained as a template; replace `probID` and `TeamID` when those identifiers are known. No identity is inferred.

## Summary

MOD-ISP contains separate sRGB denoising and Bayer-to-RGB experiments. Their data domains and evaluation sets differ, so they are reported in separate tables. Results below are measurements from the checked-in run artifacts, not newly run experiments.

## Bayer RAW / RGGB paths

Four held-out patches from one source capture, evaluated on macOS 15.7.7 arm64. The calibration crops came from the training capture. This is a small scene-separated smoke test, not a broad benchmark.

| Pipeline | PSNR ↑ dB | SSIM ↑ | Delta E 2000 ↓ | LPIPS ↓ | Recorded latency ms |
|---|---:|---:|---:|---:|---:|
| Classical | 10.355 | 0.5483 | 29.1825 | 0.2853 | 17.83 |
| Learned (`models/mod_isp.pt`) | 12.095 | 0.4042 | 28.9325 | 0.7248 | 23.93 |
| Hybrid (`models/mod_isp.pt`) | 12.005 | 0.2722 | 27.4000 | 0.8068 | 43.21 |
| 2023 MetaISP teacher, reference only | 17.630 | 0.6939 | 13.6800 | 0.1884 | 234.18 |

The learned student improves mean PSNR over Classical by 1.74 dB but reduces mean SSIM by 0.1441 and worsens LPIPS by 0.4395. Hybrid has a slightly lower mean Delta E and similar PSNR to Learned, but lower SSIM and higher LPIPS. Results are mixed across quality dimensions; no overall quality winner is claimed. The teacher is a different model and context path, and is not a controlled student ablation.

## sRGB denoising comparison

SIDD-CC sRGB test split, 928 blocks. This is a different model and task from the Bayer experiment. Metrics are mean block values; this is not official leaderboard scoring.

| Input/model | PSNR ↑ dB | SSIM ↑ |
|---|---:|---:|
| Noisy input | 26.1189 | 0.4251 |
| Samsung generic-lite initialization | 29.3029 | 0.5738 |
| Fine-tuned SIDD-CC sRGB model | 33.7765 | 0.7762 |

The fine-tuned model is +4.4736 dB PSNR and +0.2024 SSIM over the initialized checkpoint on this split. These values should not be presented as Bayer RAW results or as independent multi-camera performance.

## Bayer gate ablation

The gate was calibrated using a 0.5 dB mean PSNR-drop budget on same-capture calibration crops. On four held-out patches it routed 96% of tiles. Comparison against the all-neural hybrid path:

| Statistic | Result |
|---|---:|
| Mean PSNR change | −0.2336 dB |
| Worst patch PSNR change | −0.5516 dB |
| Mean routed fraction | 96% |
| All-neural median warm CPU time | 40.752 ms |
| Calibrated-gate median warm CPU time | 40.401 ms |
| Difference | −0.351 ms (−0.86%) |

This small timing delta is not evidence of a reliable speedup. Routed-tile percentage is not MAC reduction, and this is not mobile/NPU timing.

## LiteRT INT8 equivalence check

Eight held-out tiles were compared against PyTorch float32 on CPU. Mean absolute error was 0.01737, and input clipping was 0% on the sample. One tile (`test_002`, `[0,0]`) had mean absolute error 0.10122 and maximum error 1.30722; the other seven tiles had mean errors between 0.00503 and 0.00614. The outlier makes the overall mean an incomplete summary. No mobile delegate or NPU was tested.

## Failure cases

| Patch | Path | PSNR dB | SSIM | Delta E | LPIPS | Observation |
|---|---|---:|---:|---:|---:|---|
| `test_001` | Classical | 9.67 | 0.5731 | 34.36 | 0.4298 | Reference baseline |
| `test_001` | Learned | 9.73 | 0.1631 | 38.19 | 0.9002 | Small PSNR gain with strong SSIM/LPIPS regression |
| `test_001` | Hybrid | 9.89 | 0.0996 | 33.99 | 1.0113 | PSNR/Delta E improve slightly; perceptual metrics worsen |
| `test_003` | Classical | 10.60 | 0.5497 | 29.52 | 0.1939 | Reference baseline |
| `test_003` | Learned | 10.10 | 0.3677 | 35.61 | 0.7292 | Worse on all listed quality metrics |
| `test_003` | Hybrid | 10.85 | 0.2486 | 29.07 | 0.7557 | Better PSNR/Delta E; worse SSIM/LPIPS |
| `test_002` | Classical | 9.77 | 0.6180 | 27.07 | 0.1918 | Reference baseline |
| `test_002` | Learned | 13.10 | 0.5054 | 19.76 | 0.6613 | PSNR/Delta E improve, LPIPS regresses substantially |
| `test_002` | Hybrid | 12.87 | 0.3539 | 22.62 | 0.6965 | Similar metric disagreement |

## Setup and limitations

- The Bayer student has 29,980 parameters and was trained for 320 optimizer steps on 40 crops from one source capture.
- Calibration used eight crops from that same training capture; held-out evaluation used four crops from one other capture.
- Bayer and sRGB models use different input domains and training/evaluation sets.
- LPIPS may be null when its dependency or weights are unavailable; values above are the recorded run values.
- Process timing and memory are machine-specific; reported values are not phone measurements.
- A broad multi-scene/camera benchmark and statistical significance analysis have not been performed.

## Source artifacts

- `evaluation.json`
- `student_metaisp2023_evaluation.json`
- `teacher2023_evaluation.json`
- `student_metaisp2023_gate_validation.json`
- `student_metaisp2023_litert_verification.json`
- `models/sidd_srgb_nafnet_lite.json`
