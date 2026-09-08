"""Read only Omarchy's color metadata; never execute theme content or hooks."""
import json
from pathlib import Path
import re
import time
import tomllib


class OmarchyTheme:
    def __init__(self, home=None, clock=time.monotonic):
        home = Path.home() if home is None else Path(home)
        self.roots = [home / '.local/state/omarchy/current', home / '.config/omarchy/current']
        self.clock = clock
        self.checked = None
        self.cached = {'available': False}

    def snapshot(self):
        now = self.clock()
        if self.checked is not None and now - self.checked < 2:
            return self.cached
        self.checked = now
        for root in self.roots:
            try:
                with (root / 'theme/colors.toml').open('rb') as stream:
                    raw = stream.read(16385)
                if len(raw) > 16384:
                    continue
                values = tomllib.loads(raw.decode('utf-8'))
                colors = {k: values[k] for k in ('background', 'foreground', 'accent', 'lighter_background')
                          if isinstance(values.get(k), str) and re.fullmatch(r'#[0-9a-fA-F]{6}', values[k])}
                if not all(k in colors for k in ('background', 'foreground', 'accent')):
                    continue
                try:
                    with (root / 'theme.name').open() as stream:
                        name = stream.read(81).strip()
                    if not re.fullmatch(r'[\w .-]{1,80}', name):
                        name = 'Omarchy'
                except (OSError, UnicodeError):
                    name = 'Omarchy'
                self.cached = {'available': True, 'name': name, 'colors': colors}
                return self.cached
            except (OSError, UnicodeError, ValueError):
                continue
        self.cached = {'available': False}
        return self.cached

    def signature(self):
        return json.dumps(self.snapshot(), sort_keys=True)
