# Container runtime scope

The Docker image is an inference/demo runtime. It contains the app and its three inference checkpoints, but not datasets, training scripts, teacher weights, or LiteRT export dependencies. Training and export remain host-side workflows documented in `README.md`.

The image includes only Samsung's `denoising/nafnet_arch.py` and its `LICENSE.md`, copied from upstream commit `5a845f673edfdf92de18dcfc20d204f79f1ba38b`; this is the model definition used by the supplied sRGB checkpoint. The full Samsung Modular Neural ISP repository and its weights have CC BY-NC 4.0 terms. Review upstream terms before redistributing or using the image commercially. The generic CPU image does not claim mobile NPU support.
