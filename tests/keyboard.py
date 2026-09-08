import asyncio
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from websockets.legacy.server import serve

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from alpharch_keyboard import KeyboardHub, send


class Client:
    def __init__(self):
        self.messages = asyncio.Queue()

    async def send(self, message):
        await self.messages.put(json.loads(message)['chartKeys'])


class KeyboardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.focus = 'chart-one'
        self.hub = KeyboardHub(17863, self.tmp.name, lambda: self.focus)
        self.one, self.two = Client(), Client()
        self.hub.register(self.one, 'chart-one')
        self.hub.register(self.two, 'chart-two')

    async def test_routes_only_to_focused_window_and_requires_its_ack(self):
        task = asyncio.create_task(self.hub.dispatch('chart-one', 'indicators'))
        message = await asyncio.wait_for(self.one.messages.get(), 1)
        self.assertEqual(message['action'], 'indicators')
        self.assertTrue(self.two.messages.empty())
        self.hub.acknowledge(self.two, {'ack': message['id'], 'ok': True})
        self.assertFalse(task.done())
        self.hub.acknowledge(self.one, {'ack': message['id'], 'ok': True})
        self.assertEqual(await task, {'ok': True, 'note': ''})
        self.assertFalse(self.hub.pending)

    async def test_rejects_wrong_window_unknown_actions_and_duplicates(self):
        for target, action in [('chart-two','new'), ('chart-one','buy'), ('chart-one',{}), ('../bad','fit')]:
            with self.assertRaises(ValueError):
                await self.hub.dispatch(target, action)
        self.focus = None
        with self.assertRaises(ValueError):
            await self.hub.dispatch('chart-one','new')
        self.focus = 'chart-one'
        duplicate = Client()
        self.hub.register(duplicate, 'chart-one')
        with self.assertRaises(ValueError):
            await self.hub.dispatch('chart-one', 'fit')
        self.assertTrue(self.one.messages.empty())

    async def test_disconnect_unblocks_request_and_cleans_discovery(self):
        task = asyncio.create_task(self.hub.dispatch('chart-one','save'))
        await asyncio.wait_for(self.one.messages.get(),1)
        self.hub.remove(self.one)
        self.assertFalse((await task)['ok'])
        path = Path(self.tmp.name) / 'keyboard-17863.json'
        self.assertEqual(json.loads(path.read_text())['windows'], ['chart-two'])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.hub.remove(self.two)
        self.assertFalse(path.exists())
        self.assertFalse(self.hub.pending)

    async def test_invalid_registration_is_not_published(self):
        for name in [None, '../bad', 'x'*49]:
            with self.assertRaises(ValueError):
                self.hub.register(Client(), name)
        self.assertEqual(len(self.hub.clients), 2)

    async def test_busy_server_can_finish_handshake_without_losing_shortcut(self):
        async def handshake(path, headers):
            await asyncio.sleep(1.2)

        async def handler(ws, path):
            request = json.loads(await ws.recv())
            self.assertEqual(request['chartKeys'], {'target': 'chart-one', 'action': 'commands'})
            await ws.send(json.dumps({'chartKeysResult': {'ok': True, 'note': ''}}))

        async with serve(handler, '127.0.0.1', 0, process_request=handshake) as server:
            port = server.sockets[0].getsockname()[1]
            directory = Path(self.tmp.name) / 'slow-server'
            directory.mkdir()
            (directory / f'keyboard-{port}.json').write_text(json.dumps({'port': port, 'windows': ['chart-one']}))
            with patch('alpharch_keyboard.runtime_dir', return_value=directory):
                self.assertEqual(await send('commands', 'chart-one'), {'ok': True, 'note': ''})


if __name__ == '__main__':
    unittest.main()
