#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_indicators import calculate

class Indicators(unittest.TestCase):
    def bars(self,values):return [dict(open=v,high=v+1,low=v-1,close=v,volume=10) for v in values]
    def test_sma_ema_warmup_and_values(self):
        bars=self.bars([1,2,3,4,5])
        self.assertEqual(calculate(bars,'sma',3)['value'],[None,None,2,3,4])
        self.assertEqual(calculate(bars,'ema',3)['value'],[None,None,2,3,4])
    def test_rsi_up_down_flat(self):
        for values,expected in [(range(20),100),(range(20,0,-1),0),([10]*20,50)]:
            out=calculate(self.bars(values),'rsi',14)['value']
            self.assertTrue(all(v is None for v in out[:14]));self.assertEqual(out[-1],expected)
    def test_wilder_atr_and_bollinger(self):
        bars=self.bars([10]*20)
        self.assertEqual(calculate(bars,'atr',14)['value'][-1],2)
        bb=calculate(self.bars([1,2,3]),'bollinger',3)
        self.assertAlmostEqual(bb['upper'][-1],2+2*(2/3)**.5)
    def test_macd_and_stochastic_constant(self):
        bars=self.bars([10]*50)
        macd=calculate(bars,'macd')['histogram']
        self.assertTrue(all(v is None for v in macd[:33]));self.assertEqual(macd[-1],0)
        self.assertEqual(calculate(bars,'stochastic')['value'][-1],50)
    def test_replay_prefix_consistency_and_source(self):
        bars=self.bars(range(100))
        for name in ('sma','ema','rsi','macd','atr','bollinger','stochastic','volume'):
            long=calculate(bars,name)
            short=calculate(bars[:50],name)
            self.assertEqual({k:v[:50] for k,v in long.items()},short)
        self.assertEqual(calculate(bars,'sma',2,'high')['value'][1],1.5)

if __name__=='__main__':unittest.main()
