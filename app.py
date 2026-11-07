import base64, io, os, platform, sys, time, tracemalloc
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from flask import Flask, request, jsonify, render_template
from isp import decode_bayer, white_balance, demosaic, mosaic_rgb, pack, rgb_image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
ROOT = Path(__file__).parent
CHECKPOINT = ROOT / 'models' / 'mod_isp.pt'
RGB_CHECKPOINT = ROOT / 'models' / 'sidd_srgb_nafnet_lite.pt'
RGB_MODEL_CACHE = {}
LPIPS_MODEL = None
RAW_EXT = {'.dng','.nef','.cr2','.cr3','.arw','.raf','.rw2','.npy'}

def samsung_repo_path():
    configured=os.environ.get('MOD_ISP_SAMSUNG_REPO')
    candidates=[]
    if configured: candidates.append(Path(configured).expanduser())
    candidates.extend([ROOT.parent.parent / 'work' / 'modular_neural_isp',
                       ROOT / 'third_party' / 'modular_neural_isp'])
    return next((path for path in candidates if path.exists()),None)

def model_status():
    try:
        import torch
        if not CHECKPOINT.exists(): return {'available':False,'message':'No trained checkpoint found. Classical processing is ready.'}
        from model import load_model
        model, metadata = load_model(CHECKPOINT)
        return {'available':True,'message':'Trained checkpoint loaded','parameters':sum(p.numel() for p in model.parameters()),'size_kb':round(CHECKPOINT.stat().st_size/1024,1),'metadata':metadata}
    except Exception as e: return {'available':False,'message':f'Model unavailable: {str(e)}'}

def rgb_model_status():
    if not RGB_CHECKPOINT.exists():
        return {'available':False,'message':'No trained sRGB denoiser found.'}
    try:
        import torch
        repo = samsung_repo_path()
        if repo is None: raise FileNotFoundError('Samsung NAFNet model definition is missing.')
        checkpoint = torch.load(RGB_CHECKPOINT, map_location='cpu', weights_only=True)
        device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
        model,_=load_rgb_denoiser(device)
        return {'available':True,'message':'SIDD-CC sRGB denoiser available',
                'parameters':sum(p.numel() for p in model.parameters()),
                'size_kb':round(RGB_CHECKPOINT.stat().st_size/1024,1),
                'best_epoch':checkpoint.get('best_epoch'), 'dataset':'SIDD-CC SRGB'}
    except Exception as e: return {'available':False,'message':f'sRGB model unavailable: {str(e)}'}

def decode(file):
    ext=Path(file.filename or '').suffix.lower()
    if ext in RAW_EXT:
        m, meta=decode_bayer(file.read(),file.filename)
        m=white_balance(m,meta['gains'])
        h,w=m.shape; m=m[:h-h%2,:w-w%2]
        if min(m.shape)<2: raise ValueError('Image must be at least 2 by 2 pixels.')
        preview=meta.get('raw_render')
        if preview is None:
            preview=Image.fromarray(np.uint8(np.clip(linear_to_srgb(demosaic(m)),0,1)*255))
        meta['raw_ccm_available']=bool(meta.get('camera_matrix_available',False))
        return preview,meta['kind'],m,'bayer',meta
    if ext not in {'.png','.jpg','.jpeg','.webp','.tif','.tiff'}: raise ValueError('Use a supported RAW, NPY, JPEG, PNG, WebP, or TIFF image.')
    try:
        im=ImageOps.exif_transpose(Image.open(file.stream)); im.load(); im=im.convert('RGB')
        if min(im.size)<2: raise ValueError('Image must be at least 2 by 2 pixels.')
        original_size=im.size
        if im.width*im.height>MAX_IMAGE_PIXELS:
            scale=(MAX_IMAGE_PIXELS/(im.width*im.height))**0.5
            size=(max(2,int(im.width*scale)//2*2),max(2,int(im.height*scale)//2*2))
            im=im.resize(size,Image.Resampling.LANCZOS)
        kind='Rendered RGB / sRGB image · RGB-compatible enhancement path'
        if im.size!=original_size: kind+=f' · resized from {original_size[0]}×{original_size[1]} to {im.width}×{im.height} (16 MP processing cap)'
        return im,kind,None,'rgb',{}
    except Exception: raise ValueError('The image could not be read. Try another file.')

def encode(im):
    b=io.BytesIO(); im.convert('RGB').save(b,format='JPEG',quality=92,optimize=True); return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()

def srgb_to_linear(a):
    return np.where(a <= 0.04045, a/12.92, ((a+0.055)/1.055)**2.4)

def linear_to_srgb(a):
    a=np.clip(a,0,1)
    return np.where(a <= 0.0031308, 12.92*a, 1.055*np.power(a,1/2.4)-0.055)

def exposure_gain(im, mode, strength):
    """Estimate exposure from rendered RGB luminance, without inventing sensor RAW."""
    a=np.asarray(im,dtype=np.float32)/255
    lin=srgb_to_linear(a)
    y=lin @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
    measured=float(np.percentile(y,55))
    target=0.050 if mode=='human' else 0.030
    ev=float(np.clip(np.log2(target/max(measured,1e-5)),-1.0,4.5))*strength
    return 2.0**ev

def finish_rgb(im, mode, strength=1.0, style=None, apply_exposure=True, sharpen=True):
    """sRGB-safe color/tone finishing for already rendered RGB inputs."""
    a=np.asarray(im,dtype=np.float32)/255
    lin=srgb_to_linear(a)
    if apply_exposure:
        gain=exposure_gain(im,mode,strength)
        exposed=np.maximum(lin*gain,0)
        y=exposed @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
        # White-point Reinhard shoulder lifts dark detail while rolling highlights smoothly.
        white=max(float(np.percentile(y,99.7)),0.12)
        yd=np.clip(y*(1+y/(white*white))/(1+y),0,1)
        ratio=yd/np.maximum(y,1e-6)
        lin=np.clip(exposed*ratio[...,None],0,1)
    out=Image.fromarray(np.uint8(np.clip(linear_to_srgb(lin),0,1)*255))
    if style is not None:
        from cnilut import apply_cnilut
        out=apply_cnilut(out,style)
    return out.filter(ImageFilter.UnsharpMask(radius=1.15,percent=int((48 if mode=='human' else 30)*strength),threshold=3)) if sharpen else out

def classical_rgb(im, mode, strength, style=None):
    """Classical degraded-RGB path: adaptive exposure, conservative denoise, tone and detail."""
    gain=exposure_gain(im,mode,strength)
    a=np.asarray(im,dtype=np.float32)/255
    lin=srgb_to_linear(a)*gain
    y=lin @ np.array([0.2126,0.7152,0.0722],dtype=np.float32)
    white=max(float(np.percentile(y,99.7)),0.12)
    yd=np.clip(y*(1+y/(white*white))/(1+y),0,1)
    lin=np.clip(lin*(yd/np.maximum(y,1e-6))[...,None],0,1)
    base=Image.fromarray(np.uint8(np.clip(linear_to_srgb(lin),0,1)*255))
    # A small bilateral filter smooths chroma/noise while retaining high-contrast edges.
    try:
        import cv2
        arr=np.asarray(base)
        den=cv2.bilateralFilter(arr,5,18,2.0)
        base=Image.blend(base,Image.fromarray(den),min(0.28,0.12*strength))
    except ImportError:
        base=Image.blend(base,base.filter(ImageFilter.GaussianBlur(0.45)),min(0.14,0.06*strength))
    if style is not None:
        from cnilut import apply_cnilut
        base=apply_cnilut(base,style)
    return base.filter(ImageFilter.UnsharpMask(radius=1.15,percent=int((48 if mode=='human' else 30)*strength),threshold=3))

def classical_bayer(mosaic, mode, strength, style=None):
    # Bayer demosaic returns linear RGB; render once, then perform the perceptual stages.
    rgb=np.clip(linear_to_srgb(demosaic(mosaic)),0,1)
    return finish_rgb(Image.fromarray(np.uint8(rgb*255)),mode,strength,style,apply_exposure=True)

def load_rgb_denoiser(device):
    import torch
    key=str(device)
    if key in RGB_MODEL_CACHE: return RGB_MODEL_CACHE[key],torch
    repo=samsung_repo_path()
    if repo is None: raise FileNotFoundError('Samsung NAFNet model definition is missing.')
    if str(repo) not in sys.path: sys.path.insert(0,str(repo))
    from denoising.nafnet_arch import NAFNet
    checkpoint=torch.load(RGB_CHECKPOINT,map_location='cpu',weights_only=True)
    model=NAFNet(**checkpoint['config']);model.load_state_dict(checkpoint['state_dict'],strict=True)
    model.to(device).eval()
    RGB_MODEL_CACHE[key]=model
    return model,torch

def denoise_rgb_tiles(image, hybrid=False, route_fraction=0.5, tile=512, overlap=64,
                      precomputed=None, return_cache=False):
    """Run the SIDD sRGB denoiser on RGB tiles, optionally reusing learned tiles."""
    import torch
    device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    model=None if precomputed is not None else load_rgb_denoiser(device)[0]
    src=np.asarray(image,dtype=np.float32)/255
    h,w=src.shape[:2];step=tile-overlap
    coords=[(y,x,min(y+tile,h),min(x+tile,w)) for y in list(range(0,max(h-tile,0)+1,step))+([max(h-tile,0)] if h>tile and (h-tile)%step else []) for x in list(range(0,max(w-tile,0)+1,step))+([max(w-tile,0)] if w>tile and (w-tile)%step else [])]
    coords=list(dict.fromkeys(coords))
    if not coords: coords=[(0,0,h,w)]
    selected=set(range(len(coords)))
    if hybrid:
        # Robust high-pass MAD is a useful routing heuristic for RGB sensor noise;
        # it is deliberately not labeled as the calibrated Bayer gate.
        from scipy.ndimage import gaussian_filter
        scores=[]
        for i,(y,x,y1,x1) in enumerate(coords):
            patch=src[y:y1,x:x1].mean(axis=2)
            residual=patch-gaussian_filter(patch,sigma=1.0)
            scores.append((float(np.median(np.abs(residual))),i))
        count=max(1,int(np.ceil(len(coords)*float(route_fraction))))
        selected={i for _,i in sorted(scores,key=lambda item:(-item[0],item[1]))[:count]}
    acc=np.zeros_like(src);weight_sum=np.zeros((h,w,1),np.float32);routed=0
    routed_coords=[(i,*coords[i]) for i in sorted(selected)]
    tile_cache={}
    for start in range(0,len(routed_coords),4):
        group=routed_coords[start:start+4]
        if precomputed is not None:
            preds=[precomputed[(y,x)] for _,y,x,_,_ in group]
        else:
            patches=[src[y:y1,x:x1] for _,y,x,y1,x1 in group]
            max_h=max(p.shape[0] for p in patches);max_w=max(p.shape[1] for p in patches)
            batch=[]
            for patch in patches:
                ph,pw=patch.shape[:2]
                # All coordinates share dimensions except at image edges; replicate those borders.
                pad_h=max_h-ph;pad_w=max_w-pw
                padded=np.pad(patch,((0,pad_h),(0,pad_w),(0,0)),mode='reflect') if pad_h or pad_w else patch
                batch.append(padded.transpose(2,0,1))
            ten=torch.from_numpy(np.ascontiguousarray(np.stack(batch))).to(device)
            pad_h=(-ten.shape[-2])%4;pad_w=(-ten.shape[-1])%4
            if pad_h or pad_w: ten=torch.nn.functional.pad(ten,(0,pad_w,0,pad_h),mode='reflect')
            with torch.inference_mode():
                preds=model(ten).clamp(0,1).cpu().numpy().transpose(0,2,3,1)
        for pred,(i,y,x,y1,x1) in zip(preds,group):
            ph,pw=y1-y,x1-x;pred=pred[:ph,:pw]
            tile_cache[(y,x)]=pred.astype(np.float16,copy=True) if return_cache else pred
            # Smooth overlap seams and keep the outer image boundary fully weighted.
            wy=np.ones(ph,np.float32);wx=np.ones(pw,np.float32);edge=min(overlap//2,ph//4,pw//4)
            if edge>0:
                ramp=np.linspace(0,1,edge,endpoint=False,dtype=np.float32)
                ramp=0.5-0.5*np.cos(np.pi*ramp)
                if y>0: wy[:edge]=ramp
                if y1<h: wy[-edge:]=ramp[::-1]
                if x>0: wx[:edge]=ramp
                if x1<w: wx[-edge:]=ramp[::-1]
            weight=(wy[:,None]*wx[None,:])[...,None]
            acc[y:y1,x:x1]+=pred*weight;weight_sum[y:y1,x:x1]+=weight;routed+=1
    pred=acc/np.maximum(weight_sum,1e-8)
    if hybrid:
        coverage=np.clip(weight_sum,0,1)
        out=src*(1-coverage)+pred*coverage
    else: out=pred
    result=(Image.fromarray(np.uint8(np.clip(out,0,1)*255)),round(100*routed/max(len(coords),1),1))
    return (*result,tile_cache) if return_cache else result

def learned(mosaic, hybrid=False, threshold=None, route_fraction=None):
    import torch
    from model import load_model
    model,_=load_model(CHECKPOINT)
    if hybrid and threshold is None and route_fraction is None:
        try:
            import json
            config=json.loads((ROOT / 'models' / 'gate.json').read_text())
            if config.get('mode')=='relative_rank': route_fraction=float(config['route_fraction'])
            else: threshold=float(config['variance_threshold'])
        except (OSError, ValueError, KeyError): threshold=0.006
    h,w=mosaic.shape
    # The restoration network is trained against rendered sRGB targets. Keep
    # the classical side of a Hybrid blend in the same display-referred space.
    base=np.clip(linear_to_srgb(demosaic(mosaic)),0,1)
    out=base.copy(); tile=56; halo=8; routed=0; total=0
    selected=None
    if hybrid and route_fraction is not None:
        if not 0<=route_fraction<=1: raise ValueError('Routing fraction must be between 0 and 1.')
        blocks=[]
        for yy in range(0,h,tile):
            for xx in range(0,w,tile):
                block=mosaic[yy:min(yy+tile,h),xx:min(xx+tile,w)]
                # Rank contrast relative to illumination. This is a compute budget, not a noise estimate.
                score=float(block.var())/(float(block.mean())**2+1e-6)
                blocks.append((score,yy,xx))
        count=int(np.ceil(len(blocks)*route_fraction))
        selected={(yy,xx) for _,yy,xx in sorted(blocks,key=lambda item:(-item[0],item[1],item[2]))[:count]}
    # Evaluate selected tiles only, with a halo for convolution context and smooth blending.
    with torch.no_grad():
        for y in range(0,h,tile):
            for x in range(0,w,tile):
                y1=min(y+tile,h);x1=min(x+tile,w);total+=1
                block=mosaic[y:y1,x:x1]
                if hybrid and selected is not None and (y,x) not in selected: continue
                if hybrid and selected is None and float(block.var())<=threshold: continue
                routed+=1
                y0=max(0,y-halo);x0=max(0,x-halo);ey=min(h,y1+halo);ex=min(w,x1+halo)
                y0-=y0%2;x0-=x0%2;ey-=ey%2;ex-=ex%2
                inp=pack(mosaic[y0:ey,x0:ex]);tensor=torch.from_numpy(inp.transpose(2,0,1)).unsqueeze(0)
                pred=model(tensor).clamp(0,1).squeeze(0).permute(1,2,0).numpy()
                yy=y-y0;xx=x-x0;piece=pred[yy:yy+y1-y,xx:xx+x1-x]
                out[y:y1,x:x1]=piece
    if hybrid:
        # Blend the routed region once with a broad transition. Local four-pixel
        # fades at every tile edge created a conspicuous checkerboard.
        mask=np.zeros((h,w),np.float32)
        for y,x in selected:
            mask[y:min(y+tile,h),x:min(x+tile,w)]=1
        from scipy.ndimage import gaussian_filter
        alpha=np.clip(gaussian_filter(mask,sigma=max(tile/5,1)),0,1)[...,None]
        out=out*alpha+base*(1-alpha)
    return rgb_image(out),round(100*routed/max(total,1),1)

def metrics(im, ref):
    global LPIPS_MODEL
    if im.size != ref.size: raise ValueError('Reference dimensions must match the input image.')
    a=np.asarray(im,dtype=np.float64)/255; b=np.asarray(ref,dtype=np.float64)/255
    mse=np.mean((a-b)**2); result={'psnr':round(float(-10*np.log10(mse)),2) if mse else '∞'}
    try:
        from skimage.metrics import structural_similarity
        from skimage.color import rgb2lab, deltaE_ciede2000
        result['ssim']=round(float(structural_similarity(a,b,channel_axis=2,data_range=1)),4) if min(a.shape[:2])>=7 else None
        result['delta_e']=round(float(deltaE_ciede2000(rgb2lab(a),rgb2lab(b)).mean()),2)
    except ImportError: result.update(ssim=None,delta_e=None)
    try:
        import torch, lpips
        if LPIPS_MODEL is None: LPIPS_MODEL=lpips.LPIPS(net='squeeze',verbose=False).eval()
        x=torch.from_numpy(a.transpose(2,0,1)).float().unsqueeze(0)*2-1
        y=torch.from_numpy(b.transpose(2,0,1)).float().unsqueeze(0)*2-1
        with torch.no_grad(): result['lpips']=round(float(LPIPS_MODEL(x,y).item()),4)
    except Exception: result['lpips']=None
    return result

@app.get('/')
def index(): return render_template('index.html')
@app.get('/api/status')
def status(): return jsonify(bayer=model_status(),rgb=rgb_model_status())
@app.post('/api/process')
def process():
    try:
        if 'image' not in request.files: raise ValueError('Choose an image to process.')
        im, kind, mosaic, input_type,input_meta=decode(request.files['image'])
        if im.width*im.height>MAX_IMAGE_PIXELS: raise ValueError('This RAW/NPY image exceeds the 16 megapixel processing limit. Use a lower-resolution sensor export.')
        style_raw=request.form.get('style','off')
        if style_raw not in ('off','0','1','2'): raise ValueError('Invalid CNILUT style.')
        style=None if style_raw=='off' else int(style_raw)
        mode=request.form.get('mode','human'); strength=float(request.form.get('strength','1')); strength=max(0,min(2,strength))
        reference=None
        if 'reference' in request.files and request.files['reference'].filename: reference,_,_,_,_=decode(request.files['reference'])
        tracemalloc.start(); start=time.perf_counter()
        result=classical_rgb(im,mode,strength,style)
        elapsed=(time.perf_counter()-start)*1000; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        outputs={'classical':{'image':encode(result),'latency_ms':round(elapsed,1),'memory_mb':round(peak/1048576,2),'metrics':metrics(result,reference) if reference else None}}
        camera_managed_raw=input_type=='bayer' and input_meta.get('raw_render') is not None
        status=rgb_model_status() if input_type=='rgb' else model_status()
        if status['available']:
            rgb_model_input=None
            rgb_tile_cache=None
            for name in ['learned','hybrid']:
                tracemalloc.start(); start=time.perf_counter()
                reused_inference=False
                if input_type=='bayer':
                    # Keep learned RAW processing in the sensor domain. LibRaw's
                    # camera-managed render remains the conventional baseline.
                    out, routed=learned(mosaic, hybrid=name=='hybrid')
                    out=finish_rgb(out,mode,strength,style,apply_exposure=False)
                else:
                    # Rendered RGB uploads use the separately trained SIDD-CC
                    # sRGB denoiser; its benchmark does not stand in for RAW ISP.
                    if rgb_model_input is None:
                        rgb_model_input=finish_rgb(im,mode,strength,None,apply_exposure=True,sharpen=False)
                    if name=='learned':
                        out,routed,rgb_tile_cache=denoise_rgb_tiles(rgb_model_input,return_cache=True)
                    else:
                        out,routed=denoise_rgb_tiles(rgb_model_input,hybrid=True,precomputed=rgb_tile_cache)
                        reused_inference=True
                    out=finish_rgb(out,mode,0,style,apply_exposure=False)
                elapsed=(time.perf_counter()-start)*1000; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
                outputs[name]={'image':encode(out),'latency_ms':round(elapsed,1),'memory_mb':round(peak/1048576,2),'routed':routed,'reused_inference':reused_inference,'metrics':metrics(out,reference) if reference else None}
        processing_note=('Camera Bayer mosaic → MOD-ISP learned RGB reconstruction; LibRaw camera render is the classical baseline.' if camera_managed_raw else ('Normalized Bayer mosaic → MOD-ISP learned RGB reconstruction' if input_type=='bayer' else 'Rendered sRGB → SIDD-CC sRGB denoiser'))
        return jsonify(input=encode(im),width=im.width,height=im.height,input_kind=kind,input_type=input_type,camera_managed_raw=bool(camera_managed_raw),raw_integrity=input_meta.get('raw_integrity'),outputs=outputs,model=status,processing_note=processing_note,environment=f'{platform.system()} {platform.machine()} · Python {platform.python_version()}')
    except (ValueError, OSError) as e: return jsonify(error=str(e)),400
    except Exception as e: app.logger.exception('Processing failed'); return jsonify(error=f'Processing failed: {e}'),500

if __name__=='__main__': app.run(host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','5050')),debug=False)
