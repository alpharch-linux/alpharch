"""SPECIMEN event-bar arithmetic and boundary semantics."""
from decimal import Decimal
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_aggregation import event_bars
class AggregationTests(unittest.TestCase):
    def rows(self,side='buy'):
        return [dict(t=1700000000+i,p=Decimal(p),q=Decimal(q),side=side) for i,(p,q) in enumerate([('100.00','.1'),('100.25','.2'),('100.75','.4'),('100.50','.5')])]
    def test_tick_count_and_completing_trade_ohlc(self):
        bars=event_bars(self.rows(),'ticks',2,'.25');self.assertEqual(len(bars),2);self.assertEqual(bars[0]['v'],.3);self.assertEqual(bars[0]['end'],1700000001);self.assertEqual(bars[1]['h'],100.75)
    def test_volume_retains_whole_trade_and_exact_total(self):
        bars=event_bars(self.rows(),'volume',.25,'.25');self.assertEqual([b['v'] for b in bars],[.3,.4,.5]);self.assertAlmostEqual(sum(b['v'] for b in bars),1.2)
    def test_range_uses_native_tick_and_does_not_invent_gap_prints(self):
        bars=event_bars(self.rows(),'range',2,'.25');self.assertEqual(bars[0]['h']-bars[0]['l'],.75);self.assertEqual(bars[0]['trades'],3);self.assertFalse(bars[-1]['complete']);self.assertEqual(sum(b['trades'] for b in bars),4)
    def test_unknown_side_stays_unknown(self):
        bars=event_bars(self.rows(None),'ticks',2,'.25');self.assertIsNone(bars[0]['buy']);self.assertIsNone(bars[0]['sell']);self.assertFalse(bars[0]['footprint']);self.assertEqual(bars[0]['v'],.3)
    def test_equal_timestamp_bars_retain_unique_trade_anchors(self):
        rows=self.rows()
        for i,row in enumerate(rows):row.update(t=1700000000.123456,id='trade-'+str(i))
        bars=event_bars(rows,'ticks',1,'.25')
        self.assertEqual([b['startId'] for b in bars],['trade-0','trade-1','trade-2','trade-3'])
        self.assertTrue(all(b['t']==1700000000.123456 and b['end']==b['t'] for b in bars))
        self.assertAlmostEqual(sum(b['v'] for b in bars),1.2)
    def test_invalid_fractional_tick_size(self):
        with self.assertRaises(ValueError):event_bars(self.rows(),'ticks',1.5,'.25')
if __name__=='__main__':unittest.main()
