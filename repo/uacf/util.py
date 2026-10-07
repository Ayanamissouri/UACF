import hashlib, json, os, uuid
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def sha(x): return hashlib.sha256(x if isinstance(x, bytes) else canonical(x).encode()).hexdigest()
def file_hash(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def atomic(p, data):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    temp=p.with_name(p.name+'.tmp-'+uid())
    with temp.open('xb') as f:
        f.write(data if isinstance(data,bytes) else data.encode('utf-8')); f.flush(); os.fsync(f.fileno())
    os.replace(temp,p)
class Fault(Exception):
    def __init__(self, code, detail): self.code,self.detail=code,detail; super().__init__(detail)
    def result(self): return {'ok':False,'schema_version':'1.0','code':self.code,'detail':self.detail}
