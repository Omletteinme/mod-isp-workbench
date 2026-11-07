"""Experimental adapter for Souza & Heidrich's 2023 MetaISP real_D checkpoint.

This is NOT Chen et al.'s 2024 MetaISP. It uses SIDD AsShotNeutral metadata,
patch-local BGR context, and a selected output device style; evaluate transfer
before using its predictions as training targets.
"""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

vendor=Path(__file__).resolve().parent/'third_party'/'metaisp2023'
if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
from models.teacher_net import MetaISPNet

class MetaISP2023(nn.Module):
 def __init__(self,weights,neutral=(0.55273438,1.,0.484375),target_device=1):
  super().__init__()
  opt=SimpleNamespace(illuminant=False,iso_exp=False,multi_device=True,query_emb=True,pre_ispnet_coord=False,attention='adaquery',attention_match='prod',depth=1,positional=True,latent_n=5)
  self.net=MetaISPNet(opt);state=torch.load(weights,map_location='cpu',weights_only=True)
  state={k.removeprefix('module.'):v for k,v in state.items()};self.net.load_state_dict(state,strict=True);self.net.eval()
  neutral=np.asarray(neutral,dtype=np.float32);gain=neutral[1]/neutral
  self.register_buffer('wb',torch.tensor([gain[2],1.,gain[0],1.]).reshape(1,4,1,1));self.target_device=target_device
 def forward(self,x):
  n,_,h,w=x.shape
  # Our input is [R,G1,G2,B], pretrained model consumes [B,G1,R,G2].
  raw=x[:,[3,1,0,2]]
  r,g1,g2,b=x[:,0:1],x[:,1:2],x[:,2:3],x[:,3:4]
  context=torch.cat([b,(g1+g2)/2,r],1)
  context=F.interpolate(context,size=(224,224),mode='bilinear',align_corners=False)
  xx=torch.linspace(-1+1/w,1-1/w,w,device=x.device);yy=torch.linspace(-1+1/h,1-1/h,h,device=x.device)
  y,xcoord=torch.meshgrid(yy,xx,indexing='ij'); coord=torch.stack((xcoord,y)).unsqueeze(0).expand(n,-1,-1,-1)
  xx2=torch.arange(1,w+1,device=x.device,dtype=x.dtype)*(2*torch.pi/w);yy2=torch.arange(1,h+1,device=x.device,dtype=x.dtype)*(2*torch.pi/h)
  y2,x2=torch.meshgrid(yy2,xx2,indexing='ij');coords=torch.stack((x2,y2)).unsqueeze(0).expand(n,-1,-1,-1)
  wb=self.wb.expand(n,-1,-1,-1);mobile=torch.full((n,),self.target_device,dtype=torch.long,device=x.device)
  return self.net(raw,context,wb,coord,mobile,False,coords,None,None)
