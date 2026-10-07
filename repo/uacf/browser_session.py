"""Loopback browser sessions; no raw API credential is persisted in the browser."""
import base64,binascii,hashlib,hmac,json,secrets,time
from http.cookies import SimpleCookie
from .util import Fault,canonical

COOKIE='uacf_session'
MAX_AGE=30*24*3600
def cookie_name(port):return COOKIE+'_'+str(port)

def origin_allowed(headers,port):
 host=headers.get('Host','')
 if host not in [f'127.0.0.1:{port}',f'localhost:{port}']:return False
 return headers.get('Origin')=='http://'+host and headers.get('Sec-Fetch-Site','same-origin')=='same-origin'

def issue(state,actor,port):
 auth=json.loads((state.data/'auth.json').read_text())
 raw=canonical({'actor':actor,'authority':state.authority,'port':port,'expires':int(time.time())+MAX_AGE,'nonce':secrets.token_hex(16)}).encode()
 encoded=base64.urlsafe_b64encode(raw).decode().rstrip('=')
 signature=hmac.new(auth[actor].encode(),encoded.encode(),hashlib.sha256).hexdigest()
 return f'{cookie_name(port)}={encoded}.{signature}; Path=/; HttpOnly; SameSite=Strict; Max-Age={MAX_AGE}'

def authenticate(state,cookie,port):
 try:
  parsed=SimpleCookie();parsed.load(cookie or '')
  token=(parsed.get(cookie_name(port)) or parsed[COOKIE]).value;encoded,signature=token.split('.')
  obj=json.loads(base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4)))
  actor=obj['actor'];auth=json.loads((state.data/'auth.json').read_text())
  expected=hmac.new(auth[actor].encode(),encoded.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(signature,expected) or obj['authority']!=state.authority or obj['port']!=port or type(obj['expires'])!=int or not time.time()<obj['expires']<=time.time()+MAX_AGE+5:raise ValueError()
  return actor
 except (KeyError,ValueError,TypeError,binascii.Error,UnicodeDecodeError):raise Fault('AUTHENTICATION','browser session missing, expired or revoked; pair this browser using local auth file')

def clear(port=None):
 legacy=f'{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
 return [f'{cookie_name(port)}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0',legacy] if port is not None else legacy

def launch_ticket(state,port):
 """Native local launcher only; short-lived token, never the API credential."""
 auth=json.loads((state.data/'auth.json').read_text())
 raw=canonical({'authority':state.authority,'port':port,'expires':int(time.time())+120,'nonce':secrets.token_hex(32),'purpose':'browser-launch'}).encode()
 encoded=base64.urlsafe_b64encode(raw).decode().rstrip('=')
 return encoded+'.'+hmac.new(auth['owner'].encode(),encoded.encode(),hashlib.sha256).hexdigest()

def consume_launch_ticket(state,token,port):
 import sqlite3
 from contextlib import closing
 try:
  if not isinstance(token,str) or len(token)>2048:raise ValueError()
  encoded,signature=token.split('.')
  obj=json.loads(base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4)))
  auth=json.loads((state.data/'auth.json').read_text())
  expected=hmac.new(auth['owner'].encode(),encoded.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(signature,expected) or obj['purpose']!='browser-launch' or obj['authority']!=state.authority or obj['port']!=port or type(obj['expires'])!=int or not time.time()<obj['expires']<=time.time()+125 or len(obj['nonce'])!=64:raise ValueError()
  # Ephemeral replay protection is separate from engineering records and budgets.
  with closing(sqlite3.connect(state.data/'browser-launch-used.sqlite',timeout=10)) as c:
   with c:
    c.execute('CREATE TABLE IF NOT EXISTS used(nonce TEXT PRIMARY KEY,expires INTEGER NOT NULL)')
    c.execute('DELETE FROM used WHERE expires < ?',(int(time.time()),))
    c.execute('INSERT INTO used VALUES (?,?)',(obj['nonce'],obj['expires']))
  return 'owner'
 except (KeyError,ValueError,TypeError,binascii.Error,UnicodeDecodeError,sqlite3.IntegrityError):
  raise Fault('AUTHENTICATION','local launch ticket expired, invalid or already used; reopen the local launcher')
