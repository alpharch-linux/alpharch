"""Real JSONL capture and a shared exchange-time replay clock for the live desk."""
import bisect
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import time
from alpharch_public import Market, ASSETS, PROVIDERS, decimal
from alpharch_broker_market import BrokerMarket


class Sessions:
    def __init__(self, markets, directory=None):
        self.markets = markets
        self.directory = Path(directory or os.environ.get('ALPHARCH_TAPES', Path.home()/'tapes'))
        self.recorders = {}
        self.events = []
        self.times = []
        self.headers = {}
        self.replay = {}
        self.index = 0
        self.clock = 0
        self.paused = True
        self.speed = 1
        self.last_wall = time.monotonic()
        self.error = ''

    def files(self):
        return sorted(p.name for p in self.directory.glob('*.jsonl') if p.is_file() and not p.is_symlink())[-100:]

    def status(self):
        return {'recordings': self.files(), 'recording': list(self.recorders),
                'recordFiles': [v['path'].name for v in self.recorders.values()],
                'replaying': bool(self.headers), 'paused': self.paused, 'speed': self.speed,
                'clock': self.clock, 'progress': self.index/len(self.events) if self.events else 0,
                'events': len(self.events), 'consumed': self.index, 'streams': list(self.headers),'contracts': {key:{**h['contract'],'minTick':h['tick']} for key,h in self.headers.items() if h.get('contract')},
                'error': self.error, 'scope': 'Exact received trades; top 100 available depth levels per side sampled at most once per second.'}

    def record(self, keys):
        if not isinstance(keys, list) or not 1 <= len(keys) <= 9 or len(set(keys)) != len(keys):
            raise ValueError('Choose one to nine active market streams.')
        if self.headers:
            raise ValueError('Return to live data before recording.')
        if any(k not in self.markets or not self.markets[k].connected or not self.markets[k].tick for k in keys):
            raise ValueError('Wait for every selected live market to connect.')
        self.error=''
        self.directory.mkdir(parents=True, exist_ok=True)
        for key in keys:
            if key in self.recorders:
                continue
            market = self.markets[key]
            path = self.directory/(key.replace(':','-')+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()%1000000)+'.jsonl')
            handle = path.open('x', buffering=1)
            handle.write(json.dumps({'k':'h','ts':time.time(),'feed':market.provider,'symbol':market.symbol,
                         'asset':market.asset,'tick':str(market.price_tick()),'contract':getattr(market,'contract',None),'dataType':getattr(market,'data_type',None), 'size_decimals':market.size_decimals,
                         'depth_levels':100,'depth_sampling_seconds':1,'depth_timestamp':'exchange timestamp when supplied, otherwise local receive time'})+'\n')
            recorder = {'path':path,'handle':handle,'lastBook':0,'listener':None}
            def capture(event, recorder=recorder):
                if recorder['handle'].closed:
                    return
                if event['k']=='b':
                    now=time.monotonic()
                    if now-recorder['lastBook'] < 1:
                        return
                    recorder['lastBook']=now
                try:
                    recorder['handle'].write(json.dumps(event,allow_nan=False)+'\n')
                except (OSError,ValueError):
                    self.error='Recording stopped after a file write failure. Check available disk space.'
                    recorder['handle'].close()
            recorder['listener']=capture
            self.recorders[key]=recorder
            market.listeners.append(capture)

    def stop(self,keys=None):
        for key, recorder in list(self.recorders.items()):
            if keys is not None and key not in keys:continue
            market=self.markets.get(key)
            if market and recorder['listener'] in market.listeners:
                market.listeners.remove(recorder['listener'])
            recorder['handle'].close()
            self.recorders.pop(key,None)

    def load(self, names):
        if not isinstance(names,list) or not 1<=len(names)<=9 or len(set(names))!=len(names):
            raise ValueError('Choose one to nine different local recordings.')
        available=self.files()
        if any(n not in available for n in names):
            raise ValueError('Choose a recording from the local catalog.')
        if sum((self.directory/n).stat().st_size for n in names)>100*1024*1024:
            raise ValueError('This replay exceeds the 100 MB session limit. Select fewer recordings.')
        events=[];headers={}
        for name in names:
            with (self.directory/name).open() as handle:
                header=json.loads(handle.readline())
                if header.get('k')!='h' or header.get('feed') not in (*PROVIDERS,'ibkr'):
                    raise ValueError('This tape needs the advanced replay tool; the desk supports named Coinbase, Hyperliquid and Kraken crypto tapes.')
                asset=header.get('asset') or str(header.get('symbol','')).split('-')[0].replace('USDT','').replace('USD','')
                if (asset not in ASSETS and not (header['feed']=='ibkr' and str(asset).isdigit() and isinstance(header.get('contract'),dict) and header['contract'].get('conId')==int(asset))) or not header.get('tick'):
                    raise ValueError('This tape has no supported symbol/tick metadata. Use advanced replay.')
                tick=decimal(header['tick'],True)
                key=header['feed']+':'+asset
                if key in headers:
                    raise ValueError('Choose only one recording per provider and instrument.')
                headers[key]={**header,'asset':asset,'tick':str(tick)}
                for line_no,line in enumerate(handle,2):
                    row=json.loads(line)
                    if row.get('k') not in ('t','b','g'):
                        continue
                    ts=float(row['ts'])
                    if not math.isfinite(ts) or ts<=0:
                        raise ValueError('Invalid recording timestamp.')
                    if row['k']=='t':
                        price=Decimal(str(row['p']))
                        if not price.is_finite() or (header['feed']!='ibkr' and price<=0):raise ValueError('Invalid recorded price.')
                        decimal(row['s'],True)
                        if row.get('a') not in ('buy','sell') and not (header['feed']=='ibkr' and row.get('a') is None):
                            raise ValueError('Unclassified trade in recording.')
                    elif row['k']=='b':
                        for side in ('bids','asks'):
                            if not isinstance(row.get(side),list) or len(row[side])>1000:
                                raise ValueError('Invalid recorded depth.')
                            for p,q in row[side]:
                                value=Decimal(str(p))
                                if not value.is_finite() or (header['feed']!='ibkr' and value<=0):raise ValueError('Invalid depth price')
                                decimal(q)
                    events.append((ts,key,line_no,row))
                    if len(events)>500000:
                        raise ValueError('This replay exceeds 500,000 events.')
        if not events:
            raise ValueError('The selected tapes contain no replayable events.')
        events.sort(key=lambda v:(v[0],v[1],v[2]))
        self.stop();self.headers=headers;self.events=events;self.times=[v[0] for v in events]
        self.paused=True;self.speed=1;self.reset();self.clock=events[0][0];self.last_wall=time.monotonic()

    def reset(self):
        self.replay={}
        for key,header in self.headers.items():
            market=BrokerMarket(header['contract'],header['tick']) if header['feed']=='ibkr' else Market(header['feed'],header['asset']);market.tick=Decimal(header['tick'])
            if header['feed']=='ibkr':market.data_type=header.get('dataType',0)
            market.size_decimals=int(header.get('size_decimals',8));market.connected=True
            self.replay[key]=market
        self.index=0

    def consume(self, count):
        while self.index<min(count,len(self.events)):
            ts,key,line,row=self.events[self.index];market=self.replay[key]
            if row['k']=='t':market.add_trade(str(row.get('id',line)),ts,row['p'],row['s'],row['a'])
            elif row['k']=='b':
                market.last_heat=0
                market.book(row['bids'],row['asks'],ts)
            elif row['k']=='g':market.gap=True;market.bids={};market.asks={}
            market.last_message=time.time();self.clock=ts;self.index+=1

    def seek(self, fraction):
        if not isinstance(fraction,(int,float)) or not math.isfinite(fraction) or not 0<=fraction<=1:
            raise ValueError('Replay position must be between zero and one.')
        target=round(fraction*len(self.events));self.reset();self.consume(target)
        if not target:self.clock=self.events[0][0]
        self.paused=True;self.last_wall=time.monotonic()

    def advance(self):
        now=time.monotonic();elapsed=now-self.last_wall;self.last_wall=now
        if self.events and not self.paused:
            target_time=self.clock+elapsed*self.speed
            self.consume(bisect.bisect_right(self.times,target_time));self.clock=min(target_time,self.times[-1])
            if self.index==len(self.events):self.paused=True

    def snapshots(self):
        result=[]
        for market in self.replay.values():
            market.book_received=time.time() if market.book_time else None
            market.last_message=time.time();market.connected=True
            snapshot=market.snapshot();snapshot['replay']=True;snapshot['replayClock']=self.clock
            snapshot['status']='replay paused' if self.paused else 'replay playing'
            snapshot['tradeAge']=self.clock-snapshot['tradeTime'] if snapshot['tradeTime'] else None
            snapshot['bookAge']=self.clock-market.book_time if market.book_time else None
            if snapshot['bookAge'] is None or snapshot['bookAge']>15:snapshot['book']={'bids':[],'asks':[]}
            result.append(snapshot)
        return result

    def command(self,msg):
        action=msg.get('action')
        if action=='catalog':pass
        elif action=='record':self.record(msg.get('keys'))
        elif action=='stop':self.stop()
        elif action=='load':self.load(msg.get('files'))
        elif action=='live':self.events=[];self.times=[];self.headers={};self.replay={};self.paused=True
        elif action in ('play','pause','step','seek','speed'):
            if not self.events:raise ValueError('Load a recording first.')
            if action=='play':self.paused=False;self.last_wall=time.monotonic()
            elif action=='pause':self.paused=True
            elif action=='step':self.paused=True;self.consume(self.index+1)
            elif action=='seek':self.seek(msg.get('value'))
            elif action=='speed':
                if msg.get('value') not in (.25,.5,1,2,5,10,25):raise ValueError('Choose a supported replay speed.')
                self.speed=msg['value'];self.last_wall=time.monotonic()
        else:raise ValueError('Unknown session action.')
        return self.status()
