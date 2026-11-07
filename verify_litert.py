"""Compare PyTorch and quantized LiteRT on held-out Bayer tiles."""
import argparse,json,time
from pathlib import Path
import numpy as np
import tensorflow as tf
import torch
from model import load_model
from isp import pack
from train import pairs,read_pair
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--checkpoint',default='models/mod_isp.pt');p.add_argument('--model',default='models/mod_isp_int8.tflite');p.add_argument('--out',default='litert_verification.json');a=p.parse_args()
model,_=load_model(a.checkpoint);interpreter=tf.lite.Interpreter(model_path=a.model);interpreter.allocate_tensors();i=interpreter.get_input_details()[0];o=interpreter.get_output_details()[0];iscale,izero=i['quantization'];oscale,ozero=o['quantization'];tile=i['shape'][1]*2;rows=[]
for src,tgt in pairs(Path(a.data)):
 m,_=read_pair(src,tgt)
 for y,x in [(0,0),(m.shape[0]//2//2*2,m.shape[1]//2//2*2)]:
  if y+tile>m.shape[0] or x+tile>m.shape[1]:continue
  sample=pack(m[y:y+tile,x:x+tile])[None];unclipped=sample/iscale+izero;q=np.clip(np.round(unclipped),-128,127).astype(np.int8)
  start=time.perf_counter();interpreter.set_tensor(i['index'],q);interpreter.invoke();elapsed=(time.perf_counter()-start)*1000;out=(interpreter.get_tensor(o['index']).astype(np.float32)-ozero)*oscale
  with torch.no_grad(): ref=model(torch.from_numpy(sample.transpose(0,3,1,2))).numpy().transpose(0,2,3,1)
  rows.append({'image':src.name,'tile':[int(y),int(x)],'input_clipped_percent':float(np.mean((unclipped < -128)|(unclipped > 127))*100),'mean_abs_error':float(np.mean(np.abs(ref-out))),'max_abs_error':float(np.max(np.abs(ref-out))),'cpu_inference_ms':round(elapsed,3)})
report={'source':str(Path(a.data).resolve()),'comparison':'PyTorch float32 vs full-int8 LiteRT on held-out tiles; no mobile NPU measured','rows':rows,'mean_abs_error':float(np.mean([r['mean_abs_error'] for r in rows])),'mean_input_clipped_percent':float(np.mean([r['input_clipped_percent'] for r in rows]))};Path(a.out).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
