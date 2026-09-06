#!/usr/bin/env python3
"""SPECIMEN protocol messages verify all existing live adapters offline."""
import json
from pathlib import Path
from unittest.mock import patch
import unittest
from workstation import module, flow

options = module('options', Path(__file__).resolve().parents[1] / 'bin/alphaopt')

class Socket:
    def __init__(self, messages):
        self.messages = messages
        self.sent = []
    async def send(self, value):
        self.sent.append(json.loads(value))
    async def __aiter__(self):
        for message in self.messages:
            yield json.dumps(message)

class Connection:
    def __init__(self, socket):
        self.socket = socket
    async def __aiter__(self):
        yield self.socket

class Feeds(unittest.IsolatedAsyncioTestCase):
    async def run_feed(self, name, messages, *args):
        eng = flow.Engine(.25, 60, 8, 3)
        socket = Socket(messages)
        with patch('websockets.connect', return_value=Connection(socket)):
            await getattr(flow, name)(eng, *args, None, lambda: None)
        return eng, socket

    async def test_coinbase_maker_direction_and_incremental_book(self):
        eng, sock = await self.run_feed('coinbase_feed', [
            {'type':'snapshot','bids':[['100','4']],'asks':[['101','3']]},
            {'type':'l2update','changes':[['buy','100','0'],['buy','99','7']]},
            {'type':'match','side':'buy','price':'100','size':'2'},
        ], 'BTC-USD')
        self.assertEqual(eng.cvd, -2)
        self.assertEqual(eng.bids, {99:7})
        self.assertEqual(sock.sent[0]['product_ids'], ['BTC-USD'])

    async def test_coinbase_exchange_time_duplicate_and_full_snapshot(self):
        trade={'type':'match','trade_id':42,'time':'2026-09-05T00:00:00.123456Z',
               'side':'sell','price':'101','size':'0.00000015'}
        eng,_=await self.run_feed('coinbase_feed',[
            {'type':'snapshot','bids':[[str(100-i*.25),'1'] for i in range(205)],'asks':[['101','2']]},
            trade,dict(trade,type='last_match')], 'BTC-USD')
        self.assertEqual(len(eng.bids),205)
        self.assertEqual(eng.n_trades,1)
        self.assertEqual(eng.tape[-1].ts,1788566400.123456)
        self.assertEqual(eng.cvd,.00000015)

    async def test_binance_spot(self):
        eng, _ = await self.run_feed('binance_feed', [
            {'data':{'bids':[['100','4']],'asks':[['101','3']]}},
            {'data':{'e':'aggTrade','m':False,'T':1700000000000,'p':'101','q':'2'}},
        ], 'BTCUSDT', 'spot')
        self.assertEqual(eng.cvd, 2)
        self.assertTrue(eng.book_ok)

    async def test_binance_perp_liquidations_and_funding(self):
        eng, _ = await self.run_feed('binance_feed', [
            {'data':{'e':'forceOrder','o':{'S':'SELL','T':1700000000000,'ap':'100','p':'100','q':'5'}}},
            {'data':{'e':'markPriceUpdate','r':'.0001','T':1700000000000}},
        ], 'BTCUSDT', 'perp')
        self.assertEqual(eng.liq_long, 5)
        self.assertEqual(eng.funding[0], .0001)

    async def test_hyperliquid_direction_snapshot_funding_oi(self):
        with patch.object(flow, 'hl_universe', return_value=['BTC']):
            eng, sock = await self.run_feed('hyperliquid_feed', [
                {'channel':'trades','data':[{'time':1700000000000,'px':'101','sz':'2','side':'B'}]},
                {'channel':'l2Book','data':{'time':1700000001000,'levels':[[{'px':'100','sz':'4'}],[{'px':'101','sz':'3'}]]}},
                {'channel':'activeAssetCtx','data':{'ctx':{'funding':'.0001','openInterest':'42'}}},
            ], 'BTC')
        self.assertEqual(eng.cvd, 2)
        self.assertEqual(eng.oi[0], 42)
        self.assertEqual(eng.funding_hours, 1)
        self.assertEqual(len(sock.sent), 3)

    async def test_deribit_options_tape(self):
        st = options.OptState()
        sock = Socket([{'params':{'data':[{'instrument_name':'BTC-25DEC26-100000-C','index_price':100000,
                                         'amount':2,'price':.01,'direction':'buy','timestamp':1700000000000,'iv':50}]}}])
        with patch('websockets.connect',return_value=Connection(sock)):
            await options.trades_feed(st, 'BTC')
        self.assertEqual(st.tape[-1]['prem'], 2000)
        self.assertEqual(st.tape[-1]['cp'], 'C')
        self.assertEqual(sock.sent[0]['params']['channels'], ['trades.option.BTC.100ms'])

if __name__ == '__main__':
    unittest.main()
