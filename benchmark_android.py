"""Run user-supplied LiteRT benchmark binary and vendor NPU delegate on an attached Android device."""
import argparse,datetime,hashlib,json,shutil,subprocess,sys
from pathlib import Path

def run(args,check=True):
 p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if check and p.returncode: raise SystemExit(f'Command failed ({p.returncode}): {args[0]}\n{p.stdout}')
 return p.stdout
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary',required=True,help='Android arm64 benchmark_model executable')
p.add_argument('--delegate',required=True,help='Android vendor NPU delegate .so compatible with the phone')
p.add_argument('--model',default='models/mod_isp_int8.tflite');p.add_argument('--serial',required=True);p.add_argument('--delegate-options',default='');p.add_argument('--output',default='mobile_benchmark.json');a=p.parse_args()
if not shutil.which('adb'):sys.exit('adb not found. Install Android platform-tools and connect an authorized device.')
for f in [a.binary,a.delegate,a.model]:
 if not Path(f).is_file():sys.exit(f'File not found: {f}')
adb=['adb','-s',a.serial];devices=run(['adb','devices','-l'])
if not any(line.split()[0]==a.serial and len(line.split())>1 and line.split()[1]=='device' for line in devices.splitlines() if line.strip()):sys.exit('Specified device is not connected and authorized.\n'+devices)
props={key:run(adb+['shell','getprop',key]).strip() for key in ['ro.product.manufacturer','ro.product.model','ro.board.platform','ro.build.version.release','ro.build.version.sdk']}
remote='/data/local/tmp/modisp_benchmark';run(adb+['shell','mkdir','-p',remote]);
for f,n in [(a.binary,'benchmark_model'),(a.delegate,'delegate.so'),(a.model,'model.tflite')]:run(adb+['push',f,f'{remote}/{n}'])
run(adb+['shell','chmod','755',f'{remote}/benchmark_model'])
common=[f'{remote}/benchmark_model',f'--graph={remote}/model.tflite','--warmup_runs=20','--num_runs=100','--enable_op_profiling=true']
cpu_run=subprocess.run(adb+['shell']+common,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
cpu=cpu_run.stdout
flags=[f'--external_delegate_path={remote}/delegate.so']
if a.delegate_options:flags.append('--external_delegate_options='+a.delegate_options)
delegate_run=subprocess.run(adb+['shell']+common+flags,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
accelerated=delegate_run.stdout
report={'device':props,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model_sha256':hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),'delegate_sha256':hashlib.sha256(Path(a.delegate).read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(Path(a.binary).read_bytes()).hexdigest(),'runs':100,'warmup_runs':20,'cpu_exit_code':cpu_run.returncode,'delegate_exit_code':delegate_run.returncode,'cpu_log':cpu,'delegate_log':accelerated,'verification':'Unverified: inspect delegate log and per-op profiling to confirm NPU delegation, unsupported operations and CPU fallback before reporting NPU performance.'}
Path(a.output).write_text(json.dumps(report,indent=2));print('Saved',a.output);print(report['verification'])
