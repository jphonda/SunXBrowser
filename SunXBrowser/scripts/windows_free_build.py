"""Native Windows Chromium builds on measured standard public GitHub runners.
Compile checkpoints permit bounded continuation without paid runners or caches.
"""
import argparse, importlib.util, json, os, shutil, signal, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'upstream.json').read_text())
WORK=Path('D:/sunx'); CHECKOUT=WORK/'chromium'; SRC=CHECKOUT/'src'; OUT=SRC/'out/SunXBrowser'; DIST=Path(os.environ.get('SUNX_DIST',str(ROOT/'dist-windows'))).resolve()
ENV=os.environ.copy(); ENV.update(DEPOT_TOOLS_UPDATE='0',DEPOT_TOOLS_WIN_TOOLCHAIN='0',PYTHONUTF8='1',TEMP=str(WORK/'tmp'),TMP=str(WORK/'tmp'),CIPD_CACHE_DIR=str(WORK/'cache/cipd'),VPYTHON_VIRTUALENV_ROOT=str(WORK/'cache/vpython'),XDG_CACHE_HOME=str(WORK/'cache'))
phase='preflight';log=None;started=time.monotonic()

def state(status,detail=''):
 (DIST/'state.json').write_text(json.dumps(dict(state=status,phase=phase,detail=detail,revision=CONFIG['revision'],version='157.0.8100.0',updated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),free_gib=round(shutil.disk_usage(WORK).free/1024**3,1)),indent=2)+'\n')

def command(args,cwd=WORK,timeout=None,compile_step=False):
 resolved=shutil.which(str(args[0]),path=ENV['PATH']) or str(args[0]);cmd=[resolved,*map(str,args[1:])]
 if resolved.lower().endswith(('.bat','.cmd')): cmd=[os.environ.get('COMSPEC','cmd.exe'),'/c',*cmd]
 print('RUN',*map(str,args),flush=True);start=time.monotonic();last=0
 with log.open('a',encoding='utf8') as f:
  f.write('\nRUN '+str(args)+'\n');f.flush()
  p=subprocess.Popen(cmd,cwd=cwd,env=ENV,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
  while p.poll() is None:
   elapsed=time.monotonic()-start
   if compile_step and ((timeout and elapsed>timeout) or shutil.disk_usage(WORK).free<18*1024**3):
    try: p.send_signal(signal.CTRL_BREAK_EVENT);p.wait(timeout=20)
    except (OSError,subprocess.TimeoutExpired):
     subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     subprocess.run(['taskkill','/IM','siso.exe','/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     p.wait()
    return False
   if timeout and elapsed>timeout and not compile_step:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);raise RuntimeError('Phase exceeded timeout: '+phase)
   if elapsed-last>=60:
    last=elapsed;state('running');print(f'{phase}: {elapsed/60:.0f} minutes; {shutil.disk_usage(WORK).free/1024**3:.1f} GiB free',flush=True)
    if compile_step:
     with log.open('rb') as tail:
      tail.seek(max(0,log.stat().st_size-3000));print(tail.read().decode('utf8',errors='replace').splitlines()[-1],flush=True)
   time.sleep(5)
 if p.returncode:
  with log.open('rb') as tail:
   tail.seek(max(0,log.stat().st_size-12000));print(tail.read().decode('utf8',errors='replace'),flush=True)
  raise RuntimeError(f'Command failed ({p.returncode}): {args[0]}')
 return True

def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def output(key,value):
 if os.environ.get('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'{key}={value}\n')

def main():
 global phase,log
 parser=argparse.ArgumentParser();parser.add_argument('--resume',type=Path);parser.add_argument('--compile-seconds',type=int,default=14400);args=parser.parse_args()
 if os.name!='nt':raise RuntimeError('This entry point requires native Windows')
 for p in [WORK,WORK/'tmp',WORK/'cache',DIST,CHECKOUT]:p.mkdir(parents=True,exist_ok=True)
 log=DIST/'build.log';state('running')
 if shutil.disk_usage(WORK).free<100*1024**3:raise RuntimeError('Standard runner D: requires at least 100 GiB free; no paid runner fallback')
 phase='fetch depot_tools';state('running');depot=WORK/'depot_tools'
 command(['git','init',depot]);command(['git','remote','add','origin','https://chromium.googlesource.com/chromium/tools/depot_tools.git'],depot)
 command(['git','fetch','--depth=1','--no-tags','origin',CONFIG['depot_tools_revision']],depot,timeout=900);command(['git','checkout','--detach','FETCH_HEAD'],depot)
 ENV['PATH']=str(depot)+os.pathsep+ENV['PATH']
 phase='bootstrap tools';state('running');command([depot/'bootstrap/win_tools.bat'],depot,timeout=1800)
 phase='fetch Chromium';state('running');command(['gclient','config',CONFIG['repository'],'--unmanaged'],CHECKOUT)
 SRC.mkdir();command(['git','init'],SRC);command(['git','remote','add','origin',CONFIG['repository']],SRC)
 command(['git','fetch','--depth=1','--no-tags','origin',CONFIG['revision']],SRC,timeout=1800);command(['git','checkout','--detach',CONFIG['revision']],SRC)
 phase='sync Windows dependencies';state('running');command(['gclient','sync','-D','--no-history','--shallow','--jobs','4'],CHECKOUT,timeout=5400)
 phase='apply branding and Secure DNS';state('running');module('build').apply_overlay(SRC)
 if args.resume:
  archives=sorted(args.resume.glob('out.7z*'))
  if not archives:raise RuntimeError('Resume checkpoint archive missing')
  phase='restore compile checkpoint';state('running');command(['7z','x',archives[0],'-y',f'-o{SRC}'],timeout=2400)
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'args.gn').write_text('is_debug = false\nis_component_build = false\nsymbol_level = 0\nblink_symbol_level = 0\nv8_symbol_level = 0\nis_chrome_branded = false\nuse_remoteexec = false\ntarget_cpu = "x64"\n')
 phase='generate build';state('running');command(['gn','gen','out/SunXBrowser'],SRC,timeout=900)
 phase='compile Chromium x64 (3 jobs)';state('running')
 if not command(['autoninja','-C','out/SunXBrowser','-j','3','chrome'],SRC,timeout=max(600,min(args.compile_seconds,285*60-(time.monotonic()-started))),compile_step=True):
  phase='save compile checkpoint';state('running');command(['7z','a','-t7z','-mx=1','-mmt=2','-v1024m',DIST/'out.7z','out'],SRC,timeout=2400)
  state('checkpoint','Compile budget ended; continuation can reuse output');output('checkpoint','true');return
 phase='browser startup test';state('running');module('ci_build').smoke(CHECKOUT,'x64',DIST,ENV)
 phase='package Windows installer';state('running');os.environ.update(ENV);command([sys.executable,ROOT/'scripts/package.py',CHECKOUT,'--dist',DIST,'--cpu','x64'],ROOT,timeout=1800)
 phase='test installed payload';state('running')
 installers=list(DIST.glob('*.exe'));assert len(installers)==1
 command([installers[0],'/S'],timeout=300)
 installed=Path(os.environ['LOCALAPPDATA'])/'Programs/SunXBrowser/chrome.exe'
 if not installed.exists():raise RuntimeError('Installer did not create chrome.exe')
 import tempfile
 with tempfile.TemporaryDirectory(dir=WORK/'tmp') as profile:
  result=subprocess.run([str(installed),'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',f'--user-data-dir={profile}','--dump-dom','data:text/html,<p>installed-sunx-ok</p>'],capture_output=True,text=True,env=ENV,timeout=120)
  (DIST/'installed-smoke.log').write_text(result.stdout+'\n'+result.stderr)
  if result.returncode or 'installed-sunx-ok' not in result.stdout:raise RuntimeError('Installed browser startup failed')
 phase='complete';state('complete','Windows Chromium installer and installed payload startup verified');output('checkpoint','false')

if __name__=='__main__':
 try:main()
 except Exception as e:
  if DIST.exists() and WORK.exists():state('failed',str(e))
  print('BUILD FAILED:',e,flush=True);sys.exit(1)
