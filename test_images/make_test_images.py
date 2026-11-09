"""Regenerate the test images in this folder (seeded, so the output is repeatable).

    .venv\\Scripts\\python.exe test_images\\make_test_images.py        (Windows)
    .venv/bin/python test_images/make_test_images.py                   (macOS/Linux)

Sources are the public-domain / CC0 sample photos bundled with scikit-image.
Noisy variants are synthetic, so the clean original in clean/ is an exact aligned
reference for them (upload it as "Aligned reference" to get PSNR / SSIM / Delta E).
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage import data

HERE = Path(__file__).parent
W, H = 512, 384
rng = np.random.default_rng(2026)


def source(name):
    arr = getattr(data, name)()
    im = Image.fromarray(arr)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    # Fit-and-crop to W x H so every derived image has an identical size.
    scale = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left, top = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((left, top, left + W, top + H))


def save(im, folder, name):
    out = HERE / folder
    out.mkdir(exist_ok=True)
    Image.fromarray(np.uint8(np.clip(np.asarray(im), 0, 255) + 0.5)).save(out / name, optimize=True)


def to_lin(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return 255.0 * np.where(a <= 0.0031308, 12.92 * a, 1.055 * a ** (1 / 2.4) - 0.055)


def gaussian_noise(img, sigma):
    return np.asarray(img, np.float32) + rng.normal(0, sigma, (H, W, 3))


def blotchy_noise(img, std=34.0, blur=1.2):
    """Colour noise that is correlated over a few pixels (like resized or compressed noise)."""
    n = np.stack([gaussian_filter(rng.normal(0, 1, (H, W)), blur) for _ in range(3)], -1)
    n *= std / n.std()
    return np.asarray(img, np.float32) + n


def low_light_linear(img, gain, photons=300.0, read=0.004):
    """Dark capture with shot noise + read noise, in linear light."""
    lin = to_lin(np.asarray(img, np.float32)) * gain
    return rng.poisson(lin * photons) / photons + rng.normal(0, read, lin.shape)


def low_light(img, gain):
    return to_srgb(low_light_linear(img, gain))


def uneven_light(img):
    """A bright patch on the left falling off to deep shadow on the right, plus a little noise."""
    x = np.linspace(0, 1, W)[None, :]
    y = np.linspace(0, 1, H)[:, None]
    lamp = np.exp(-(((x - 0.18) / 0.35) ** 2 + ((y - 0.4) / 0.6) ** 2))
    illum = 0.035 + 0.965 * lamp
    return to_srgb(to_lin(np.asarray(img, np.float32)) * illum[..., None] + rng.normal(0, 0.002, (H, W, 3)))


photos = {n: source(n) for n in ('astronaut', 'coffee', 'chelsea', 'camera')}

for n, im in photos.items():
    save(im, 'clean', f'{n}.png')

for n, s in (('astronaut', 15), ('astronaut', 25), ('astronaut', 50), ('coffee', 25), ('camera', 25)):
    save(gaussian_noise(photos[n], s), 'noisy_gaussian', f'{n}_sigma{s}.png')

for n in ('astronaut', 'coffee'):
    save(blotchy_noise(photos[n]), 'noisy_correlated', f'{n}_blotchy.png')

save(to_srgb(to_lin(np.asarray(photos['astronaut'], np.float32)) * 0.08), 'low_light', 'astronaut_dark_clean.png')
save(low_light(photos['astronaut'], 0.08), 'low_light', 'astronaut_dark_noisy.png')
save(low_light(photos['coffee'], 0.05), 'low_light', 'coffee_very_dark_noisy.png')
save(low_light(photos['chelsea'], 0.10), 'low_light', 'chelsea_dark_noisy.png')
save(uneven_light(photos['astronaut']), 'low_light', 'astronaut_uneven_light.png')
save(uneven_light(photos['coffee']), 'low_light', 'coffee_uneven_light.png')

# Small, textured crops (the size that exposed the zoom and over-smoothing bugs).
small = {
    'camera_196x205': photos['camera'].crop((170, 20, 366, 225)),
    'astronaut_face_196x205': photos['astronaut'].crop((190, 10, 386, 215)),
}
for n, im in small.items():
    save(im, 'small', f'{n}.png')
    save(np.asarray(im, np.float32) + rng.normal(0, 20, (205, 196, 3)), 'small', f'{n}_sigma20.png')

# Normalised RGGB Bayer mosaics (.npy, float32 in [0, 1]) for the Bayer path.
def mosaic(linear_rgb):
    """RGGB mosaic of LINEAR-light values in [0, 1], which is what the app expects for .npy input."""
    a = np.asarray(linear_rgb, np.float32)
    m = np.empty(a.shape[:2], np.float32)
    m[0::2, 0::2] = a[0::2, 0::2, 0]
    m[0::2, 1::2] = a[0::2, 1::2, 1]
    m[1::2, 0::2] = a[1::2, 0::2, 1]
    m[1::2, 1::2] = a[1::2, 1::2, 2]
    return m

bayer = HERE / 'bayer_npy'
bayer.mkdir(exist_ok=True)
np.save(bayer / 'astronaut_rggb_clean.npy', mosaic(to_lin(np.asarray(photos['astronaut'], np.float32))))
np.save(bayer / 'astronaut_rggb_dark_noisy.npy', np.clip(mosaic(low_light_linear(photos['astronaut'], 0.12)), 0, 1))
print('done:', sum(1 for _ in HERE.rglob('*') if _.suffix in ('.png', '.npy')), 'files')
