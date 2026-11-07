"""Official NILUT authors' three-style conditional MLP, sampled as an interpolated LUT.
Architecture and pretrained weights from https://github.com/mv-lab/nilut (MIT).
"""
from functools import lru_cache
from pathlib import Path
import numpy as np
import torch
from torch import nn
from PIL import Image

class CNILUT(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(6,256),nn.ReLU(),nn.Linear(256,256),nn.Tanh(),nn.Linear(256,256),nn.Tanh(),nn.Linear(256,3))
    def forward(self,x):return torch.clamp(self.net(x)+x[:,:3],0,1)

@lru_cache(maxsize=3)
def lut(style,size=33):
    model=CNILUT(); checkpoint=torch.load(Path(__file__).parent/'models/nilutx3style.pt',map_location='cpu',weights_only=True);model.load_state_dict(checkpoint['model']);model.eval()
    axis=np.linspace(0,1,size,dtype=np.float32);colors=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1).reshape(-1,3);cond=np.zeros_like(colors);cond[:,style]=1
    with torch.inference_mode():out=model(torch.from_numpy(np.concatenate([colors,cond],axis=1))).numpy()
    return out.reshape(size,size,size,3)

def apply_cnilut(image,style):
    table=lut(style); source=np.asarray(image,dtype=np.uint8); size=table.shape[0]
    result=np.empty_like(source)
    # Bound temporary memory for full-resolution camera images.
    for y in range(0,source.shape[0],128):
        a=source[y:y+128].astype(np.float32)/255; x=a*(size-1);lo=np.floor(x).astype(np.int32);hi=np.minimum(lo+1,size-1);frac=x-lo;out=np.zeros_like(a)
        for r in (0,1):
            for g in (0,1):
                for b in (0,1):
                    indexes=[hi[...,i] if v else lo[...,i] for i,v in enumerate((r,g,b))]
                    weights=np.prod(np.stack([frac[...,i] if v else 1-frac[...,i] for i,v in enumerate((r,g,b))],-1),-1)
                    out+=table[indexes[0],indexes[1],indexes[2]]*weights[...,None]
        result[y:y+128]=(np.clip(out,0,1)*255).astype(np.uint8)
    return Image.fromarray(result)
