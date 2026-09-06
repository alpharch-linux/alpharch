"""SPECIMEN credential responses only; never contacts private accounts."""
import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from alpharch_connections import Connections, ConnectionError, catalog, verify, kraken_signature, post, next_nonce

class ConnectionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager=Connections();self.messages=[]
        async def emit(value): self.messages.append(json.loads(json.dumps(value)))
        self.emit=emit
    async def asyncTearDown(self):await self.manager.close()
    async def connect(self, **extra):
        await self.manager.command({'action':'connect','provider':'kraken','credentials':{'key':'SPECIMEN_KEY','secret':'SPECIMEN_SECRET'},**extra},self.emit)
        await asyncio.sleep(.01)
    async def test_unsupported_adapter_does_not_accept_credentials(self):
        with patch('alpharch_connections.verify',new_callable=AsyncMock) as check:
            await self.connect(provider='cqg');check.assert_not_called()
        self.assertFalse(self.manager.secrets);self.assertEqual(self.messages[-1]['states']['cqg']['state'],'setup required')
    async def test_connected_data_never_contains_secrets(self):
        with patch('alpharch_connections.verify',new_callable=AsyncMock,return_value={'account':'SPECIMEN','permission':'read','refresh':True}):
            await self.connect()
            self.assertEqual(self.messages[-1]['states']['kraken']['state'],'connected')
            self.assertNotIn('SPECIMEN_SECRET',json.dumps(self.messages));self.assertNotIn('SPECIMEN_KEY',json.dumps(self.messages))
            await self.manager.command({'action':'disconnect','provider':'kraken'},self.emit)
            self.assertFalse(self.manager.secrets)
    async def test_provider_exception_is_redacted(self):
        with patch('alpharch_connections.verify',new_callable=AsyncMock,side_effect=RuntimeError('SPECIMEN_SECRET')):
            await self.connect()
        self.assertEqual(self.messages[-1]['states']['kraken']['state'],'stale');self.assertNotIn('SPECIMEN_SECRET',json.dumps(self.messages))
    async def test_denied_permissions_forget_credentials(self):
        with patch('alpharch_connections.verify',new_callable=AsyncMock,side_effect=ConnectionError('not entitled','Read permission required')):
            await self.connect()
        self.assertEqual(self.messages[-1]['states']['kraken']['state'],'not entitled');self.assertFalse(self.manager.secrets)
    async def test_reconnect_cancellation_does_not_erase_new_credentials(self):
        with patch('alpharch_connections.verify',new_callable=AsyncMock,return_value={'refresh':True}):
            await self.connect();await self.connect()
        self.assertIn('kraken',self.manager.secrets)
    async def test_unknown_environment_rejected_before_network(self):
        with self.assertRaises(ValueError):await self.connect(environment='http://malicious.example')
    async def test_browser_connection_owns_its_credentials(self):
        other=Connections()
        with patch('alpharch_connections.verify',new_callable=AsyncMock,return_value={'refresh':True}):
            await self.connect()
        self.assertFalse(other.secrets);await self.manager.close();self.assertFalse(self.manager.secrets)
    async def test_real_kraken_request_shape_without_network(self):
        with patch('alpharch_connections.post',return_value={'error':[],'result':{'XXBT':'0.01'}}) as request:
            result=await verify('kraken',{'key':'SPECIMEN_KEY','secret':'c3BlY2ltZW4='},'live')
        url,body,headers=request.call_args.args
        self.assertEqual(url,'https://api.kraken.com/0/private/Balance');self.assertNotIn(b'SPECIMEN_KEY',body);self.assertEqual(headers['API-Key'],'SPECIMEN_KEY');self.assertIn('API-Sign',headers);self.assertEqual(result['assetCount'],1)
    async def test_deribit_readonly_auth_uses_body_and_does_not_return_tokens(self):
        sent=[]
        class Socket:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def send(self,raw):sent.append(json.loads(raw))
            async def recv(self):return json.dumps({'id':len(sent),'result':{'access_token':'SPECIMEN_TOKEN'} if len(sent)==1 else {'summaries':[]}})
        with patch('websockets.connect',return_value=Socket()) as connect:
            result=await verify('deribit',{'key':'SPECIMEN_CLIENT','secret':'SPECIMEN_SECRET'},'test')
        self.assertEqual(connect.call_args.args[0],'wss://test.deribit.com/ws/api/v2');self.assertEqual(sent[0]['params']['scope'],'account:read');self.assertEqual(sent[1]['method'],'private/get_account_summaries');self.assertNotIn('SPECIMEN_TOKEN',json.dumps(result))
    async def test_binance_signed_account_request_has_no_secret_in_url_or_payload(self):
        sent=[]
        class Socket:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def send(self,raw):sent.append(json.loads(raw))
            async def recv(self):return json.dumps({'id':1,'status':200,'result':{'balances':[],'accountType':'SPOT'}})
        with patch('websockets.connect',return_value=Socket()) as connect:
            await verify('binance',{'key':'SPECIMEN_KEY','secret':'SPECIMEN_SECRET'},'live')
        self.assertNotIn('SPECIMEN_KEY',connect.call_args.args[0]);self.assertNotIn('SPECIMEN_SECRET',json.dumps(sent));self.assertEqual(sent[0]['method'],'account.status');self.assertEqual(len(sent[0]['params']['signature']),64)
    def test_signature_changes_with_nonce(self):
        first=kraken_signature('/0/private/Balance',{'nonce':'1'},'c3BlY2ltZW4=')
        second=kraken_signature('/0/private/Balance',{'nonce':'2'},'c3BlY2ltZW4=')
        self.assertNotEqual(first,second)
    def test_private_redirect_does_not_forward_api_headers(self):
        import http.server
        import threading
        seen=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(self.path);self.send_response(302);self.send_header('Location','/credential-sink');self.end_headers()
            def do_GET(self):
                seen.append(self.path);self.send_response(200);self.end_headers()
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with self.assertRaises(ConnectionError):post('http://127.0.0.1:'+str(server.server_port)+'/private',b'nonce=1',{'API-Key':'SPECIMEN_KEY'})
            self.assertEqual(seen,['/private'])
        finally:server.shutdown();server.server_close();thread.join()
    def test_nonce_monotonic_when_clock_stalls_or_moves_backward(self):
        with patch('alpharch_connections.time.time_ns',return_value=1000000):
            first=int(next_nonce('SPECIMEN_NONCE'));second=int(next_nonce('SPECIMEN_NONCE'))
        with patch('alpharch_connections.time.time_ns',return_value=0):third=int(next_nonce('SPECIMEN_NONCE'))
        self.assertGreater(second,first);self.assertGreater(third,second)
    def test_catalog_has_true_capability_boundaries(self):
        providers={p['id']:p for p in catalog()}
        self.assertEqual(providers['cqg']['method'],'setup');self.assertIsNone(providers['cqg']['chartFeed']);self.assertEqual(providers['coinbase']['method'],'public');self.assertIn('Linux',providers['interactive-brokers']['detail'])

if __name__=='__main__':unittest.main()
