import asyncio
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from alpharch_keyboard import KeyboardHub


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


if __name__ == '__main__':
    unittest.main()
