"""IBKR futures market state: exact contract identity, no inferred aggressor side."""
from decimal import Decimal
import time
from alpharch_public import Market
from alpharch_ibkr import price_increment

class BrokerMarket(Market):
    def __init__(self, contract, min_tick, rules=None):
        super().__init__('coinbase','BTC')
        self.provider='ibkr';self.asset=str(contract['conId']);self.key='ibkr:'+self.asset
        self.contract=contract;self.symbol=contract.get('localSymbol') or contract['symbol']
        self.tick=Decimal(str(min_tick));self.rules=rules or [];self.sequence=0
        self.data_type=0;self.size_decimals=0
        self.note='Awaiting entitled live futures trades. Aggressor side is not supplied by TWS.'

    def price_tick(self, price=None):
        price=price if price is not None else self.trades[-1]['p'] if self.trades else 0
        value=price_increment(price,self.rules,str(self.tick))
        return Decimal(value) if value else self.tick

    def ingest(self,event):
        kind=event['type'];self.last_message=event['receivedAt']
        if kind=='data_type':self.data_type=event['dataType']
        elif kind=='trade':
            self.sequence+=1
            self.add_trade(str(self.sequence),event['exchangeTime'],event['price'],event['size'],None,event['receivedAt'])
            self.connected=True;self.note='TWS trades do not supply aggressor side; delta and footprints are unavailable.'
        elif kind=='depth':
            # TWS depth callbacks carry local receive time, not an exchange timestamp.
            self.book([(r['price'],r['size']) for r in event['bids']],[(r['price'],r['size']) for r in event['asks']],event['receivedAt'])
        elif kind=='depth_reset':self.bids={};self.asks={};self.book_received=None;self.gap=True
        elif kind=='error':
            self.note=event.get('message','IBKR market-data request failed')
            if event.get('state') in ('not entitled','disconnected','stale'):self.connected=False

    def book(self,bids,asks,ts,replace=True):
        def levels(rows):
            result={}
            for price,size in rows:
                p,q=Decimal(str(price)),Decimal(str(size))
                if not p.is_finite() or not q.is_finite() or q<0:raise ValueError('Invalid futures depth')
                if q:result[p]=result.get(p,Decimal(0))+q
            return result
        bids,asks=levels(bids),levels(asks)
        if bids and asks and max(bids)>=min(asks):
            self.bids={};self.asks={};self.book_received=None;self.gap=True
            raise ValueError('Crossed futures depth')
        self.connected=True;self.bids=bids;self.asks=asks
        self.book_time=float(ts);self.book_received=time.time()
        if self.book_received-self.last_heat>=1 and bids and asks:
            self.last_heat=self.book_received
            self.heat.append({'t':self.book_time,'levels':[[float(p),float(q)] for p,q in list(bids.items())+list(asks.items())]})
        if self.listeners:
            record={'k':'b','ts':self.book_time,'bids':[[str(p),str(q)] for p,q in bids.items()],'asks':[[str(p),str(q)] for p,q in asks.items()]}
            for listener in self.listeners:listener(record)

    def snapshot(self):
        value=super().snapshot();value['contract']=self.contract;value['aggressorKnown']=False
        value['depthTimestamp']='local receive time';value['quantityUnit']='contracts';value['dataType']=self.data_type
        value['note']=self.note
        if self.data_type==0 and self.connected:value['status']='data type unverified'
        if self.data_type in (2,3,4):
            value['status']={2:'frozen',3:'delayed',4:'delayed frozen'}[self.data_type]
            value['book']={'bids':[],'asks':[]}
        return value
