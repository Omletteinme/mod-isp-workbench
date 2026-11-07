"""Export bayer-v1 checkpoint to fixed-tile float32 and calibrated full-int8 LiteRT."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
import tensorflow as tf
from model import load_model
from train import pairs,read_pair
from isp import pack

p=argparse.ArgumentParser();p.add_argument('--checkpoint',default='models/mod_isp.pt');p.add_argument('--calibration-data',required=True);p.add_argument('--out',default='models/mod_isp_int8.tflite');p.add_argument('--tile',type=int,default=56);args=p.parse_args()
if args.tile%4 or args.tile<4: p.error('tile must be a positive multiple of 4')
model,meta=load_model(args.checkpoint);weights=model.state_dict();tile=args.tile
class ExportModel(tf.Module):
    def conv(self,x,name):
        w=weights[name+'.weight'].numpy().transpose(2,3,1,0);b=weights[name+'.bias'].numpy()
        return tf.nn.bias_add(tf.nn.conv2d(x,tf.constant(w),strides=1,padding='SAME'),tf.constant(b))
    def shuffle(self,x,r):
        # PyTorch channel order: output channel, then subpixel index.
        sh=tf.shape(x);n,h,w,c=sh[0],sh[1],sh[2],sh[3];out=c//(r*r)
        x=tf.reshape(x,[n,h,w,out,r,r]);x=tf.transpose(x,[0,1,4,2,5,3]);return tf.reshape(x,[n,h*r,w*r,out])
    @tf.function(input_signature=[tf.TensorSpec([1,tile//2,tile//2,4],tf.float32,name='bayer_rggb')])
    def __call__(self,x):
        a=x[:,0::2,0::2,:];b=x[:,0::2,1::2,:];c=x[:,1::2,0::2,:];d=x[:,1::2,1::2,:]
        z=tf.concat([(a+b+c+d)/2,(a-b+c-d)/2,(a+b-c-d)/2,(a-b-c+d)/2],-1)
        f=tf.nn.relu(self.conv(z,'enc.0'));f=tf.nn.relu(self.conv(f,'enc.2'))
        att=tf.reduce_mean(f,axis=[1,2],keepdims=True);att=tf.nn.relu(self.conv(att,'attn.1'));att=tf.sigmoid(self.conv(att,'attn.3'))
        spatial=tf.sigmoid(self.conv(f,'spatial'));z=self.conv(f*att*spatial,'dec');rgb=self.shuffle(self.shuffle(z,2),2)
        context=tf.broadcast_to(tf.reduce_mean(rgb,axis=[1,2],keepdims=True),tf.shape(rgb));color_input=tf.concat([rgb,context],axis=-1)
        color=self.conv(tf.nn.relu(self.conv(tf.nn.relu(self.conv(color_input,'color.0')),'color.2')),'color.4')
        return {'rgb':rgb+color}
module=ExportModel();concrete=module.__call__.get_concrete_function()
files=pairs(Path(args.calibration_data))
def representative():
    count=0
    for src,tgt in files:
        m,_=read_pair(src,tgt);h,w=m.shape
        for y in range(0,h-tile+1,tile):
            for x in range(0,w-tile+1,tile):
                sample=pack(m[y:y+tile,x:x+tile])[None].astype(np.float32)
                # Calibrate for exposure changes using training tiles only, including full sensor range.
                for gain in (1.0, 2.0, 4.0, 8.0, 16.0):
                    yield [np.clip(sample*gain,0,1)];count+=1
                    if count>=100:return
    if not count: raise ValueError('Calibration pairs must contain an image at least as large as tile')
converter=tf.lite.TFLiteConverter.from_concrete_functions([concrete],module);converter.optimizations=[tf.lite.Optimize.DEFAULT];converter.representative_dataset=representative;converter.target_spec.supported_ops=[tf.lite.OpsSet.TFLITE_BUILTINS_INT8];converter.inference_input_type=tf.int8;converter.inference_output_type=tf.int8
result=converter.convert();Path(args.out).parent.mkdir(parents=True,exist_ok=True);Path(args.out).write_bytes(result)
# Verify tensor quantization and compare the converted model against the actual PyTorch checkpoint.
interp=tf.lite.Interpreter(model_content=result);interp.allocate_tensors();ind=interp.get_input_details()[0];outd=interp.get_output_details()[0];sample=next(representative())[0]
scale,zero=ind['quantization'];quant=np.clip(np.round(sample/scale+zero),-128,127).astype(np.int8);interp.set_tensor(ind['index'],quant);interp.invoke();out=interp.get_tensor(outd['index']);oscale,ozero=outd['quantization'];out=(out.astype(np.float32)-ozero)*oscale
with torch.no_grad(): expected=model(torch.from_numpy(sample.transpose(0,3,1,2))).numpy().transpose(0,2,3,1)
report={'checkpoint':str(args.checkpoint),'calibration_data':str(args.calibration_data),'tile':tile,'bytes':len(result),'input_quantization':[float(scale),int(zero)],'output_quantization':[float(oscale),int(ozero)],'max_abs_error':float(np.max(np.abs(expected-out))),'mean_abs_error':float(np.mean(np.abs(expected-out))),'checkpoint_metadata':meta}
Path(args.out+'.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
