"""SPECIMEN observations: arithmetic and source/expiry boundaries."""
import asyncio
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_public import Market
from alpharch_insights import observations,Options

class ObservationTests(unittest.TestCase):
    def test_exact_captured_quantities_and_source_labels(self):
        market=Market('coinbase','BTC');market.connected=True;market.tick=Decimal('.01')
        market.add_trade('1',1700000000,'100.01','.00000001','buy');market.add_trade('2',1700000001,'100.02','2','sell')
        market.book([['100','1'],['99','1'],['98','9']],[['101','1'],['102','1'],['103','1']],1700000001)
        facts=observations(market)
        self.assertEqual(facts['volume'],'2.00000001');self.assertEqual(facts['delta'],'-1.99999999');self.assertEqual(facts['high'],'100.02');self.assertEqual(facts['source'],'coinbase');self.assertEqual(facts['levels'][0]['price'],98);self.assertEqual(facts['levels'][0]['ratio'],9)
        market.book_received-=20;self.assertFalse(observations(market)['levels'])

class OptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_options_are_on_demand_and_cached(self):
        options=Options()
        with patch('alpharch_insights.request_json',return_value={'result':[]}) as request:
            self.assertFalse(options.cache);request.assert_not_called()
            first=await options.get('BTC');second=await options.get('BTC')
            self.assertIs(first,second);self.assertEqual(request.call_count,1)
            with self.assertRaises(ValueError):await options.get('SOL')
    async def test_failure_clears_old_levels(self):
        options=Options();options.cache['BTC']={'fetchedAt':0,'levels':[{'SPECIMEN':True}]}
        with patch('alpharch_insights.request_json',side_effect=OSError('offline')):
            result=await options.get('BTC')
        self.assertEqual(result['status'],'unavailable');self.assertFalse(result['levels'])

if __name__=='__main__':unittest.main()
