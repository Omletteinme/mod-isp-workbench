# MOD-ISP Hackathon Readiness Audit

**Audit date:** 7 November 2026 (final rubric, dataset-accounting, and full-resolution API pass)  
**Scope:** supplied MOD-ISP blueprint, supplied Problem Statement 2 PDF, visible rubric screenshot, source code, local data manifests, saved training/evaluation reports, and the two links supplied earlier.

## Executive finding

The project is **not currently supportable as a 100/100 submission**. It has a substantial working prototype and one strong, properly held-out sRGB denoising result, but its core Bayer RAW-to-RGB evidence is small and weak, several named blueprint stages are absent or materially different, and the app is local-only. The earlier Apple DNG magenta/grid regression has been fixed and rechecked. The rubric screenshot is partial and internally inconsistent, so an exact total score cannot be calculated. The workbench now presents the measured SIDD-CC sRGB test result as a separate benchmark note and explicitly says it is not a score for the current upload or Bayer RAW quality.

The strongest defensible result is the separate SIDD-CC sRGB denoiser: 206 training pairs from 103 scenes, 24 validation pairs from 12 held-out scenes, and evaluation on all 928 published test blocks. That is evidence for sRGB denoising. It is **not** evidence that the complete Bayer ISP reaches comparable quality. A RAW regression check now confirms that the exact iPhone SE DNG has a clean camera-managed preview and no magenta cast; its Learned/Hybrid comparison uses the sRGB denoiser after LibRaw rendering because the Bayer model has no iPhone-camera training. For this DNG, the three paths share LibRaw's camera-managed rendering; Classical adds conventional finishing, Learned adds the SIDD-CC sRGB denoiser, and Hybrid reuses selected learned tiles. They are useful processing comparisons, but they are not three independently trained, end-to-end Bayer ISP systems. The UI exposes a RAW sensor record containing camera/CFA metadata, normalization levels, WB gains, renderer/matrix status and boundary clipping fractions, with uncalibrated noise clearly disclosed. RAW is usable, but this is not a validated end-to-end learned Bayer ISP for that phone.

## Rubric audit

The visible rubric says the demo/viva is worth 25 points and the other five criteria 15 points each, but the visible table gives Evaluation Metrics a maximum of 25 and Implementation a maximum of 20. The screenshot shows only four table rows; the shown maxima sum to 75. The missing rows and scoring scale need the complete rubric before anyone can calculate a defensible total. Its performance bands also depend on how the submission compares with other participants, which local reports cannot establish.

| Visible criterion | Evidence in this project | Readiness |
|---|---|---|
| Evaluation metrics | The sRGB denoiser improves the SIDD-CC test mean from 26.12 dB / 0.425 SSIM noisy input to 33.78 dB / 0.776. The separate Bayer student has mixed results on only four patches: mean PSNR improves from 10.36 to 12.10 dB, while mean SSIM falls from 0.548 to 0.404 and LPIPS worsens from 0.285 to 0.725. Delta E remains about 28.9. | Strong evidence for a separate sRGB denoising task; insufficient and inconsistent evidence for end-to-end RAW ISP superiority. No cohort ranking is available. |
| Implementation | There are classical, learned, and hybrid paths; training, evaluation, quantization, and error handling code exist. Bayer training is one-scene scale; calibration shares that training scene. The Apple iPhone SE DNG regression was rerun: LibRaw renders its embedded DNG color metadata, and tile blending no longer produces the prior grid. Learned and hybrid paths use the separately trained sRGB denoiser after RAW rendering, not the Bayer checkpoint. The UI reports sensor provenance and sample boundary fractions; it does not claim calibrated noise. | Functional RAW ingest and camera-managed rendering verified on one DNG; limited Bayer training and cross-camera evidence still prevent a top-band claim. |
| UI/UX and deployment | A local Flask app runs at `http://127.0.0.1:5050/`, handles image size limits, and shows path/runtime/reference metrics. A Dockerfile and runtime requirements were added for a single-command container run, but Docker is unavailable here, so a build has not been verified. The app is not publicly deployed. The final live iPhone SE DNG API request returned 200 with all three full-resolution paths in 18.51 s. | Does not meet the visible top-band requirement for a public URL working on phone and laptop; measured full-resolution runtime is over ten seconds. |
| Project documentation | README describes the domains, training, evaluation, limits, result files, and container scope. A current-code architecture diagram has been added. There is no evidence here that the rubric's complete design-document template is satisfied or that another judge can reproduce all results from a clean checkout; the Docker build remains unverified and datasets still must be obtained separately. | Better documented, but reproducibility and template completeness still need a clean-machine check. |
| Demo/viva and two unseen rubric rows | Not measurable from repository artifacts. | Requires the complete rubric and a rehearsed live demo. |

## Training data accounting

### SIDD-CC sRGB denoiser

- The local sRGB training split has 230 paired noisy/ground-truth images across 115 scenes.
- The run used 206 pairs from 103 scenes for fitting and 24 pairs from 12 held-out scenes for validation. Thus **all of the locally available SIDD-CC sRGB training split was accounted for across train and validation**, but the validation pairs were not used for gradient updates.
- The saved final report evaluates the fine-tuned model on all 928 SIDD-CC test blocks. Those test blocks were not used for training.
- This is an sRGB denoising adaptation of Samsung's generic Lite NAFNet checkpoint. It is not a Bayer RAW-to-RGB model and not the full Samsung Modular Neural ISP.

### Bayer RAW-to-RGB student

- The local Bayer data preparation used one SIDD-CC source capture for 40 training crops and eight calibration crops, plus four crops from one different source capture for held-out testing. The 40 training crops equal eight epochs times 40 examples = 320 optimizer steps in the promoted student run.
- The calibration crops come from the **same source capture as training**, so calibration is not scene-independent. The test set is one different capture, only four patches, and is too small to establish broad generalization.
- The full SIDD-CC RAW modality is not present locally. The local SIDD-CC data is the sRGB modality plus two source MAT/PNG pairs used by the Bayer preparation script. The original SIDD project offers substantially more data; that full collection was not used here.
- No ZRR, MAI2021, S24, or Adobe FiveK images were used to train this Bayer student.

### What the Samsung link contributed

The Samsung URL is a **code/model repository**, not the dataset used in the sRGB training run. The local experiment initialized NAFNet from its `generic_lite` checkpoint, then fine-tuned that denoiser on SIDD-CC sRGB. No Samsung S24, Zurich, or Adobe FiveK training images were used. The repository's dataset documentation identifies S24 as its main experiment dataset and describes separate Zurich and MIT-Adobe FiveK evaluation/preparation paths; the S24 dataset itself must be separately obtained. The Bayer student was instead distilled from the 2023 MetaISP checkpoint, not trained from the Samsung repository's complete Modular ISP.

## Blueprint-to-code check

| Blueprint requirement | Current implementation |
|---|---|
| Bayer black-level normalization and white balance | Raw Bayer mosaic normalization and as-shot gains are implemented for the Bayer path. Camera RAW display rendering now uses LibRaw with DNG metadata (including the iPhone SE file's embedded color matrix), rather than treating an unknown camera matrix as identity. The Bayer checkpoint is not used for camera RAW without camera-specific paired validation. |
| Calibrated patch gate | A relative variance/brightness rank gate exists. It is not a sensor-noise estimator. It routes 96% of tiles in the saved held-out test and does not demonstrate the blueprint's stated 341x MAC reduction. |
| Wavelet-attention restoration | A compact ~30K-parameter model uses a fixed Haar-like pixel-unshuffle transform plus channel/spatial attention. It is not the proposed 65K attention U-Net/MW-ISPNet design. |
| 3x3 camera colour correction matrix | The app now delegates DNG camera color rendering to LibRaw, which consumes the embedded matrix with the rest of the DNG metadata. The exposed `rawpy.color_matrix` is XYZ-to-camera and is not incorrectly applied as a direct camera-to-sRGB matrix. This is not the blueprint's separately trained per-camera CCM stage. |
| Tone mapping and sharpening | Tone/exposure finishing and unsharp masking exist. The sharpening is not a guided filter. |
| CNILUT | A pretrained 134,147-parameter, three-style NILUT-derived model is used as an optional style effect. It is not the blueprint's 8.7K camera-calibrated CNILUT and is not part of the INT8 model. |
| Human and machine-vision modes | A mode toggle adjusts finishing targets. There is no downstream detection/recognition benchmark proving machine-vision gains and no learned DynamicISP controller. |
| MetaISP distillation | The student was distilled from a 2023 MetaISP teacher (6,257,501 parameters), not the blueprint's 2024 MetaISP. |
| INT8 LiteRT | A 47,112-byte full-INT8 tile export exists and was compared with PyTorch on eight held-out tiles. One tile has mean absolute output difference about 0.101 and maximum difference about 1.307; the small average masks this outlier. The live app still uses PyTorch, not this LiteRT model. |
| Mobile NPU | Not measured; no phone was available. Local CPU tile timing is not an NPU result. |
| Evaluation metrics | PSNR, SSIM, Delta E, and LPIPS code exists for supplied aligned references. The Bayer evaluation set is only four patches; LPIPS is notably worse for learned/hybrid than the classical baseline there. |

## Highest-value improvements

1. **Expand and qualify RAW color across cameras.** The iPhone SE regression now passes through LibRaw's DNG-aware renderer; validate representative DNG, NEF, CR2/CR3, ARW, RAF and RW2 files and report unsupported metadata. Keep the UI explicit that the trained Bayer checkpoint is not calibrated to arbitrary phone cameras.
2. **Expand the Bayer experiment with scene-level splits.** Obtain the SIDD-CC RAW modality and use train/validation/test splits by scene, keeping calibration separate from training scenes. Preserve metadata and sensor values rather than clipping blindly. Report all image metrics and per-scene results against the classical path. Do not tune on the test scenes.
3. **Close the deployment gap.** The visible rubric explicitly rewards a public URL that opens on phone and laptop. A locally running server does not meet that band. A deployment needs a tested cold start, upload limits, resource budget, and a clear failure state; an external URL has not been created in this audit.
4. **Make the judge demo evidence-first.** Add a one-click, deterministic benchmark run over a small set of documented RAW and low-light cases. Show input, output per path, PSNR/SSIM/Delta E/LPIPS where a matching reference exists, latency, model size, and the exact device. Include a compact per-scene summary so a judge can verify claims without trusting projected targets.
5. **Turn machine-vision mode into a measured claim.** If time permits, evaluate one downstream task on a labeled low-light set and report task accuracy beside image-quality metrics. Until then, describe it as a display/tonality preset, not a detection improvement.

The most defensible near-term differentiator is a **RAW sensor integrity card**, now implemented: detected camera and Bayer pattern, black/white levels, white-balance gains, matrix-use status, renderer, and sensor-boundary clipping fractions. The clipping message uses an explicitly documented 1% heuristic and noise calibration remains unavailable. This makes RAW provenance judge-verifiable without overstating sensor characterization. It does not replace the need for stronger held-out Bayer metrics.

## Evidence references

- `[local Downloads]/mod_isp_hackathon_blueprint.md`, especially Stage 5 and the specified quality audit.
- `[local Downloads]/Computer Vision Hackathon 2026.pdf`, mandatory and advanced requirements.
- [SIDD project and dataset description](https://abdokamel.github.io/sidd/).
- [Samsung Modular Neural ISP code repository](https://github.com/SamsungLabs/modular_neural_isp) and its [dataset documentation](https://github.com/SamsungLabs/modular_neural_isp/blob/main/datasets/README.md).
- Local run reports: `student_metaisp2023_evaluation.json`, `student_metaisp2023_gate_validation.json`, `student_metaisp2023_litert_verification.json`, and `models/sidd_srgb_nafnet_lite.json`.

## Follow-up iPhone SE DNG regression verification

The sample shown in the user's screenshot was found at `[local Downloads]/smartphone-raw-test-images/Apple - iPhone SE - 16bit (4_3).dng`. Its visible CFA is BGGR (normalized by the Bayer loader), black level is 528, white level is 4095, and as-shot white-balance gains are read from RAW metadata. LibRaw exposes a valid DNG color matrix although its generic RGB-to-XYZ matrix is zero for this camera. Because DNG ColorMatrix is XYZ-to-camera and not a direct camera-to-sRGB matrix, runtime rendering now delegates this metadata path to LibRaw's sRGB output rather than applying an identity or incorrectly oriented matrix.

The RAW API was rerun after the change and returned a full-resolution 4030×3022 image with all three comparison paths. The Classical path uses the camera-managed render plus RGB finishing; Learned uses the fine-tuned SIDD-CC sRGB denoiser after that render; Hybrid uses the same denoiser on selected RGB tiles with a smooth spatial transition. The Bayer checkpoint is intentionally not applied to this iPhone RAW because it has no iPhone-camera-specific paired training. Visual inspection confirms the magenta cast and hard square Bayer-tile artifacts are gone. The image remains visibly noisy in dark regions; this is a low-light sample and the sRGB denoiser has no camera-specific RAW calibration. This is a functional RAW ingest/render regression result, not evidence of RAW quality superiority.

The workbench now displays and was browser-verified with a sensor record for this file: Apple iPhone SE, source CFA BGGR, normalized RGGB black levels 528/528/528/528, white level 4095, RGGB WB gains 2.198/1/1/2.0291, and LibRaw AHD camera-WB sRGB rendering. The measured boundary fractions were 3.2457% near black and 0.0014% near white, using a ±1-code-value count. The UI labels this as a heuristic and explicitly states that noise is not camera-calibrated. The comparison reuses learned tile predictions for the Hybrid composition; after this optimization, an HTTP 200 API rerun returned all three full-resolution outputs in 18.5 seconds (Classical 2.59 s, Learned 9.73 s, Hybrid incremental 3.15 s). Hybrid time and Python allocation are explicitly labeled incremental, not standalone costs. These local single-run timings are not mobile measurements.

## Reproducibility and latency follow-up

Added `Dockerfile`, `requirements-runtime.txt`, `run_local.sh`, and `CONTAINER_NOTICE.md` for one-command local and container inference/demo runs. The CPU image uses one Gunicorn worker, supports a health endpoint, and excludes datasets and teacher weights. It includes the NAFNet architecture and upstream license from the pinned Samsung commit. The app accepts `HOST` and `PORT` environment variables and can locate that architecture from either the original workspace clone or its vendored path. Docker and Podman are absent from this environment, so image build and clean-container launch remain unverified.

The RGB and camera-RAW comparison now performs shared sRGB inference once. A synthetic stitching check with an identity model verified cached and independently routed Hybrid outputs differ by at most one 8-bit code value; the cached path adds no model forward calls. The final iPhone SE DNG API check returned HTTP 200, 4030×3022 outputs for all three paths, and 18.51 seconds end-to-end: Classical 2.63 s, Learned 10.41 s, Hybrid 3.25 s incremental. Hybrid reuses the learned predictions and is not a standalone timing. The RAW record reported Apple iPhone SE, source CFA BGGR, normalized RGGB black levels 528, white 4095, WB gains 2.198/1/1/2.0291, LibRaw AHD camera-WB sRGB, 3.2457% shadow-boundary and 0.0014% highlight-boundary samples. This is one Mac run and not a phone benchmark. The full-resolution run still misses the visible rubric's approximate ten-second response target.

## High-return work before judging

These steps are more likely to improve a defensible score than adding more interface controls:

1. **Close data-domain and generalization gaps.** The supplied [SIDD page](https://abdokamel.github.io/sidd/) describes 160 SIDD-Small pairs, 320 SIDD-Medium pairs, and about 24,000 training images in SIDD-Full Raw-RGB, with benchmark-held-out scenes. The page also documents a Bayer-pattern table, camera noise-level functions and DNG archives. None of the full SIDD Raw-RGB corpus or its DNGs is represented by the current local Bayer experiment. Raw-RGB tensors need a documented conversion and color-space contract before they can supervise this app's Bayer-mosaic-to-RGB model. [Samsung's repository documentation](https://github.com/SamsungLabs/modular_neural_isp/blob/main/datasets/README.md) describes S24 Raw-to-sRGB data and Adobe 5K/Zurich preparation paths; those datasets were not locally trained here. Obtain authorized, camera-matched data, split by scene/camera before patch extraction, and publish per-scene results for Classical/Learned/Hybrid. The SIDD page currently says its evaluation server is down and points to Kaggle scoring options, so leaderboard submission needs a separate availability check.
2. **Demonstrate one measured win, not a feature count.** Select a held-out RAW or low-light sRGB case with aligned clean reference; show a fixed side-by-side crop and report PSNR/SSIM, Delta E and LPIPS where the target color space makes each meaningful. Add a small failure case so the limits are visible. The current Bayer report has four patches and mixed metrics, so do not present it as a quality win.
3. **Make the demo repeatable and fast.** Publish a working judge-accessible URL after a tested deployment; add one-command clean-environment setup and verify it from a second device. Preload models, keep a small judge sample ready, and benchmark a representative full-resolution input until cold and warm response times are reliably near the rubric's stated ten seconds. A Dockerfile is not evidence of a successful image build.
4. **Use the viva/demo weight deliberately.** The screenshot gives demo/viva 25 points. Prepare a short sequence: explain the problem and paths; upload the same input and show the enhancement; switch among paths; show provenance and measured metrics; then explain training split, one limitation, and the next experiment. Keep a local backup sample for flaky network or cold-start conditions.
5. **Add a compact robustness matrix.** On held-out images, compare outputs under controlled low-light, sensor noise, compression and mild blur, with degradation levels fixed and recorded. This maps directly to the problem statement's degraded-image requirement and creates a stronger demonstration than a broad but unmeasured set of toggles.

These are recommendations, not completed results. The visible rubric screenshot is incomplete and internally inconsistent; obtain the complete rubric before treating any estimate as a final score.

Follow-up smoke checks passed: Python module compilation, browser JavaScript syntax validation, a 112×112 synthetic Bayer hybrid output with finite bounded pixels, and PNG API processing through Classical/Learned/Hybrid. Local iPhone DNG API timing was approximately 27 seconds for all three paths on this machine (Classical ~2.95 s, Learned ~12.62 s, Hybrid ~8.32 s); these are one-run local measurements and are not deployment or mobile performance claims.
