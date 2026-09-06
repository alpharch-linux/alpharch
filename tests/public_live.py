#!/usr/bin/env python3
"""Explicit live check against an already-running local chart server."""
import argparse
import asyncio
from decimal import Decimal
import json
import time
import websockets

async def check(port):
    url=f'ws://127.0.0.1:{port}/ws'
    origin=f'http://127.0.0.1:{port}'
    try:
        async with websockets.connect(url,origin='https://untrusted.example',open_timeout=5):
            raise AssertionError('Foreign origin was accepted')
    except websockets.exceptions.InvalidStatus as e:
        assert e.response.status_code==403
    evidence={}
    async with websockets.connect(url,origin=origin,max_size=2**24) as ws:
        await ws.send(json.dumps({'subscribe':['coinbase:NQ']}))
        assert 'error' in json.loads(await ws.recv())
        keys=[p+':'+a for p in ['coinbase','hyperliquid','kraken'] for a in ['BTC','ETH','SOL']]
        await ws.send(json.dumps({'subscribe':keys}))
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            payload=json.loads(await asyncio.wait_for(ws.recv(),10));m=payload.get('market')
            if not m or not m['bars'] or not m['historical'] or not m['book']['bids'] or not m['book']['asks']:continue
            assert m['key'] in keys
            assert Decimal(m['book']['bids'][0][0])<Decimal(m['book']['asks'][0][0])
            assert m['bookAge']<15
            assert m['tradeTime']<=m['receivedAt']+5
            assert all(v['buy'] is None and v['sell'] is None for v in m['historical'])
            for b in m['bars']:
                assert b['h']>=max(b['o'],b['c']) and b['l']<=min(b['o'],b['c'])
                assert abs(b['v']-b['buy']-b['sell'])<1e-8
                assert abs(sum(r[1]+r[2] for r in b['footprint'])-b['v'])<1e-8
            evidence[m['key']]={'status':m['status'],'tick':m['tick'],'historicalCandles':len(m['historical']),'capturedBars':len(m['bars']),'bookLevelsPerSide':len(m['book']['bids']),'capturedTradesShown':len(m['tape']),'heatSamples':len(m['heat']),'captureHasGaps':m['incomplete']}
            if len(evidence)==9:break
        assert len(evidence)==9,sorted(evidence)
    return {'checkedAtUTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks':['foreign origin rejected','unsupported market rejected','nine real trade/book/candle streams','non-crossed fresh books','exchange timestamp sanity','historical side classification stays unknown','OHLC and exact footprint volume conservation'],'sources':evidence}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=17863);args=parser.parse_args();print(json.dumps(asyncio.run(check(args.port)),indent=2))
