#!/usr/bin/env python3
import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_execution import PaperAccount
from alpharch_levels import concentrations,options_levels,LevelTracker

class PaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'ledger.sqlite3'
        self.paper=PaperAccount(self.path,'TEST');self.addCleanup(self.paper.db.close)
        self.order={'id':'specimen-order-1','environment':'SIMULATION','account':'SIM-LOCAL',
                    'symbol':'TEST','side':'buy','quantity':3,'kind':'limit','price':100.25}
    def test_explicit_enable_identity_and_alignment(self):
        with self.assertRaises(ValueError):self.paper.submit(self.order,.25)
        self.paper.enabled=True
        with self.assertRaises(ValueError):self.paper.submit({**self.order,'environment':'LIVE'},.25)
        with self.assertRaises(ValueError):self.paper.submit({**self.order,'price':100.1},.25)
    def test_partial_fill_idempotency_staleness_and_restart(self):
        self.paper.enabled=True
        self.paper.submit(self.order,.25);self.paper.submit(self.order,.25)
        self.paper.match({100:10},{100.25:2},1000,1,stale=True)
        self.assertEqual(self.paper.snapshot()['orders'][0]['filled'],0)
        self.paper.match({100:10},{100.25:2},1000,1)
        self.paper.match({100:10},{100.25:2},1000,1)
        self.assertEqual(self.paper.snapshot()['orders'][0]['filled'],2)
        self.paper.match({100:10},{100.25:2},1001,2)
        self.assertEqual(self.paper.snapshot()['orders'][0]['status'],'filled')
        restored=PaperAccount(self.path,'TEST');self.addCleanup(restored.db.close)
        self.assertFalse(restored.enabled)
        self.assertEqual(len(restored.snapshot()['fills']),2)
    def test_cancel_and_client_id_conflict(self):
        self.paper.enabled=True;self.paper.submit(self.order,.25)
        with self.assertRaises(ValueError):self.paper.submit({**self.order,'quantity':2},.25)
        self.paper.cancel(self.order['id'])
        self.paper.match({100:10},{100.25:10},1000,1)
        self.assertEqual(self.paper.snapshot()['orders'][0]['status'],'cancelled')

class LevelTests(unittest.TestCase):
    def test_expiry_and_put_call_separation(self):
        chain=[]
        for expiry,side in [('25DEC26','C'),('25DEC26','P'),('26MAR27','C')]:
            for strike,oi in [(100,1),(110,2),(120,20)]:
                chain.append({'instrument_name':f'BTC-{expiry}-{strike}-{side}','open_interest':oi})
        levels=options_levels(chain,timestamp=1700000000,now=1700000000)
        self.assertEqual(len(levels),3)
        self.assertEqual(len({l['id'] for l in levels}),3)
        self.assertEqual({l['metric'] for l in levels},{'options_open_interest'})
        self.assertEqual(options_levels(chain,timestamp=1700000000,now=1700000200),[])
    def test_lifecycle_dedup_cooldown_and_stale_retirement(self):
        tracker=LevelTracker(cooldown=60)
        levels=concentrations([(100,1),(101,2),(102,20)],source='SPECIMEN',timestamp=1000,instrument='TEST',metric='resting_bid')
        self.assertEqual(len(tracker.update(levels,1000)),1)
        self.assertEqual(tracker.update(levels,1001),[])
        tracker.update([],1002)
        self.assertEqual(tracker.history[-1]['event'],'retired')
        self.assertEqual(tracker.update(levels,1003),[])
        tracker.update(levels,1200)
        self.assertEqual(tracker.active,{})

if __name__=='__main__':unittest.main()
