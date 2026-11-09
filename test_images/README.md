# Test images

23 files, about 8 MB. Upload any of them at http://127.0.0.1:5050 under **Source image**. The photos are the public-domain / CC0 samples bundled with scikit-image, cropped to 512×384 (or 196×205 for the small set). Everything noisy or dark is synthetic and seeded, so `make_test_images.py` recreates the same files.

For the noisy files, upload the clean photo of the same name from `clean/` as **Aligned reference** to get PSNR, SSIM and Delta E. For the dark and uneven-light files the clean photo is a brightness target, not a pixel match, so the metrics mostly measure exposure.

| Folder | Files | What it tests |
|---|---|---|
| `clean/` | astronaut, camera (grayscale), chelsea, coffee | Do-no-harm: a clean photo should come out about the same. Also the aligned references |
| `noisy_gaussian/` | astronaut σ15 / σ25 / σ50, coffee σ25, camera σ25 | Independent per-pixel noise at mild, moderate and heavy levels. σ50 should make Hybrid fall back to Classical |
| `noisy_correlated/` | astronaut, coffee (blotchy) | Colour noise spread over a few pixels, like resized or compressed noise. A pixel-level noise estimate reads this as clean |
| `low_light/` | astronaut dark (clean and noisy), coffee very dark, chelsea dark, astronaut and coffee uneven light | Brightening with shot and read noise (simulated in linear light), and one bright patch falling off into deep shadow, which a single global gain cannot handle |
| `small/` | camera and astronaut face crops (196×205), each clean and σ20 | Small, textured images: the size that exposed the frame-zoom bug and the over-smoothing |
| `bayer_npy/` | astronaut RGGB mosaic, clean and dark+noisy | The Bayer path: normalized **linear-light** RGGB `.npy`, float32 in [0, 1] |

## Known behaviour worth watching

- **Bayer student output is brighter than the input.** On the clean `.npy`, Classical and the source agree (mean luma 117) but Learned/Hybrid come out near 176. The Bayer path is the one the README says was trained on a tiny, single-scene set.
- **Hybrid on rendered images** uses the learned denoiser only where it reduces the image's noise estimate; otherwise it returns the classical result and says so in the summary line.

Regenerate with `python test_images/make_test_images.py` from the project root (needs numpy, Pillow, SciPy and scikit-image, all in the full requirements).
