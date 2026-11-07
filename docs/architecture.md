# System architecture

This diagram reflects the implemented code paths. The Bayer restoration model, sRGB denoiser, and camera-managed RAW renderer are separate paths; they are not interchangeable models.

```mermaid
flowchart TB
  U[Browser workbench] -->|multipart image + profile + options| API[Flask /api/process]
  API --> DEC{Input decoder}
  DEC -->|Camera RAW| RAW[rawpy / LibRaw\nCFA + levels + WB metadata\nAHD demosaic + sRGB render]
  DEC -->|Normalized RGGB .npy| BAYER[Validate 2-D [0,1]\nRGGB mosaic]
  DEC -->|JPEG / PNG / WebP / TIFF| RGB[Rendered RGB image]

  RAW --> RGBPIPE[RGB finishing]
  RGB --> RGBPIPE
  RGBPIPE --> CLASSRGB[Classical RGB\nexposure + bilateral + detail]
  RGBPIPE --> SIDD[SIDD-CC sRGB\nNAFNet denoiser]
  RGBPIPE --> RGBGATE[RGB high-pass tile ranking]
  RGBGATE -->|selected tiles| SIDD
  RGBGATE -->|unselected tiles| CLASSRGB

  BAYER --> NORM[Black-level normalization\nand as-shot WB]
  NORM --> DEMOSAIC[Classical bilinear demosaic]
  NORM --> MODISP[Compact Bayer-v1\nrestoration network]
  NORM --> GATE[Relative variance/brightness\ntile rank gate]
  GATE -->|selected tiles| MODISP
  GATE -->|remaining tiles| DEMOSAIC
  DEMOSAIC --> FINISH[Bayer RGB finishing]
  MODISP --> FINISH
  GATE --> FINISH

  CLASSRGB --> RESULTS[Encoded outputs per available path]
  SIDD --> RESULTS
  FINISH --> RESULTS
  RESULTS --> REF{Aligned reference attached?}
  REF -->|yes| METRICS[PSNR · SSIM · Delta E 2000 · LPIPS]
  REF -->|no| OUT[Return images + actual local timing + resource measurements]
  METRICS --> OUT
  OUT --> U

  subgraph Research workflow
    PAIRS[Registered input/target pairs] --> TRAIN[train.py\nL1 reconstruction + optional teacher loss]
    TEACHER[Optional supplied teacher] --> TRAIN
    TRAIN --> CKPT[Bayer checkpoint]
    CKPT --> EXPORT[export_litert.py]
    CAL[Calibration split] --> GATECFG[calibrate_gate.py]
    CKPT --> GATECFG
    TEST[Held-out split] --> EVAL[evaluate.py / verify_gate.py]
    CKPT --> EVAL
    GATECFG --> EVAL
  end
```

## Runtime boundaries

- Uploads are processed by the local Flask app. The image API is not a hosted service.
- Camera RAW is rendered through LibRaw using camera metadata; the Bayer model is intentionally not applied to camera RAW without camera-specific paired validation.
- `.npy` Bayer input must be a finite normalized 2-D RGGB mosaic in `[0,1]`.
- Rendered RGB stays in an RGB denoising/finishing path and is never mosaiced for inference.
- When a matching, aligned reference is supplied, metrics compare each returned output to that reference. Without one, quality metrics are absent.
- The hybrid path is a tile-routing heuristic. Routed-tile percentage is not a measured MAC reduction; reported incremental timing is not standalone end-to-end latency.

## Source map

| Concern | Files |
|---|---|
| Web UI and API | `app.py`, `templates/index.html`, `static/` |
| Bayer decoding and classical ISP | `isp.py` |
| Compact Bayer model | `model.py` |
| Training / teacher distillation | `train.py`, `metaisp2023_adapter.py` |
| sRGB denoiser training | `train_sidd_srgb.py`, vendored NAFNet definition under `third_party/` |
| Evaluation / gate / export | `evaluate.py`, `calibrate_gate.py`, `verify_gate.py`, `export_litert.py` |
