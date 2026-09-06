"""SPECIMEN IBKR callbacks only; no account or gateway connection."""
from decimal import Decimal
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_broker_market import BrokerMarket
from alpharch_broker_session import BrokerSession
from alpharch_sessions import Sessions
CONTRACT={'conId':1234,'symbol':'NQ','localSymbol':'NQU6','secType':'FUT','exchange':'CME','currency':'USD','lastTradeDateOrContractMonth':'20260918'}
class SpecimenBridge:
    def __init__(self):self.events=[];self.closed=[]
    def poll(self):v=self.events;self.events=[];return v
    def status(self):return {'ready':True,'state':'connected'}
    def subscribe(self,*a,**k):return {'quote':1,'trade':2,'depth':3}
    def request_market_rule(self,*a):pass
    def unsubscribe(self,rid):self.closed.append(rid)
    def disconnect(self):pass

class BrokerSessionTests(unittest.TestCase):
    def test_only_resolved_contracts_can_open_and_ticks_follow_rules(self):
        bridge=SpecimenBridge();session=BrokerSession(bridge)
        with self.assertRaises(ValueError):session.command({'action':'open','conId':1234})
        bridge.events=[{'type':'contract','contract':CONTRACT,'minTick':'.25','marketRules':[{'exchange':'CME','marketRuleId':26}]}];session.poll();session.command({'action':'open','conId':1234})
        bridge.events=[{'type':'market_rule','marketRuleId':26,'increments':[{'lowEdge':'0','increment':'.25'}]}];session.poll()
        self.assertEqual(session.markets['ibkr:1234'].price_tick(100),Decimal('.25'))
        session.retain(set());self.assertEqual(bridge.closed,[1,2,3]);self.assertFalse(session.markets)
    def test_trades_keep_unknown_aggressor_and_quote_does_not_create_volume(self):
        market=BrokerMarket(CONTRACT,'.25');market.ingest({'type':'quote','receivedAt':1700000000,'field':'last','value':'20000.25'})
        self.assertFalse(market.trades)
        market.ingest({'type':'trade','receivedAt':1700000001,'exchangeTime':1700000000,'price':'20000.25','size':'2','side':None})
        s=market.snapshot();self.assertEqual(s['bars'][0]['v'],2);self.assertIsNone(s['bars'][0]['buy']);self.assertIsNone(s['tape'][0]['a']);self.assertFalse(s['bars'][0]['footprint']);self.assertEqual(s['profile'][0],[20000.25,0,0,2]);self.assertFalse(s['aggressorKnown'])
    def test_record_replay_preserves_futures_identity_and_unknown_side(self):
        with tempfile.TemporaryDirectory() as folder:
            market=BrokerMarket(CONTRACT,'.25');market.connected=True;market.data_type=1
            manager=Sessions({'ibkr:1234':market},folder);manager.record(['ibkr:1234'])
            market.ingest({'type':'trade','receivedAt':1700000001,'exchangeTime':1700000000,'price':'20000.25','size':'2','side':None})
            manager.stop();manager.load(manager.files());manager.seek(1);s=manager.snapshots()[0]
            self.assertEqual(s['contract']['conId'],1234);self.assertEqual(s['tick'],.25);self.assertIsNone(s['tape'][0]['a']);self.assertTrue(s['replay'])
    def test_negative_prices_and_duplicate_price_levels_retain_all_quantity(self):
        market=BrokerMarket(CONTRACT,'.25')
        market.book([['-10.25','2'],['-10.25','3']],[['-10.00','4']],1700000000)
        self.assertEqual(market.bids[Decimal('-10.25')],Decimal('5'))
        market.ingest({'type':'trade','receivedAt':1700000001,'exchangeTime':1700000000,'price':'-10.00','size':'2','side':None})
        self.assertEqual(market.snapshot()['last'],-10)
    def test_future_quote_type_cannot_relabel_delayed_trades_as_live(self):
        market=BrokerMarket(CONTRACT,'.25')
        market.ingest({'type':'data_type','receivedAt':1700000000,'dataType':3})
        market.ingest({'type':'trade','receivedAt':1700000001,'exchangeTime':1700000000,'price':'20000.25','size':'1','side':None})
        self.assertEqual(market.snapshot()['status'],'delayed')
    def test_delayed_market_cannot_show_depth_as_live(self):
        market=BrokerMarket(CONTRACT,'.25');market.connected=True;market.data_type=3
        self.assertEqual(market.snapshot()['status'],'delayed');self.assertFalse(market.snapshot()['book']['bids'])
if __name__=='__main__':unittest.main()
