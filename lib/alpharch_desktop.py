"""Explicit user-invoked local tools. Fixed commands, no shell or broker actions."""
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TAPES = Path(os.environ.get('ALPHARCH_TAPES', Path.home()/'tapes')).expanduser()


def recordings():
    return sorted(p.name for p in TAPES.glob('*.jsonl') if p.is_file() and not p.is_symlink())[-100:]


def catalog():
    commands={'journal':'trade-journal','calendar':'trade-cal','options':'alphaopt','brain':'trade-brain','replay':'alphad','record':'alphad'}
    return {'available':[k for k,v in commands.items() if (ROOT/'bin'/v).is_file()], 'recordings':recordings(), 'tapeDirectory':str(TAPES)}


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def command(action, message):
    fixed={'journal':['trade-journal','today'],'calendar':['trade-cal','week','--plain'],'options':['alphaopt'],'brain':['trade-brain','help']}
    if action in fixed:
        args=fixed[action]
        if not (ROOT/'bin'/args[0]).is_file():
            raise ValueError('This local tool is not installed in this bundle')
        terminal=shutil.which('omarchy-launch-terminal')
        if terminal:
            # Keep read-only output visible until the user closes the terminal.
            return [terminal,'bash','-c','"$@"; printf "\\nPress Enter to close."; read -r _alpharch_reply','alpharch-tool',str(ROOT/'bin'/args[0]),*args[1:]]
        for name in ('foot','ghostty','kitty','alacritty'):
            if shutil.which(name):
                return [name,'-e',str(ROOT/'bin'/args[0]),*args[1:]]
        raise ValueError('A supported terminal is required for this local tool')
    if action == 'replay':
        name=message.get('file')
        if name not in recordings():
            raise ValueError('Choose an available local recording')
        return [sys.executable,str(ROOT/'bin/alphad'),'--canvas','--replay',str(TAPES/name),'--start-paused','--port',str(free_port())]
    if action == 'record':
        asset,feed=message.get('asset'),message.get('feed')
        if asset not in ('BTC','ETH','SOL') or feed not in ('coinbase','hyperliquid'):
            raise ValueError('Choose a supported crypto chart')
        tick=message.get('tick')
        if not isinstance(tick,(int,float)) or not math.isfinite(tick) or not 1e-8<=tick<=100000:
            raise ValueError('A current chart price increment is required to record')
        TAPES.mkdir(parents=True,exist_ok=True)
        path=TAPES/(feed+'-'+asset+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()%1000000)+'.jsonl')
        terminal=shutil.which('omarchy-launch-terminal')
        if not terminal:
            raise ValueError('Record needs omarchy-launch-terminal so its running engine can be stopped visibly')
        return [terminal,sys.executable,str(ROOT/'bin/alphad'),'--canvas','--exchange',feed,'--symbol',asset+'-USD' if feed=='coinbase' else asset,'--market','spot' if feed=='coinbase' else 'perp','--tick',str(tick),'--record',str(path),'--port',str(free_port())]
    raise ValueError('Unsupported local tool')


def launch(message):
    action=message.get('action')
    if action=='journal-note':
        note=message.get('text')
        if not isinstance(note,str) or not 1<=len(note.strip())<=4000 or '\x00' in note:
            raise ValueError('Write a journal note of 1–4000 characters.')
        result=subprocess.run([str(ROOT/'bin/trade-journal'),'note',note],capture_output=True,text=True,timeout=8)
        if result.returncode:
            raise ValueError('The journal note could not be saved. Check the journal directory permissions.')
        return {'opened':'journal-note','note':'Appended to your local daily journal.'}
    if action=='catalog':
        return catalog()
    args=command(action,message)
    subprocess.Popen(args,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {'opened':action,'note':'Opened local '+action+('. Close the recording terminal or press Ctrl+C there to stop.' if action=='record' else '')}
