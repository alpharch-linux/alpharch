#!/usr/bin/env python3
"""Protocol fixtures and precision checks for read-only public chart data."""
import unittest
import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_public import Market

class PublicData(unittest.TestCase):
    def market(self,provider='coinbase'):
        m=Market(provider,'BTC');m.tick=Decimal('.01');m.connected=True;return m
    def test_exchange_timestamp_and_maker_inversion(self):
        m=self.market();m.ingest_coinbase({'type':'match','product_id':'BTC-USD','trade_id':1,'time':'2026-09-05T00:00:00.123456Z','price':'79641.67','size':'0.00000015','side':'buy'})
        t=m.trades[0];self.assertEqual(t['p'],Decimal('79641.67'));self.assertEqual(t['q'],Decimal('.00000015'));self.assertEqual(t['side'],'sell');self.assertEqual(t['t'],1788566400.123456)
    def test_duplicate_does_not_change_volume(self):
        m=self.market();self.assertTrue(m.add_trade('1',1700000000,'100','.00000015','buy'));self.assertFalse(m.add_trade('1',1700000000,'100','.00000015','buy'));s=m.snapshot();self.assertEqual(s['bars'][0]['v'],.00000015);self.assertEqual(s['tape'][0]['s'],'1.5E-7')
    def test_partial_book_zero_delete(self):
        m=self.market();m.book([['100','2'],['99','3']],[['101','4']],1700000000);m.book([['100','0'],['98','2']],[],1700000001,False);self.assertEqual(m.bids,{Decimal(99):Decimal(3),Decimal(98):Decimal(2)})
    def test_crossed_book_rejected(self):
        m=self.market()
        with self.assertRaises(ValueError):m.book([['102','2']],[['101','3']],1700000000)
        self.assertFalse(m.bids)
    def test_nan_and_negative_rejected(self):
        m=self.market()
        for p,q in [('NaN','1'),('100','-1'),('100','0'),('0','1')]:
            with self.assertRaises(ValueError):m.add_trade(p+q,1700000000,p,q,'buy')
    def test_unknown_side_rejected(self):
        with self.assertRaises(ValueError):self.market().add_trade('1',1700000000,'100','1','unknown')
    def test_trade_gap_is_explicit(self):
        m=self.market()
        for ident in [1,3]:m.ingest_coinbase({'type':'match','trade_id':ident,'time':'2026-09-05T00:00:00Z','price':'100','size':'1','side':'sell'})
        self.assertTrue(m.snapshot()['incomplete'])
    def test_disconnected_book_is_never_served_as_fresh(self):
        m=self.market();m.book([['100','2']],[['101','3']],1700000000);m.disconnect();s=m.snapshot();self.assertEqual(s['book']['bids'],[]);self.assertEqual(s['status'],'disconnected')
    def test_old_book_hidden_independently_of_trades(self):
        m=self.market();m.book([['100','2']],[['101','3']],1700000000);m.book_received-=20;m.add_trade('1',1700000000,'100','1','buy');self.assertEqual(m.snapshot()['book']['asks'],[])
    def test_hyperliquid_taker_side_and_exact_book(self):
        m=self.market('hyperliquid');m.ingest_hyperliquid({'channel':'trades','data':[{'coin':'BTC','tid':1,'time':1700000000123,'px':'79597.0','sz':'.00001','side':'B'}]});self.assertEqual(m.trades[0]['side'],'buy');self.assertEqual(m.trades[0]['t'],1700000000.123)
        m.ingest_hyperliquid({'channel':'l2Book','data':{'coin':'BTC','time':1700000000123,'levels':[[{'px':'79596','sz':'2'}],[{'px':'79597','sz':'3'}]]}});self.assertEqual(m.snapshot()['book']['bids'][0],['79596','2'])
    def test_hyperliquid_tick_magnitude_rule(self):
        m=self.market('hyperliquid');m.tick=Decimal('.001')
        self.assertEqual(m.price_tick(Decimal('79600')),Decimal(1));self.assertEqual(m.price_tick(Decimal('2451')),Decimal('.1'));self.assertEqual(m.price_tick(Decimal('101')),Decimal('.01'));self.assertEqual(m.price_tick(Decimal('123456')),Decimal(1))
    def test_real_footprint_profile_volume_conservation(self):
        m=self.market();m.add_trade('1',1700000000,'100.25','.00000015','buy');m.add_trade('2',1700000001,'100.25','2','sell');m.add_trade('3',1700000002,'100.50','3','buy');s=m.snapshot();b=s['bars'][0]
        self.assertEqual(b['v'],5.00000015);self.assertEqual(b['buy'],3.00000015);self.assertEqual(b['sell'],2);self.assertEqual(b['footprint'],[[100.25,2,.00000015],[100.5,0,3]]);self.assertEqual(s['profile'],[[100.25,.00000015,2],[100.5,3,0]])
    def test_out_of_order_trade_ohlc_uses_exchange_time(self):
        m=self.market();m.add_trade('2',1700000002,'102','1','buy');m.add_trade('1',1700000001,'101','1','buy');s=m.snapshot();self.assertEqual(s['bars'][0]['o'],101);self.assertEqual(s['bars'][0]['c'],102);self.assertEqual(s['last'],102)
    def test_equal_timestamp_numeric_trade_order(self):
        m=self.market();m.add_trade('9',1700000000,'99','1','buy');m.add_trade('10',1700000000,'100','1','buy')
        self.assertEqual(m.snapshot()['last'],100)
    def test_trade_cache_reuse_and_invalidation(self):
        m=self.market();m.add_trade('1',1700000000,'100','1','buy');first=m.trade_data()[0]
        self.assertIs(m.trade_data()[0],first)
        m.add_trade('2',1700000001,'101','2','sell');self.assertIsNot(m.trade_data()[0],first)
        self.assertEqual(m.snapshot()['bars'][0]['v'],3)
    def test_retention_rebuilds_ohlc_and_profile_exactly(self):
        from collections import deque
        m=self.market();m.trades=deque(maxlen=3)
        m.add_trade('1',1700000000,'100','1','buy');m.add_trade('2',1700000001,'101','2','sell');m.add_trade('3',1700000002,'102','3','buy');m.snapshot()
        m.add_trade('4',1700000003,'103','4','sell');s=m.snapshot()
        self.assertEqual(s['bars'][0]['o'],101);self.assertEqual(s['bars'][0]['v'],9)
        self.assertEqual(sum(r[1]+r[2] for r in s['profile']),9);self.assertNotIn(100,[r[0] for r in s['profile']])
    def test_kraken_snapshot_checksum_and_fail_closed(self):
        m=self.market('kraken')
        bids={Decimal('100.0'):Decimal('0.10000000')};asks={Decimal('100.1'):Decimal('1.00000000')}
        data={'symbol':'BTC/USD','bids':[{'price':p,'qty':q} for p,q in bids.items()],'asks':[{'price':p,'qty':q} for p,q in asks.items()],'checksum':m.kraken_checksum(bids,asks)}
        m.ingest_kraken({'channel':'book','type':'snapshot','data':[data]})
        self.assertEqual(m.bids,bids)
        with self.assertRaises(ValueError):m.ingest_kraken({'channel':'book','type':'update','data':[dict(data,checksum=0)]})
        self.assertFalse(m.bids);self.assertFalse(m.connected)
    def test_kraken_taker_side_and_decimal_precision(self):
        m=self.market('kraken');m.tick=Decimal('.1')
        m.ingest_kraken({'channel':'trade','data':[{'symbol':'BTC/USD','trade_id':12,'timestamp':'2026-09-05T00:00:00.123456Z','price':Decimal('79959.9'),'qty':Decimal('.00000001'),'side':'buy'}]})
        self.assertEqual(m.trades[0]['side'],'buy');self.assertEqual(m.trades[0]['q'],Decimal('.00000001'));self.assertEqual(m.price_tick(),Decimal('.1'))
    def test_unsupported_market_fails_closed(self):
        with self.assertRaises(ValueError):Market('coinbase','NQ')

if __name__=='__main__':unittest.main()
