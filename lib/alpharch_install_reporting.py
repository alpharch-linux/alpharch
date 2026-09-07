#!/usr/bin/env python3
"""Opt-in installation receipts. No daemon, device identifier, or trading data."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import tempfile
import uuid

ENDPOINT = 'https://alpharch-install-insights.dapper-tang-3900.chatgpt.site/api/v1/install'
CONSENT_VERSION = 1
DISCLOSURE = '''Optional installation reports
Help count completed Alpharch installations. Off by default.
If enabled, send the app version, build, install/update/reinstall type and a
random ID used only to prevent duplicate reports. The server adds the date.
No account, trade, chart, hardware or device identifiers are included.
The hosting provider receives your IP as part of the connection; Alpharch's
report database does not store it. Reports are kept for release statistics.
Details: https://alpharch.org/privacy.html
You can turn this off anytime: alpharch install-reports off'''


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.install-report-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, separators=(',', ':'))
            out.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def valid_report(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'event_id', 'kind', 'version', 'build'}:
        return False
    try:
        ident = uuid.UUID(value['event_id'])
        return (value['schema'] == 1 and ident.version == 4 and str(ident) == value['event_id']
                and value['kind'] in ('install', 'update', 'reinstall')
                and bool(re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.-]{1,32})?', value['version']))
                and bool(re.fullmatch(r'[a-f0-9]{7,64}', value['build'])))
    except (ValueError, TypeError, AttributeError):
        return False


def transmit(report):
    """Fixed HTTPS destination, no redirects, bounded time and response size."""
    try:
        result = subprocess.run([
            'curl', '--silent', '--show-error', '--fail', '--proto', '=https',
            '--connect-timeout', '1', '--max-time', '2', '--max-filesize', '4096',
            '--request', 'POST', '--header', 'Content-Type: application/json',
            '--user-agent', 'Alpharch-install-report/1', '--data-binary', '@-', ENDPOINT,
        ], input=json.dumps(report), text=True, capture_output=True, timeout=3)
        if result.returncode:
            return False
        return json.loads(result.stdout).get('status') in ('accepted', 'duplicate')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


class Reporter:
    def __init__(self, home=None, send=transmit):
        self.home = Path(home or Path.home())
        self.config_path = self.home / '.config/alpharch/install-reporting.json'
        self.state_path = self.home / '.local/state/alpharch/install-reporting.json'
        self.config = read_json(self.config_path)
        self.state = read_json(self.state_path)
        self.send = send

    @property
    def enabled(self):
        return self.config.get('enabled') is True and self.config.get('consent_version') == CONSENT_VERSION

    def set_enabled(self, enabled):
        self.config = {'enabled': bool(enabled), 'consent_version': CONSENT_VERSION}
        write_json(self.config_path, self.config)
        if not enabled:
            self.state.pop('pending', None)
            write_json(self.state_path, self.state)

    def finish(self, version, build, existing, choice='ask', prompt=None):
        if not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.-]{1,32})?', version):
            raise ValueError('Invalid version')
        if not re.fullmatch(r'[a-f0-9]{7,64}', build):
            raise ValueError('Invalid build')
        if choice in ('on', 'off'):
            self.set_enabled(choice == 'on')
        elif self.config.get('consent_version') != CONSENT_VERSION:
            self.set_enabled(bool(prompt and prompt()))
        previous = self.state.get('last_build')
        kind = 'install' if not existing else ('reinstall' if previous == build else 'update')
        self.state['last_build'] = build
        # Historical opt-out receipts are never sent after opting in later.
        if not self.enabled:
            self.state.pop('pending', None)
            write_json(self.state_path, self.state)
            return 0
        pending = self.state.get('pending', [])
        if not isinstance(pending, list):
            pending = []
        # Reject corrupt or edited queued records rather than transmitting extra fields.
        pending = [r for r in pending if valid_report(r)][-9:]
        pending.append({'schema': 1, 'event_id': str(uuid.uuid4()), 'kind': kind, 'version': version, 'build': build})
        self.state['pending'] = pending
        write_json(self.state_path, self.state)
        sent = 0
        # A retry keeps its event ID; at most three requests on a later install.
        for report in list(pending)[:3]:
            if not self.send(report):
                break
            pending.remove(report)
            sent += 1
            write_json(self.state_path, self.state)
        return sent


def ask():
    if not sys.stdout.isatty():
        return False
    try:
        with open('/dev/tty', 'r+') as tty:
            tty.write('\n' + DISCLOSURE + '\n\nShare installation reports? [y/N] (defaults to No in 20 seconds): ')
            tty.flush()
            ready, _, _ = select.select([tty], [], [], 20)
            answer = tty.readline().strip().lower() if ready else ''
            tty.write('\n')
            return answer in ('y', 'yes')
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description='Manage optional installation reports.')
    parser.add_argument('action', choices=['finish', 'on', 'off', 'status'])
    parser.add_argument('--version')
    parser.add_argument('--build')
    parser.add_argument('--existing', choices=['0', '1'], default='1')
    parser.add_argument('--choice', choices=['ask', 'on', 'off'], default='ask')
    args = parser.parse_args()
    lock = Path.home() / '.local/state/alpharch/install-reporting.lock'
    lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(lock, 'a') as handle:
        os.chmod(lock, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Installation report settings are busy. Try again shortly.')
            return 0 if args.action == 'finish' else 1
        reporter = Reporter()
        if args.action in ('on', 'off'):
            if args.action == 'on':
                print(DISCLOSURE)
            reporter.set_enabled(args.action == 'on')
        elif args.action == 'finish':
            sent = reporter.finish(args.version or '', args.build or '', args.existing == '1', args.choice, ask)
            if sent:
                print('Optional installation report received. Thank you.')
            elif reporter.enabled:
                print('Installation report pending; installation succeeded. A later install can retry it.')
        print('Installation reports: ' + ('on' if reporter.enabled else 'off'))
        if args.action != 'finish':
            print('Change anytime: alpharch install-reports on | off | status')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError) as exc:
        print('Installation reporting unavailable; your installation is unaffected.', file=sys.stderr)
        sys.exit(1)
