"""Resolve the desktop session for services that started before Omarchy did."""
import json
import os
from pathlib import Path
import subprocess

SESSION_KEYS = ('HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY', 'DISPLAY',
                'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP',
                'DESKTOP_SESSION', 'DBUS_SESSION_BUS_ADDRESS', 'PATH')


def session_ready(env):
    signature = env.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    runtime = env.get('XDG_RUNTIME_DIR', '')
    if not runtime or not signature or '/' in signature or signature in ('.', '..'):
        return False
    return (Path(runtime)/'hypr'/signature/'.socket.sock').is_socket() and bool(env.get('WAYLAND_DISPLAY'))


def desktop_env():
    """Keep caller context when valid; otherwise discover this user's session.

    Only desktop variables are refreshed. Never import credentials or replace
    the chart service's configuration, proxy settings or process environment.
    """
    original = os.environ.copy()
    if session_ready(original):
        return original
    candidate = original.copy()
    try:
        result = subprocess.run(['systemctl', '--user', 'show-environment'],
                                env=original, capture_output=True, text=True, timeout=2, check=True)
        for line in result.stdout.splitlines():
            key, separator, value = line.partition('=')
            if separator and key in SESSION_KEYS and value:
                candidate[key] = value
    except (OSError, subprocess.SubprocessError):
        pass
    if session_ready(candidate):
        return candidate
    # hyprctl can list instances without an inherited instance signature.
    # Refuse to guess between desktops if the session manager cannot identify one.
    try:
        result = subprocess.run(['hyprctl', 'instances', '-j'], env=candidate,
                                capture_output=True, text=True, timeout=2, check=True)
        instances = json.loads(result.stdout)
        if isinstance(instances, list) and len(instances) == 1:
            instance = instances[0]
            signature, display = instance.get('instance'), instance.get('wl_socket')
            if isinstance(signature, str) and isinstance(display, str) and '/' not in display:
                candidate.update(HYPRLAND_INSTANCE_SIGNATURE=signature, WAYLAND_DISPLAY=display)
                candidate.setdefault('XDG_RUNTIME_DIR', '/run/user/'+str(os.getuid()))
                if session_ready(candidate):
                    return candidate
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        pass
    return original
