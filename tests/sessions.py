"""SPECIMEN deterministic recordings; no invented data reaches live charts."""
import json
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_public import Market
from alpharch_sessions import Sessions
from alpharch_streams import Streams

class SessionTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def tape(self,asset='BTC',offset=0):
        name=asset+'.jsonl';rows=[{'k':'h','feed':'coinbase','symbol':asset+'-USD','tick':'.01'},
         {'k':'t','ts':1700000000+offset,'p':'100.01','s':'.00000001','a':'buy'},
         {'k':'b','ts':1700000001+offset,'bids':[['100','2']],'asks':[['100.02','3']]},
         {'k':'t','ts':1700000002+offset,'p':'100.02','s':'2','a':'sell'}]
        (self.path/name).write_text('\n'.join(json.dumps(r) for r in rows)+'\n');return name
    def test_synchronized_clock_and_end_consumes_every_event(self):
        manager=Sessions({},self.path);manager.load([self.tape(),self.tape('ETH',1)])
        self.assertTrue(manager.paused);self.assertEqual(manager.index,0)
        manager.command({'action':'step'});self.assertEqual(manager.clock,1700000000)
        manager.seek(1);self.assertEqual(manager.status()['progress'],1);self.assertEqual(manager.index,6)
        self.assertEqual(len(manager.replay['coinbase:BTC'].trades),2);self.assertEqual(len(manager.replay['coinbase:ETH'].trades),2)
        for snapshot in manager.snapshots():self.assertTrue(snapshot['replay']);self.assertEqual(snapshot['replayClock'],1700000003)
        manager.seek(0);self.assertEqual(manager.index,0);self.assertFalse(manager.replay['coinbase:BTC'].trades)
    def test_precise_recording_round_trip_and_listener_cleanup(self):
        market=Market('kraken','BTC');market.tick=Decimal('.1');market.connected=True
        manager=Sessions({'kraken:BTC':market},self.path);manager.record(['kraken:BTC'])
        market.add_trade('1',1700000000,'79959.9','.00000001','buy');market.book([['79959.8','1']],[['79959.9','2']],1700000001)
        manager.stop();self.assertFalse(market.listeners)
        name=manager.files()[0];text=(self.path/name).read_text();self.assertIn('79959.9',text)
        manager.load([name]);manager.seek(1);self.assertEqual(manager.replay['kraken:BTC'].trades[0]['q'],Decimal('.00000001'));self.assertEqual(manager.replay['kraken:BTC'].price_tick(),Decimal('.1'))
    def test_stopping_one_provider_preserves_other_recording(self):
        first=Market('coinbase','BTC');second=Market('kraken','BTC')
        for market in (first,second):market.tick=Decimal('.1');market.connected=True
        manager=Sessions({first.key:first,second.key:second},self.path);manager.record([first.key,second.key]);manager.stop([first.key])
        self.assertFalse(first.listeners);self.assertTrue(second.listeners);self.assertEqual(manager.status()['recording'],[second.key]);manager.stop()
    def test_record_write_failure_is_explicit_without_breaking_feed(self):
        market=Market('coinbase','BTC');market.tick=Decimal('.01');market.connected=True
        manager=Sessions({market.key:market},self.path);manager.record([market.key]);record=manager.recorders[market.key];record['handle'].close()
        class FailingHandle:
            closed=False
            def write(self,*args):raise OSError('SPECIMEN disk full')
            def close(self):self.closed=True
        record['handle']=FailingHandle()
        market.add_trade('1',1700000000,'100','1','buy')
        self.assertTrue(manager.error);self.assertTrue(market.connected);self.assertTrue(record['handle'].closed);manager.stop()
    def test_invalid_load_preserves_previous_session(self):
        manager=Sessions({},self.path);manager.load([self.tape()]);manager.seek(1)
        with self.assertRaises(ValueError):manager.load(['../private.jsonl'])
        self.assertEqual(manager.index,3)
    def test_symlink_not_in_catalog(self):
        (self.path/'linked.jsonl').symlink_to('/etc/passwd');self.assertNotIn('linked.jsonl',Sessions({},self.path).files())
    def test_unknown_sides_and_missing_tick_fail(self):
        name=self.tape();p=self.path/name;p.write_text(p.read_text().replace('"buy"','"unknown"'))
        with self.assertRaises(ValueError):Sessions({},self.path).load([name])

class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_source_survives_one_owner_and_stops_after_last(self):
        import asyncio
        class SpecimenMarket:
            def __init__(self,*args):self.stopped=False
            async def run(self):
                try:await asyncio.Future()
                finally:self.stopped=True
        streams=Streams(SpecimenMarket)
        await streams.set('window-one',{'coinbase:BTC'});await asyncio.sleep(0)
        original=streams.markets['coinbase:BTC']
        await streams.set('window-two',{'coinbase:BTC','kraken:ETH'});await asyncio.sleep(0)
        await streams.remove('window-one');self.assertIs(streams.markets['coinbase:BTC'],original);self.assertFalse(original.stopped)
        await streams.set('recorder',{'coinbase:BTC'})
        await streams.remove('window-two');self.assertIn('coinbase:BTC',streams.markets);self.assertNotIn('kraken:ETH',streams.markets)
        await streams.remove('recorder');self.assertTrue(original.stopped);self.assertFalse(streams.markets);self.assertFalse(streams.tasks)
        await streams.close()

if __name__=='__main__':unittest.main()
