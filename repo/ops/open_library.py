"""User-invoked local entry. No provider, agent, archive job or paid call."""
import argparse,json,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from uacf.state import State
from uacf.browser_session import launch_ticket

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
 root=Path(a.root).resolve();s=State(root);port=s.config['port'];url=f'http://127.0.0.1:{port}/'
 def health():
  try:
   with urllib.request.urlopen(url+'health',timeout=2) as r:v=json.load(r)
  except Exception:return False
  if v.get('authority_id')!=s.authority:raise RuntimeError('Port belongs to another authority; no pairing issued')
  return bool(v.get('ok'))
 if not health():
  # A detached Windows service must not inherit communicate() pipe handles.
  # Otherwise a successful cold start can leave the caller waiting forever.
  subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'repo/ops/manage.ps1'),'-Action','start','-Root',str(root)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(40):
   if health():break
   time.sleep(.25)
  else:raise RuntimeError('Local service did not become ready')
 if a.check:
  print(json.dumps({'ok':True,'authority_id':s.authority,'port':port,'provider_calls':0}));return
 # Fragment is removed by the page before exchange; never an API credential.
 if not webbrowser.open(url+'#pair='+launch_ticket(s,port),new=2):raise RuntimeError('Browser could not be opened')

if __name__=='__main__':
 try:main()
 except Exception as e:print('UACF entry failed: '+str(e));sys.exit(1)
