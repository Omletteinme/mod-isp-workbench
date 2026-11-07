"""Prepare small scene-separated SIDD RAW/sRGB patch splits from downloaded MAT/PNG pairs."""
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from PIL import Image
root=Path('data'); src=root/'source'; rng=np.random.default_rng(42)
for name,shift in [('train',(0,1)),('test',(1,1))]:
    contents=loadmat(src/f'{name}.mat'); vals=[v for k,v in contents.items() if not k.startswith('__') and isinstance(v,np.ndarray) and v.ndim==2]
    if len(vals)!=1: raise ValueError(f'Expected one RAW mosaic in {name}.mat, got {len(vals)}')
    m=np.clip(vals[0].astype(np.float32),0,1); rgb=np.asarray(Image.open(src/f'{name}.png').convert('RGB'))
    if m.shape!=rgb.shape[:2]: raise ValueError(f'Unaligned dimensions {m.shape}, {rgb.shape}')
    sy,sx=shift;m=m[sy:,sx:];rgb=rgb[sy:,sx:];h,w=m.shape;h-=h%2;w-=w%2;m=m[:h,:w];rgb=rgb[:h,:w]
    print(name,'shape',m.shape,'min/max',float(m.min()),float(m.max()),flush=True)
    # Uniform grid creates non-overlapping 256x256 crops; one distinct source scene is held out.
    coords=[(y,x) for y in range(0,h-256,256) for x in range(0,w-256,256)];rng.shuffle(coords)
    for i,(y,x) in enumerate(coords[:(48 if name=='train' else 4)]):
        split=('calibration' if name=='train' and i>=40 else name)
        for folder in ['input','target']:(root/split/folder).mkdir(parents=True,exist_ok=True)
        stem=f'{name}_{i:03d}';np.save(root/split/'input'/f'{stem}.npy',m[y:y+256,x:x+256]);Image.fromarray(rgb[y:y+256,x:x+256]).save(root/split/'target'/f'{stem}.png')
print('Prepared 40 train, 8 calibration, 4 test patches, with disjoint source scenes.')
