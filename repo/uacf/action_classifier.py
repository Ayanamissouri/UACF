"""Small, conservative action facts; opaque execution is never proved read-only.

Adapted from a registered DS candidate after main-host boundary review. This is
not a shell parser or sandbox. Names outside the explicit table stay unknown.
"""
import re

READ_TOOLS={'read_file','search_files','mcp__uacf__uacf_context','mcp__uacf__uacf_status',
 'mcp__uacf__uacf_work_brief','mcp__uacf__uacf_search','view_image'}
WRITE_TOOLS={'apply_patch','edit','write','write_file','edit_file','multiedit'}
SHELL_TOOLS={'exec_command','bash','shell','shell_command','powershell'}
WRITE_CMDS={'set-content','add-content','remove-item','new-item','move-item','copy-item','out-file'}
# Reject interpolation, pipelines, redirection and script expressions rather
# than pretending that splitting words can establish their execution effects.
UNPROVEN=re.compile(r'[;&|<>\n\r`$(){}@]')

def classify(name,inp):
 if not isinstance(name,str):return 'unknown'
 name=name.removeprefix('functions.').removeprefix('tools.')
 low=name.lower()
 if low in WRITE_TOOLS:return 'write'
 if name in READ_TOOLS:return 'read'
 if low not in SHELL_TOOLS:return 'unknown'
 if isinstance(inp,str):cmd=inp
 elif isinstance(inp,dict):
  if inp.get('cmd') and inp.get('command') and inp['cmd']!=inp['command']:return 'unknown'
  cmd=inp.get('command') or inp.get('cmd')
 else:return 'unknown'
 if not isinstance(cmd,str) or not cmd.strip() or UNPROVEN.search(cmd):return 'unknown'
 words=cmd.lower().strip().split();head=words[0]
 if head in WRITE_CMDS:return 'write'
 if head in {'get-content','get-item','get-childitem','select-object'}:return 'read'
 if head=='git' and len(words)>1 and words[1] in {'status','diff','show','log'}:
  if any(w.startswith(('--output','--ext-diff','--textconv','--config','--exec')) or w=='-o' for w in words[2:]):return 'unknown'
  return 'read'
 if head=='rg':
  if any(w.startswith(('--pre','--hostname-bin')) for w in words[1:]):return 'unknown'
  return 'read'
 return 'unknown'
