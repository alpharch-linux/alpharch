"""Route a fixed set of UI actions to the focused Alpharch window only."""
import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
from websockets.exceptions import ConnectionClosed

ACTIONS = {'commands', 'new', 'indicators', 'interval', 'drawings', 'save',
           'style', 'connections', 'review', 'history', 'live', 'fit', 'tools', 'layouts'}
WINDOW = re.compile(r'^[A-Za-z0-9_-]{1,48}$')
TITLE = re.compile(r'^Alpharch (?:Hyprland|Live) \[([A-Za-z0-9_-]{1,48})\]$')


def focused_target():
    from alpharch_native import live
    window = live.monitors('activewindow')
    title = window.get('title', '') if isinstance(window, dict) else ''
    match = TITLE.fullmatch(title)
    return match[1] if match else ('default' if title == 'Alpharch · Live desk' else None)


def runtime_dir():
    return Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'alpharch'


class KeyboardHub:
    def __init__(self, port, directory=None, focus=focused_target):
        self.port, self.focus = port, focus
        self.directory = Path(directory) if directory is not None else runtime_dir()
        self.clients, self.pending = {}, {}

    def publish(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.directory / f'keyboard-{self.port}.json'
        if not self.clients:
            path.unlink(missing_ok=True)
            return
        temp = self.directory / f'.keyboard-{uuid.uuid4().hex}.tmp'
        try:
            with temp.open('x') as stream:
                os.chmod(temp, 0o600)
                json.dump({'port': self.port, 'windows': list(self.clients.values())}, stream)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    def register(self, ws, name):
        if not isinstance(name, str) or not WINDOW.fullmatch(name):
            raise ValueError('Invalid chart window.')
        self.clients[ws] = name
        self.publish()

    def remove(self, ws):
        if ws in self.clients:
            del self.clients[ws]
            self.publish()
        for ident, (recipient, future) in list(self.pending.items()):
            if recipient is ws and not future.done():
                future.set_result({'ok': False, 'note': 'Chart disconnected. Try again after it reconnects.'})

    def acknowledge(self, ws, msg):
        ident = msg.get('ack')
        if not isinstance(ident, str):
            return
        item = self.pending.get(ident)
        if item and item[0] is ws and not item[1].done():
            item[1].set_result({'ok': msg.get('ok') is True, 'note': str(msg.get('note', ''))[:200]})

    async def dispatch(self, target, action):
        if not isinstance(action, str) or action not in ACTIONS or not isinstance(target, str) or not WINDOW.fullmatch(target):
            raise ValueError('Unsupported chart shortcut.')
        if target != await asyncio.to_thread(self.focus):
            raise ValueError('Focus an Alpharch chart first.')
        matches = [ws for ws, name in self.clients.items() if name == target]
        if len(matches) != 1:
            raise ValueError('The focused chart is not ready, or is open twice. Reload it before using shortcuts.')
        recipient = matches[0]
        ident = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.pending[ident] = (recipient, future)
        try:
            await recipient.send(json.dumps({'chartKeys': {'id': ident, 'action': action}}))
            return await asyncio.wait_for(future, 3)
        except (asyncio.TimeoutError, OSError, ConnectionClosed):
            return {'ok': False, 'note': 'Chart did not respond. Reload the focused chart and try again.'}
        finally:
            self.pending.pop(ident, None)


async def send(action, target):
    from websockets.legacy.client import connect
    for path in sorted(runtime_dir().glob('keyboard-*.json'))[:32]:
        try:
            if path.is_symlink() or path.stat().st_size > 65536:
                continue
            info = json.loads(path.read_text())
            port = info['port']
            if type(port) is not int or not 1024 <= port <= 65535 or target not in info['windows']:
                continue
            async with connect(f'ws://127.0.0.1:{port}/ws', open_timeout=1, max_size=65536) as ws:
                await ws.send(json.dumps({'chartKeys': {'target': target, 'action': action}}))
                while True:
                    reply = json.loads(await asyncio.wait_for(ws.recv(), 4))
                    if 'chartKeysResult' in reply:
                        return reply['chartKeysResult']
        except (OSError, ValueError, KeyError, TypeError, asyncio.TimeoutError, ConnectionClosed):
            continue
    return {'ok': False, 'note': 'Reload this Alpharch chart to activate its keyboard controls.'}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=sorted(ACTIONS))
    args = parser.parse_args()
    target = focused_target()
    result = asyncio.run(send(args.action, target)) if target else {'ok': False, 'note': 'Focus an Alpharch chart first. Super+Alt+V opens the desk.'}
    if not result.get('ok'):
        print(result.get('note', 'Chart shortcut unavailable.'))
        try:
            subprocess.run(['notify-send', 'Alpharch', result.get('note', 'Chart shortcut unavailable.')], check=False)
        except FileNotFoundError:
            pass
        return 1
    return 0
