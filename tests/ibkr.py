"""Offline SDK-boundary specimens. Never opens a broker connection."""
from decimal import Decimal
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from alpharch_ibkr import IBKRBridge, IBKRError, contract_spec, number, price_increment


class Wrapper:
    pass


class Client:
    def __init__(self, wrapper):
        self.wrapper=wrapper;self.calls=[];self.stop=threading.Event();self.started=threading.Event()
    def connect(self, host, port, clientId):
        self.calls.append(('connect',host,port,clientId))
        self.started.set()
    def run(self): self.stop.wait(3)
    def disconnect(self): self.stop.set()
    def reqContractDetails(self,*args): self.calls.append(('details',*args))
    def reqMarketRule(self,*args): self.calls.append(('rule',*args))
    def reqMarketDataType(self,*args): self.calls.append(('data_type',*args))
    def reqMktData(self,*args): self.calls.append(('quote',*args))
    def reqTickByTickData(self,*args): self.calls.append(('trade',*args))
    def reqMktDepth(self,*args): self.calls.append(('depth',*args))
    def cancelMktData(self,*args): self.calls.append(('cancel_quote',*args))
    def cancelTickByTickData(self,*args): self.calls.append(('cancel_trade',*args))
    def cancelMktDepth(self,*args): self.calls.append(('cancel_depth',*args))


SPEC = dict(conId=12345,symbol='ES',secType='FUT',exchange='CME',currency='USD',lastTradeDateOrContractMonth='202609')


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.bridge=IBKRBridge(sdk_loader=lambda:(Client,Wrapper,Obj),handshake_timeout=2)
        self.bridge.connect()
        self.client=self.bridge._client
        self.assertTrue(self.client.started.wait(1))
    def tearDown(self): self.bridge.disconnect()
    def ready(self):
        self.client.nextValidId(7654321)
        self.bridge.poll()
    def test_api_handshake_not_tcp_connect_controls_ready(self):
        self.assertFalse(self.bridge.status()['ready'])
        with self.assertRaises(IBKRError): self.bridge.subscribe(SPEC)
        self.ready();self.assertTrue(self.bridge.status()['ready'])
        self.assertNotIn('7654321',str(self.bridge.poll()))
    def test_accounts_are_owner_local_and_forgotten(self):
        self.client.managedAccounts('DU_SPECIMEN_1,DU_SPECIMEN_2,')
        events=self.bridge.poll();accounts=next(e for e in events if e['type']=='accounts')
        self.assertEqual(accounts['accounts'],['DU_SPECIMEN_1','DU_SPECIMEN_2'])
        self.bridge.disconnect();self.assertEqual(self.bridge.status()['accountCount'],0)
    def test_missing_sdk_does_not_break_import_or_fake_connected(self):
        def absent(): raise ModuleNotFoundError('ibapi')
        b=IBKRBridge(sdk_loader=absent)
        self.assertFalse(b.connect());self.assertEqual(b.status()['state'],'setup required')
        self.assertFalse(b.status()['ready'])
    def test_only_loopback_and_nonzero_client_ids_allowed(self):
        for values in ({'host':'broker.example'},{'host':'192.168.1.3'},{'host':'127.0.0.1.evil'},{'client_id':0},{'port':True}):
            with self.assertRaises(IBKRError): self.bridge.connect(**values)
    def test_futures_search_requests_contract_details_not_stock_matching(self):
        self.ready();rid=self.bridge.search_futures('nq',expiry='202609')
        call=self.client.calls[-1]
        self.assertEqual(call[:2],('details',rid));self.assertEqual(call[2].secType,'FUT')
        self.assertEqual(call[2].symbol,'NQ');self.assertEqual(call[2].lastTradeDateOrContractMonth,'202609')
    def test_contract_identity_tick_rules_and_completion(self):
        self.ready();rid=self.bridge.search_futures('ES')
        details=Obj(contract=Obj(**SPEC),minTick=.25,validExchanges='CME,SMART',marketRuleIds='26,27',timeZoneId='US/Central',tradingHours='SPECIMEN')
        self.client.contractDetails(rid,details);self.client.contractDetailsEnd(rid)
        event,end=self.bridge.poll()
        self.assertEqual(event['minTick'],'0.25');self.assertEqual(event['contract']['conId'],12345)
        self.assertEqual(event['marketRules'],[{'exchange':'CME','marketRuleId':26},{'exchange':'SMART','marketRuleId':27}])
        self.assertEqual(end['type'],'contract_end');self.assertNotIn(rid,self.bridge._requests)
    def test_market_rule_increment_is_price_dependent(self):
        self.ready();self.bridge.request_market_rule(26)
        self.client.marketRule(26,[Obj(lowEdge=0,increment=.25),Obj(lowEdge=100,increment=.5)])
        event=self.bridge.poll()[0]
        self.assertEqual(price_increment('99.75',event['increments']),'0.25')
        self.assertEqual(price_increment('100',event['increments']),'0.5')
        self.assertEqual(price_increment('-10',event['increments'],'.01'),'0.01')
        self.assertIsNone(price_increment('-10',event['increments']))
    def test_subscribe_only_uses_read_operations_and_resolved_futures(self):
        self.ready();ids=self.bridge.subscribe(SPEC,depth_rows=20)
        self.assertEqual(set(ids),{'quote','trade','depth'})
        trade=next(c for c in self.client.calls if c[0]=='trade')
        self.assertEqual(trade[3:],('Last',0,False))
        depth=next(c for c in self.client.calls if c[0]=='depth')
        self.assertEqual(depth[3:],(20,False,[]))
        for invalid in ({**SPEC,'secType':'CONTFUT'},{k:v for k,v in SPEC.items() if k!='conId'}, {**SPEC,'password':'SECRET'}):
            with self.assertRaises(IBKRError):self.bridge.subscribe(invalid)
        self.assertFalse(hasattr(self.bridge,'placeOrder'))
    def test_quote_and_size_are_not_trade_events(self):
        self.ready();rid=self.bridge.subscribe(SPEC,trades=False,depth_rows=0)['quote']
        self.client.marketDataType(rid,3)
        self.client.tickPrice(rid,66,6000.25,Obj())
        self.client.tickSize(rid,69,Decimal('10.0000000001'))
        events=self.bridge.poll()
        self.assertEqual([e['type'] for e in events],['data_type','quote','quote_size'])
        self.assertEqual(events[1]['dataType'],3);self.assertIsNone(events[1]['exchangeTime'])
        self.assertEqual(events[2]['value'],'10.0000000001')
    def test_trade_preserves_size_and_unknown_aggressor(self):
        self.ready();rid=self.bridge.subscribe(SPEC,depth_rows=0)['trade']
        self.client.tickByTickAllLast(rid,1,1700000000,-.25,Decimal('2.125'),Obj(pastLimit=False,unreported=False),'CME','')
        event=self.bridge.poll()[0]
        self.assertEqual(event['price'],'-0.25');self.assertEqual(event['size'],'2.125')
        self.assertIsNone(event['side']);self.assertEqual(event['exchangeTime'],1700000000)
    def test_depth_positional_insert_update_delete_and_copy(self):
        self.ready();rid=self.bridge.subscribe(SPEC,trades=False)['depth']
        self.client.updateMktDepth(rid,0,0,1,6000.25,Decimal('3'))
        first=self.bridge.poll()[0]
        self.client.updateMktDepth(rid,1,0,1,6000,Decimal('5'))
        self.client.updateMktDepthL2(rid,0,'CME',1,1,6000.25,Decimal('9'),False)
        self.client.updateMktDepth(rid,1,2,1,0,0)
        events=self.bridge.poll();last=events[-1]
        self.assertEqual(first['bids'][0]['size'],'3');self.assertEqual(last['bids'],[{'price':'6000.25','size':'9','marketMaker':'CME'}])
        self.assertEqual(last['asks'],[]);self.assertIsNone(last['exchangeTime'])
    def test_reset_and_bad_positions_clear_old_depth(self):
        self.ready();rid=self.bridge.subscribe(SPEC,trades=False)['depth']
        self.client.updateMktDepth(rid,0,0,0,6000.5,Decimal('3'))
        self.client.error(rid,317,'Sensitive raw message')
        self.client.updateMktDepth(rid,5,1,0,6000.5,Decimal('3'))
        resets=[e for e in self.bridge.poll() if e['type']=='depth_reset']
        self.assertEqual(len(resets),2);self.assertEqual(resets[0]['asks'],[])
    def test_error_signatures_redact_remote_text_and_flag_entitlement(self):
        self.ready();rid=self.bridge.subscribe(SPEC,trades=False,depth_rows=0)['quote']
        self.client.error(rid,354,'account DU_SECRET invalid', '{secret}')
        self.client.error(rid,1700000000,10090,'account DU_SECRET','{secret}')
        events=self.bridge.poll()
        self.assertEqual([e['state'] for e in events],['not entitled','not entitled'])
        self.assertNotIn('SECRET',str(events));self.assertNotIn('{secret}',str(events))
    def test_data_farm_restore_does_not_silently_mark_prices_live(self):
        self.ready();self.client.error(-1,1100,'lost')
        self.assertFalse(self.bridge.status()['ready'])
        self.client.error(-1,1102,'restored')
        self.assertEqual(self.bridge.status()['state'],'resubscribe required')
        self.assertFalse(self.bridge.status()['ready'])
    def test_unsubscribe_cancels_correct_requests_and_discards_late_events(self):
        self.ready();ids=self.bridge.subscribe(SPEC)
        for rid in ids.values():self.bridge.unsubscribe(rid)
        self.bridge.poll();self.client.tickPrice(ids['quote'],1,6000,Obj())
        self.assertEqual(self.bridge.poll(),[])
        self.assertEqual({c[0] for c in self.client.calls if c[0].startswith('cancel_')},{'cancel_quote','cancel_trade','cancel_depth'})
    def test_old_socket_callbacks_do_not_pollute_reconnection(self):
        old=self.client;self.bridge.connect(client_id=72)
        self.bridge.poll();old.nextValidId(900);old.managedAccounts('DU_OLD')
        self.assertEqual(self.bridge.poll(),[]);self.assertFalse(self.bridge.status()['ready'])
    def test_overflow_invalidates_feed_and_disconnects_instead_of_silent_loss(self):
        b=IBKRBridge(capacity=4,sdk_loader=lambda:(Client,Wrapper,Obj))
        b.connect();client=b._client;client.nextValidId(1);b.poll()
        rid=b.subscribe(SPEC,trades=False,depth_rows=0)['quote']
        for _ in range(8):client.tickPrice(rid,1,6000,Obj())
        events=b.poll()
        self.assertEqual(events[0]['state'],'overflow');self.assertTrue(events[0]['gap'])
        self.assertTrue(client.stop.is_set());self.assertFalse(b.status()['ready']);b.disconnect()
    def test_numbers_do_not_round_or_accept_unset_values(self):
        self.assertEqual(number(Decimal('6000.250000')),'6000.250000')
        for value in (float('nan'),float('inf'),'1.7976931348623157e308',None):
            with self.assertRaises(IBKRError):number(value)
        with self.assertRaises(IBKRError):contract_spec({**SPEC,'lastTradeDateOrContractMonth':'September'})
    def test_connect_timeout_keeps_feed_unready(self):
        b=IBKRBridge(sdk_loader=lambda:(Client,Wrapper,Obj),handshake_timeout=.03)
        b.connect();time.sleep(.08)
        self.assertFalse(b.status()['ready']);self.assertEqual(b.status()['state'],'timeout');b.disconnect()


try:
    from ibapi.client import EClient
    from ibapi.decoder import Decoder
    from ibapi.protobuf.NextValidId_pb2 import NextValidId
    from ibapi.protobuf.TickPrice_pb2 import TickPrice
    from ibapi.protobuf.MarketDepth_pb2 import MarketDepth
    from ibapi.protobuf.ErrorMessage_pb2 import ErrorMessage
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


@unittest.skipUnless(SDK_AVAILABLE, 'Optional official SDK is not installed in this runtime')
class OfficialSDKTest(unittest.TestCase):
    def test_official_protobuf_decoder_reaches_bridge_without_network(self):
        stop=threading.Event()
        with patch.object(EClient,'connect'), patch.object(EClient,'run',side_effect=lambda:stop.wait(3)), \
             patch.object(EClient,'disconnect',side_effect=stop.set), \
             patch.object(EClient,'reqMarketDataType'), patch.object(EClient,'reqMktData'), \
             patch.object(EClient,'reqTickByTickData'), patch.object(EClient,'reqMktDepth'):
            b=IBKRBridge()
            try:
                b.connect();decoder=Decoder(b._client,200)
                decoder.processNextValidIdMsgProtoBuf(NextValidId(orderId=42).SerializeToString())
                self.assertTrue(b.status()['ready']);b.poll()
                ids=b.subscribe(SPEC)
                decoder.processTickPriceMsgProtoBuf(TickPrice(reqId=ids['quote'],tickType=1,price=6000.25,size='7.125',attrMask=1).SerializeToString())
                depth=MarketDepth(reqId=ids['depth']);depth.marketDepthData.position=0
                depth.marketDepthData.operation=0;depth.marketDepthData.side=1
                depth.marketDepthData.price=6000.25;depth.marketDepthData.size='4.0001'
                decoder.processMarketDepthMsgProtoBuf(depth.SerializeToString())
                error=ErrorMessage(id=ids['quote'],errorTime=1700000000,errorCode=354,errorMsg='DU_PRIVATE')
                decoder.processErrorMsgProtoBuf(error.SerializeToString())
                events=b.poll()
                self.assertEqual([e['type'] for e in events],['quote','quote_size','depth','error'])
                self.assertEqual(events[1]['value'],'7.125')
                self.assertEqual(events[2]['bids'][0]['size'],'4.0001')
                self.assertEqual(events[3]['state'],'not entitled');self.assertNotIn('DU_PRIVATE',str(events))
            finally:b.disconnect()


if __name__=='__main__':unittest.main()
