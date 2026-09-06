#!/usr/bin/env python3
"""Offline behavioral checks. All prices below are SPECIMEN DATA."""
import asyncio
import csv
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

flow = module('flow', ROOT / 'bin/alphad')
importer = module('importer', ROOT / 'bin/alpha-import-futures')

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / 'source.csv'
        self.dst = Path(self.tmp.name) / 'replay.jsonl'
        self.rows = [dict(ts_event='1700000000000000000', instrument_id='123',
                         action='T', side='B', price='23214.25', size='3',
                         bid_px_00='23214', ask_px_00='23214.25',
                         bid_sz_00='4', ask_sz_00='5')]

    def convert(self, schema='mbp-1', prices='decimal'):
        with self.src.open('w') as f:
            w = csv.DictWriter(f, fieldnames=self.rows[0].keys())
            w.writeheader(); w.writerows(self.rows)
        return importer.convert(self.src, self.dst, 'TEST', .25, schema, prices)

    def test_roundtrip_and_precision(self):
        self.convert()
        events = [json.loads(x) for x in self.dst.read_text().splitlines()]
        self.assertEqual(events[0]['tick'], .25)
        self.assertEqual(events[1]['bids'], [[23214, 4]])
        self.assertEqual(events[2]['p'], 23214.25)
        self.assertEqual(events[2]['a'], 'buy')
        facts = flow.analyze_tape(str(self.dst), .25, 60, 8, 3)
        self.assertEqual(facts['session']['open'], 23214.25)
        self.assertEqual(flow.fpx(23214.25), '23,214.25')

    def test_fixed_price_and_sell(self):
        for k in ['price', 'bid_px_00', 'ask_px_00']:
            self.rows[0][k] = str(int(float(self.rows[0][k]) * 10**9))
        self.rows[0]['side'] = 'A'
        self.convert(prices='fixed')
        event = json.loads(self.dst.read_text().splitlines()[-1])
        self.assertEqual((event['p'], event['a']), (23214.25, 'sell'))

    def test_mixed_contracts_rejected_atomically(self):
        self.rows.append({**self.rows[0], 'instrument_id': '456'})
        with self.assertRaisesRegex(ValueError, 'multiple instruments'):
            self.convert()
        self.assertFalse(self.dst.exists())

    def test_no_overwrite(self):
        self.dst.write_text('precious recording')
        with self.assertRaises(FileExistsError):
            self.convert()
        self.assertEqual(self.dst.read_text(), 'precious recording')

    def test_unknown_aggressor_not_invented(self):
        self.rows[0]['side'] = 'N'
        result = self.convert()
        self.assertEqual(result['unknown_side_trades_skipped'], 1)
        self.assertEqual(result['events'], 1)

    def test_nan_rejected(self):
        self.rows[0]['price'] = 'Infinity'
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            self.convert()
        self.assertFalse(self.dst.exists())

    def test_timezone_required(self):
        self.rows[0]['ts_event'] = '2026-09-05T10:00:00'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            self.convert()

class ChartTests(unittest.TestCase):
    def test_tick_volume_and_time_rebuild_keep_session(self):
        eng = flow.Engine(.25, 60, 8, 3)
        eng.symbol = 'TEST'
        for i in range(10):
            eng.on_trade(flow.Trade(1700000000+i*20, 100+i*.25, 2, 'buy'))
        before = (eng.cvd, eng._v, len(eng.history))
        flow.apply_ctrl(eng, {}, {'bars': {'mode':'tick', 'value':3}})
        self.assertEqual([b.trades for b in eng.buckets], [3,3,3])
        flow.apply_ctrl(eng, {}, {'bars': {'mode':'volume', 'value':5}})
        self.assertEqual([b.volume for b in eng.buckets], [6,6,6])
        flow.apply_ctrl(eng, {}, {'bars': {'mode':'time', 'value':60}})
        self.assertEqual((eng.cvd, eng._v, len(eng.history)), before)
        self.assertEqual(eng.bar_mode, 'time')

class ReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_pause_step_seek_and_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tape.jsonl'
            events = [{'k':'h','ts':9999999999,'feed':'test','symbol':'TEST'}]
            events += [{'k':'t','ts':100+i*10,'p':100+i,'s':1,'a':'buy'} for i in range(3)]
            path.write_text('\n'.join(map(json.dumps,events)))
            eng = flow.Engine(.25,60,8,3); eng.symbol='TEST';eng.replay_paused=True
            task = asyncio.create_task(flow.replay_feed(eng,str(path),32,lambda:None))
            try:
                await asyncio.sleep(.07)
                self.assertEqual(eng.n_trades,0)
                eng.replay_step=True
                await asyncio.sleep(.07)
                self.assertEqual(eng.n_trades,1)
                eng.replay_seek=1
                await asyncio.sleep(.07)
                self.assertEqual(eng.n_trades,3)
                self.assertEqual(eng.replay_progress,1)
                eng.replay_step=True
                await asyncio.sleep(.07)
                self.assertEqual(eng.n_trades,3)
                self.assertTrue(eng.replay_done)
                eng.replay_seek=0
                await asyncio.sleep(.07)
                self.assertEqual(eng.n_trades,0)
                self.assertFalse(eng.replay_done)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

if __name__ == '__main__':
    unittest.main()
