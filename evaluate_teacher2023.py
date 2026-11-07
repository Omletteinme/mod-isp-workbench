"""Evaluate the 2023 pretrained teacher on explicitly named SIDD input metadata."""
import argparse,json,platform,time
from pathlib import Path
import numpy as np, torch
from train import pairs,read_pair
from isp import pack,rgb_image
from app import metrics
from metaisp2023_adapter import MetaISP2023
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--checkpoint',default='models/metaisp_2023_real_D.pth');p.add_argument('--neutral',nargs=3,type=float,required=True);p.add_argument('--device-style',type=int,choices=[0,1,2],required=True);p.add_argument('--out',default='teacher2023_evaluation.json');a=p.parse_args()
m=MetaISP2023(a.checkpoint,neutral=a.neutral,target_device=a.device_style);rows=[]
for src,target in pairs(Path(a.data)):
 raw,rgb=read_pair(src,target);x=torch.from_numpy(pack(raw).transpose(2,0,1)).unsqueeze(0);start=time.perf_counter()
 with torch.no_grad():out=m(x)
 elapsed=(time.perf_counter()-start)*1000
 out=out.clamp(0,1).squeeze(0).permute(1,2,0).numpy();rows.append({'image':src.name,'latency_ms':round(elapsed,2),**metrics(rgb_image(out),rgb_image(rgb))})
r={'teacher':'Souza and Heidrich VMV 2023 MetaISP real_D; not Chen et al. IJCAI 2024','context':'patch-local resized BGR rather than full-frame; sensor metadata supplied explicitly','dataset':str(Path(a.data).resolve()),'neutral':a.neutral,'device_style':a.device_style,'parameters':sum(x.numel() for x in m.parameters()),'environment':platform.platform(),'results':rows}
Path(a.out).write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
