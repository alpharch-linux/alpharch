"""Hyprland edition: fixed local window actions and private, separate desk files.

Chart documents are inert JSON. The renderer validates chart semantics; no part
of a document is evaluated, used as a command, or accepted as a filesystem path.
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import uuid
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
STORE = Path(os.environ.get('ALPHARCH_HOME', Path.home()/'.config/alpharch'))/'hyprland'
LOCK = threading.RLock()
NAME = re.compile(r'^[A-Za-z0-9_-]{1,48}$')
TITLE = re.compile(r'^Alpharch Hyprland \[([A-Za-z0-9_-]{1,48})\]$')
loader = importlib.machinery.SourceFileLoader('alpharch_live_launcher', str(ROOT/'bin/trade-live'))
spec = importlib.util.spec_from_loader(loader.name, loader)
live = importlib.util.module_from_spec(spec)
loader.exec_module(live)


def name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError('Use 1–48 letters, numbers, dashes or underscores for desk names.')
    return value


def read(kind, key):
    path = STORE/kind/(name(key)+'.json')
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576:
        raise ValueError('This saved Hyprland desk is unavailable.')
    return json.loads(path.read_text())


def write(kind, key, data):
    folder = STORE/kind
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder/(name(key)+'.json')
    if path.is_symlink():
        raise ValueError('A saved desk cannot replace a symbolic link.')
    with tempfile.NamedTemporaryFile(mode='w', dir=folder, delete=False) as tmp:
        try:
            json.dump(data, tmp, allow_nan=False)
            tmp.close()
            os.replace(tmp.name, path)
        finally:
            Path(tmp.name).unlink(missing_ok=True)


def document(value, single=False):
    if not isinstance(value, dict) or not isinstance(value.get('name'), str) or len(value['name']) > 80:
        raise ValueError('Invalid chart document.')
    charts = value.get('charts')
    if not isinstance(charts, list) or len(charts) > (1 if single else 8) or any(not isinstance(c, dict) for c in charts):
        raise ValueError('Choose up to eight charts; each native window holds one chart.')
    if value.get('palette') not in ('pit', 'aurora', 'ember'):
        raise ValueError('Invalid chart palette.')
    # Keep the complete request below the local WebSocket frame limit.
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError('Chart settings must be finite JSON values.') from error
    if len(encoded.encode()) > 60000:
        raise ValueError('This desk is too large to open at once. Open its charts separately.')
    return json.loads(encoded)


def clients():
    return [c for c in live.monitors('clients') if TITLE.fullmatch(c.get('title', ''))]


def require_hyprland():
    if not live.monitors('monitors'):
        raise ValueError('Hyprland is not available on this computer. Classic desk is still available.')


def place(window, workspace, monitor=None):
    destination = workspace if workspace.isdigit() else 'name:'+workspace
    script = 'source "$1"; hypr_window_to_workspace "$2" "$3"; if [[ -n "$4" ]]; then hypr_workspace_to_monitor "$3" "$4"; fi'
    subprocess.run(['bash', '-c', script, 'alpharch-hyprland', str(ROOT/'lib/alpharch-common.sh'),
                    window['address'], destination, monitor or ''], check=True, timeout=8)


def visit(workspace):
    destination = workspace if workspace.isdigit() else 'name:'+workspace
    subprocess.run(['bash', '-c', 'source "$1"; hypr_workspace "$2"', 'alpharch-hyprland',
                    str(ROOT/'lib/alpharch-common.sh'), destination], check=True, timeout=8)


def focus(window):
    subprocess.run(['bash', '-c', 'source "$1"; hypr_window_focus "$2"', 'alpharch-hyprland',
                    str(ROOT/'lib/alpharch-common.sh'), window['address']], check=True, timeout=8)


def open_window(key, port, workspace, monitor=None):
    name(key); name(workspace)
    existing = next((c for c in clients() if c['title'] == f'Alpharch Hyprland [{key}]'), None)
    if existing:
        return str(existing['workspace']['name'])
    url = f'http://127.0.0.1:{port}/#'+urlencode({'edition':'hyprland', 'window':key})
    subprocess.Popen(live.browser_command(url), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        window = next((c for c in clients() if c['title'] == f'Alpharch Hyprland [{key}]'), None)
        if window:
            place(window, workspace, monitor)
            return workspace
        time.sleep(.1)
    raise ValueError('The window launch could not be confirmed. Check your app browser before retrying.')


def home_workspace():
    existing = clients()
    if existing:
        return str(existing[0]['workspace']['name'])
    occupied = {w.get('id') for w in live.monitors('workspaces')}
    # Numbered workspaces stay reachable with Omarchy's workspace keys. Do not
    # put the new desk into a workspace occupied by the user's other apps.
    return str(next(i for i in [9, 8, 7, 6, 10, *range(11, 1000)] if i not in occupied))


def launch_document(value, port, source=None, workspace=None):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Invalid local service port.')
    require_hyprland()
    value = document(value)
    workspace = workspace or home_workspace()
    if len(clients()) + max(1, len(value['charts'])) > 12:
        raise ValueError('Twelve Hyprland chart windows are already in use. Close a window before adding more.')
    if source:
        parent = next((c for c in clients() if c['title'] == f'Alpharch Hyprland [{name(source)}]'), None)
        if parent:
            workspace = str(parent['workspace']['name'])
    name(workspace)
    live.ensure_server(port)
    opened = []
    # Save all seeds first, so a failed placement never loses the chosen chart.
    for chart in value['charts'] or [None]:
        key = 'chart-'+uuid.uuid4().hex[:12]
        seed = {**value, 'charts':[{**chart, 'x':0, 'y':0, 'w':1, 'h':1}] if chart else []}
        write('windows', key, seed)
        opened.append(key)
    for key in opened:
        open_window(key, port, workspace)
    visit(workspace)
    return {'opened':opened, 'note':f'Opened {len(opened)} Hyprland window(s). Your Classic desk is unchanged.'}


def save_layout(key):
    require_hyprland(); name(key)
    displays = {m['id']:m['name'] for m in live.monitors('monitors')}
    windows = []
    for client in clients():
        window = TITLE.fullmatch(client['title'])[1]
        windows.append({'name':window, 'document':document(read('windows', window), single=True),
                        'workspace':name(str(client['workspace']['name'])), 'monitor':displays.get(client.get('monitor'))})
    if not 1 <= len(windows) <= 12:
        raise ValueError('Open 1–12 Hyprland chart windows before saving a desk.')
    write('layouts', key, {'schema':'alpharch.hyprland/1', 'windows':windows})
    return {'note':f'Saved {len(windows)} chart windows, workspaces and monitors. Hyprland controls the tile proportions.'}


def load_layout(key, port):
    require_hyprland()
    data = read('layouts', key)
    if not isinstance(data, dict) or data.get('schema') != 'alpharch.hyprland/1' or not isinstance(data.get('windows'), list) or not 1 <= len(data['windows']) <= 12:
        raise ValueError('Invalid Hyprland desk file.')
    displays = [m['name'] for m in live.monitors('monitors')]
    active = {TITLE.fullmatch(c['title'])[1] for c in clients()}
    seen = set()
    for item in data['windows']:
        if not isinstance(item, dict) or name(item.get('name')) in seen:
            raise ValueError('Duplicate or invalid saved window.')
        seen.add(item['name']); name(item.get('workspace')); document(item.get('document'), single=True)
        if item.get('monitor') is not None and not isinstance(item['monitor'], str):
            raise ValueError('Invalid monitor.')
    if len(active | seen) > 12:
        raise ValueError('Close some Hyprland windows before restoring this desk (12 maximum).')
    live.ensure_server(port)
    for item in data['windows']:
        if item['name'] in active:
            continue  # Never overwrite an already-open chart with an older snapshot.
        write('windows', item['name'], item['document'])
        open_window(item['name'], port, item['workspace'], item.get('monitor') if item.get('monitor') in displays else displays[0])
    first = data['windows'][0]
    actual = next((c for c in clients() if c['title'] == f"Alpharch Hyprland [{first['name']}]"), None)
    visit(str(actual['workspace']['name']) if actual else first['workspace'])
    return {'note':'Hyprland desk restored. Already-open charts were preserved.'}


def action(message, port):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Invalid local service port.')
    # A launch waits for the new browser to fetch its seed. Reads/writes must not
    # wait on the launch lock, or the compositor can never receive its title.
    kind = message.get('action')
    if kind == 'read':
        return {'document':document(read('windows', message.get('window')), single=True)}
    if kind == 'write':
        key = name(message.get('window'))
        read('windows', key)  # Only the launcher may create a window identity.
        write('windows', key, document(message.get('document'), single=True))
        return {'saved':True}
    if kind == 'catalog':
        return {'available':bool(live.monitors('monitors')), 'windows':[TITLE.fullmatch(c['title'])[1] for c in clients()], 'layouts':[p.stem for p in sorted((STORE/'layouts').glob('*.json')) if NAME.fullmatch(p.stem)]}
    with LOCK:
        if kind == 'open':
            return launch_document(message.get('document'), port, message.get('source'))
        if kind == 'save':
            return save_layout(message.get('name'))
        if kind == 'load':
            return load_layout(message.get('name'), port)
        if kind == 'classic':
            live.open_window('desk', port, workspace='alpharch-classic')
            existing = next((c for c in live.monitors('clients') if c.get('title') == 'Alpharch Live [desk]'), None)
            if existing:
                focus(existing)
            return {'note':'Opened Classic desk with its own saved layout.'}
    raise ValueError('Unsupported Hyprland action.')
