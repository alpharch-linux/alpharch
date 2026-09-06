"""One browser's local IBKR bridge and resolved futures subscriptions."""
from decimal import Decimal
from itertools import count
from alpharch_ibkr import IBKRBridge, IBKRError
from alpharch_broker_market import BrokerMarket

_CLIENT_IDS=count(71)

class BrokerSession:
    def __init__(self, bridge=None):
        self.bridge=bridge or IBKRBridge()
        self.client_id=next(_CLIENT_IDS)
        self.contracts={};self.markets={};self.requests={};self.rules={}

    def command(self, msg):
        action=msg.get('action')
        if action=='connect':
            self.clear();self.bridge.connect(port=msg.get('port',7497),client_id=msg.get('clientId',self.client_id))
        elif action=='disconnect':self.clear();self.bridge.disconnect()
        elif action=='search':
            self.bridge.search_futures(msg.get('symbol',''),msg.get('exchange','CME'),msg.get('currency','USD'),msg.get('expiry',''))
        elif action=='open':
            ident=msg.get('conId');entry=self.contracts.get(ident)
            if not entry:raise IBKRError('Choose a contract returned by this gateway search.')
            if not entry.get('minTick') or Decimal(entry['minTick'])<=0:raise IBKRError('The contract has no valid price increment.')
            key='ibkr:'+str(ident)
            if key in self.markets:return {'status':self.bridge.status(),'opened':key,'contract':entry}
            if len(self.markets)>=8:raise IBKRError('Close a futures chart before opening another.')
            market=BrokerMarket(entry['contract'],entry['minTick'])
            ids=self.bridge.subscribe(entry['contract'],depth_rows=msg.get('depthRows',10))
            self.markets[key]=market
            for rid in ids.values():self.requests[rid]=key
            for rule in entry.get('marketRules',[]):
                if rule['exchange']==entry['contract']['exchange']:
                    self.rules.setdefault(rule['marketRuleId'],set()).add(key)
                    self.bridge.request_market_rule(rule['marketRuleId'])
            return {'status':self.bridge.status(),'opened':key,'contract':entry}
        elif action!='status':raise IBKRError('Choose a supported IBKR action.')
        return {'status':self.bridge.status(),'clientId':self.client_id}

    def retain(self, keys):
        for key in self.markets.keys()-set(keys):
            for rid in [rid for rid,target in self.requests.items() if target==key]:
                self.bridge.unsubscribe(rid);self.requests.pop(rid,None)
            market=self.markets.pop(key,None)
            if market:market.disconnect('IBKR subscription closed')
            for targets in self.rules.values():targets.discard(key)

    def clear(self):
        self.retain(set());self.contracts.clear();self.rules.clear()

    def poll(self):
        events=self.bridge.poll()
        for event in events:
            kind=event['type']
            if kind=='contract':
                self.contracts[event['contract']['conId']]=event
            elif kind=='market_rule':
                for key in self.rules.get(event['marketRuleId'],set()):
                    if key in self.markets:self.markets[key].rules=event['increments']
            elif kind=='state' and event.get('state')!='connected':
                for market in self.markets.values():market.disconnect(event.get('message','IBKR disconnected'))
            elif kind=='error' and event.get('requestId',-1)<0 and event.get('state') in ('stale','disconnected','resubscribe required'):
                for market in self.markets.values():market.disconnect(event['message'])
            else:
                key=self.requests.get(event.get('requestId'))
                if key in self.markets:
                    try:self.markets[key].ingest(event)
                    except (ValueError,KeyError,TypeError):self.markets[key].disconnect('Invalid futures market update rejected; reconnect to rebuild depth.')
        return {'events':events,'status':self.bridge.status()}

    def close(self):
        self.clear();self.bridge.disconnect()
