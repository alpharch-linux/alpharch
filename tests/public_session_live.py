#!/usr/bin/env python3
"""Opt-in real capture/replay and two-browser ownership acceptance, isolated files."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets
ROOT=Path(__file__).resolve().parents[1]

async def run():
    with tempfile.TemporaryDirectory(prefix='alpharch-live-session-') as directory:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env={**os.environ,'ALPHARCH_TAPES':directory}
        process=subprocess.Popen([sys.executable,str(ROOT/'bin/alpharch-chart-server'),'--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            def health():
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as response:return json.load(response)
            for _ in range(50):
                try:health();break
                except OSError:await asyncio.sleep(.1)
            uri=f'ws://127.0.0.1:{port}/ws';origin=f'http://127.0.0.1:{port}'
            async with websockets.connect(uri,origin=origin,max_size=2**24) as first,websockets.connect(uri,origin=origin,max_size=2**24) as second:
                async def request(ws,key,payload):await ws.send(json.dumps({key:payload}))
                async def reply(ws,key,condition=lambda v:True):
                    deadline=time.monotonic()+40
                    while time.monotonic()<deadline:
                        value=json.loads(await asyncio.wait_for(ws.recv(),12))
                        if key in value and condition(value[key]):return value[key]
                        if 'error' in value or 'sessionError' in value:raise AssertionError(value)
                    raise AssertionError('Expected response did not arrive')
                keys=['coinbase:BTC','coinbase:ETH']
                await request(first,'subscribe',keys);await request(second,'subscribe',['coinbase:BTC'])
                seen=set()
                while len(seen)<2:
                    value=await reply(first,'market',lambda m:m['connected'] and bool(m['bars']) and bool(m['book']['bids']))
                    seen.add(value['key'])
                await request(first,'session',{'action':'record','keys':keys});recording=await reply(first,'session')
                assert len(recording['recording'])==2
                await request(first,'subscribe',[])
                # Actual feed events continue because recorder ownership is independent.
                await asyncio.sleep(10)
                assert set(health()['sources'])==set(keys)
                await request(first,'session',{'action':'stop'});stopped=await reply(first,'session')
                assert health()['sources']==['coinbase:BTC']
                await second.close();await asyncio.sleep(1.2)
                assert not health()['sources']
                files=stopped['recordings'];assert len(files)==2
                trades=0
                for file in files:
                    rows=[json.loads(line) for line in (Path(directory)/file).read_text().splitlines()]
                    trades+=sum(row['k']=='t' for row in rows)
                assert trades>0
                await request(first,'session',{'action':'load','files':files});loaded=await reply(first,'session',lambda s:s['replaying'])
                assert loaded['paused'] and loaded['consumed']==0
                await request(first,'session',{'action':'seek','value':1});end=await reply(first,'session',lambda s:s['progress']==1)
                assert end['consumed']==end['events']
                snapshots={}
                while len(snapshots)<2:
                    market=await reply(first,'market',lambda m:m.get('replay'))
                    snapshots[market['key']]=market
                assert len({m['replayClock'] for m in snapshots.values()})==1
                await request(first,'session',{'action':'live'});live=await reply(first,'session',lambda s:not s['replaying'])
                assert not live['streams']
            return {'checkedAtUTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'realCapturedTrades':trades,'recordedEvents':end['events'],'streams':keys,'checks':['two-browser shared source survives one unsubscribe','recorder owns removed chart source','last owner closes underlying sources','exact real capture starts and stops','two tapes share one paused replay clock','seek consumes final event','return live clears replay','temporary test files removed']}
        finally:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':print(json.dumps(asyncio.run(run()),indent=2))
