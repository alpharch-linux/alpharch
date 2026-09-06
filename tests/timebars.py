"""SPECIMEN vectors for source overlap, custom boundaries and per-chart history."""
from decimal import Decimal
from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_timebars import time_bars, history_resolution, History
from unittest.mock import patch

class TimeBarTests(unittest.TestCase):
    def trade(self,t,p,q='1',side='buy'):
        return dict(t=t,p=Decimal(p),q=Decimal(q),side=side)
    def test_seconds_and_arbitrary_boundary(self):
        trades=[self.trade(151,'100','.1'),self.trade(154,'101','.2'),self.trade(155,'102','.3'),self.trade(225,'103','.4')]
        bars=time_bars(trades,5)
        self.assertEqual([v['t'] for v in bars],[150,155,225])
        self.assertEqual(bars[0]['c'],101)
        self.assertAlmostEqual(sum(b['v'] for b in bars),1)
        self.assertEqual([b['t'] for b in time_bars(trades,75)],[150,225])
        self.assertTrue(bars[0]['partial']);self.assertFalse(bars[-1]['partial'])
    def test_history_and_live_same_four_hour_bar_both_preserved(self):
        history=[dict(t=i*3600,o=100,h=102,l=99,c=101,v=10,buy=None,sell=None,historical=True) for i in (4,5,6,7)]
        trades=[self.trade(7*3600+1200,'105','2'),self.trade(7*3600+1201,'106','3')]
        bars=time_bars(trades,14400,history,3600)
        self.assertEqual(len(bars),1);b=bars[0]
        self.assertEqual((b['o'],b['h'],b['l'],b['c'],b['v']),(100,106,99,106,35))
        self.assertTrue(b['partial']);self.assertIsNone(b['buy']);self.assertIsNone(b['pv'])
    def test_unknown_aggressor_never_becomes_delta(self):
        b=time_bars([self.trade(150,'100',side=None),self.trade(152,'101')],60)[0]
        self.assertIsNone(b['buy']);self.assertIsNone(b['sell']);self.assertEqual(b['footprint'],[[101,0,1]])
    def test_no_fill_of_missing_intervals_or_future_rest_candles(self):
        self.assertEqual([b['t'] for b in time_bars([self.trade(1,'100'),self.trade(121,'101')],60)],[0,120])
    def test_invalid_settings(self):
        for n in [True,0,-1,1.5,float('nan'),31622401]:
            with self.assertRaises(ValueError):time_bars([],n)
    def test_history_resolution_divides_exactly(self):
        self.assertEqual(history_resolution(14400),3600);self.assertEqual(history_resolution(180),60)
        self.assertIsNone(history_resolution(75));self.assertEqual(history_resolution(86400),86400)
    def test_per_chart_size_never_changes_shared_history(self):
        trades=[self.trade(i*60,'100') for i in range(1,25)]
        short=time_bars(trades,60)[-5:];long=time_bars(trades,300)
        self.assertEqual(len(short),5);self.assertEqual(len(trades),24);self.assertEqual(sum(b['v'] for b in long),24)

class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_coinbase_pages_deduplicate_and_exclude_forming(self):
        class Market:provider='coinbase';asset='BTC';key='coinbase:BTC'
        now=3600*2000+123
        def request(url):
            from urllib.parse import urlparse, parse_qs
            from datetime import datetime
            q=parse_qs(urlparse(url).query);start=datetime.fromisoformat(q['start'][0].replace('Z','+00:00')).timestamp();end=datetime.fromisoformat(q['end'][0].replace('Z','+00:00')).timestamp()
            return [[t,99,102,100,101,5] for t in range(int(start),int(end)+3600,3600)]
        h=History();key=('coinbase:BTC',3600,600)
        with patch('alpharch_timebars.request_json',side_effect=request),patch('alpharch_timebars.time.time',return_value=now):
            await h.load(Market(),3600,key,600)
        rows=h.cache[key][1];self.assertEqual(len(rows),600);self.assertEqual(len({v['t'] for v in rows}),600)
        self.assertTrue(all(v['t']+3600<=now and v['buy'] is None for v in rows))
        await h.close()
if __name__=='__main__':unittest.main()
