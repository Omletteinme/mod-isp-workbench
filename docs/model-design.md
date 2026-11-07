# Model and implementation design

## Scope

MOD-ISP is an experimental local image signal processing workbench. It implements two distinct restoration domains:

1. A compact Bayer mosaic to RGB student (`bayer-v1`), with classical demosaicing and a tile-gated hybrid path.
2. A fine-tuned sRGB NAFNet denoiser for already rendered images, including camera RAW rendered to sRGB by LibRaw.

It is not a universal camera ISP, a camera-calibrated denoiser for arbitrary sensors, or a measured mobile-NPU deployment.

## Bayer model

`ModISP` accepts four packed RGGB planes at half resolution. It applies a 2×2 pixel-unshuffle and a fixed Haar-like sum/difference transform, followed by two convolutional encoder layers, channel attention, spatial attention, a decoder, and pixel-shuffle upsampling. A small pointwise color network receives the RGB estimate and its image-wide mean color context. The model has 29,980 trainable parameters in the shipped configuration.

Training uses registered input/target crops and an L1 reconstruction objective. An optional teacher adds a weighted L1 distillation term. The promoted student was distilled from the authors' 2023 MetaISP `real_D` checkpoint for 320 optimizer steps. The teacher adapter uses patch-local resized BGR context and explicit sensor metadata; this differs from the teacher's full-frame inference context and remains an adaptation.

The present Bayer data experiment used 40 training crops and eight calibration crops from one SIDD-CC source capture, plus four held-out crops from a different capture. The calibration source is the training scene. Therefore the four-patch result is a smoke-scale, scene-separated comparison, not evidence of broad cross-camera or cross-scene generalization.

## Classical and hybrid Bayer paths

The classical baseline normalizes and white-balances the mosaic, applies bilinear demosaicing, then runs RGB finishing. The hybrid rank gate scores tiles by variance normalized by squared mean brightness and selects a fixed per-image fraction. Neural restoration runs on selected tiles; remaining tiles keep the classical result, with blending at transitions.

The gate was selected on same-scene calibration crops with a 0.5 dB mean PSNR-drop budget. This is a relative tile-ranking heuristic, not a calibrated sensor-noise model. A 96% routed fraction does not establish 4% MAC savings or a latency improvement.

## sRGB path

The sRGB denoiser is a 245,223-parameter fine-tuned Samsung generic-lite NAFNet. It was initialized from the upstream checkpoint and fine-tuned on 206 SIDD-CC sRGB pairs from 103 scenes, with 24 pairs from 12 separate training scenes held for validation. The fine-tuned checkpoint was evaluated on 928 SIDD-CC test blocks. This is an sRGB-domain denoising experiment, not the Bayer model and not an official leaderboard result.

For camera RAW, LibRaw performs camera-aware demosaic and sRGB rendering. The sRGB denoiser runs after that render. The Bayer student is not used on arbitrary camera RAW because camera-specific paired training and validation are unavailable.

## Execution and evaluation

`app.py` exposes local upload and processing APIs. It enforces a 30 MB upload cap and a 16-megapixel processing limit; oversized rendered RGB inputs are resized by the app while oversized RAW/NPY inputs fail to preserve mosaic handling. Where a same-size aligned reference is supplied, the evaluator records PSNR, SSIM, CIEDE2000 Delta E, and LPIPS where available. Per-run latency and memory figures are local to the recorded machine and process; memory accounting has documented exclusions.

Training/evaluation data, local virtual environments, and the original 2023 teacher weights are deliberately excluded from this repository. The code and scripts are complete; reproduce experiments only with separately acquired, authorized data and teacher checkpoints.

## Known design limits

- Bayer training and calibration are tiny and scene-concentrated.
- Bayer learned and hybrid paths have substantial perceptual-metric regressions on some held-out patches.
- Relative gate calibration does not guarantee quality on unseen scenes.
- The sRGB and Bayer domains have separate weights and color assumptions.
- LiteRT tile equivalence has a severe outlier on one held-out tile; the mean alone hides it.
- No phone/NPU runtime, broad multi-camera benchmark, or downstream machine-vision benefit has been measured.
