"""Usage: python ops/deploy.py --root ROOT build|verify|apply|rollback|uninstall ..."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from uacf import deploy
from uacf.util import Fault,canonical
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('action',choices=['build','verify','apply','rollback','uninstall']);p.add_argument('--identity');p.add_argument('--expected');a=p.parse_args()
try:
 if a.action=='build':r=deploy.build(a.root)
 elif a.action=='verify':r=dict(deploy.verify(a.root,a.identity),ok=True)
 elif a.action=='uninstall':r=deploy.uninstall_release(a.root,a.expected)
 else:r=getattr(deploy,a.action)(a.root,a.identity,a.expected)
 print(canonical(r))
except Fault as e:print(canonical(e.result()));sys.exit(6)
