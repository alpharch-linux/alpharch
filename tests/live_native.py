#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from workstation import module, ROOT
live=module('live_native', ROOT/'bin/trade-live')

class NativeLiveTests(unittest.TestCase):
    def test_window_url_validation(self):
        self.assertIn('asset=BTC',live.window_url('btc',17863,'BTC'))
        for name in ('../bad','x;echo','x\nhello'):
            with self.assertRaises(ValueError):live.window_url(name,17863,'BTC')
        with self.assertRaises(ValueError):live.window_url('btc',17863,'NQ')
    def test_dry_run_has_no_launch_or_service(self):
        with patch.object(live,'browser_command',return_value=['browser','--app=url']),patch.object(live,'ensure_server') as service,patch.object(live.subprocess,'Popen') as launch,patch('builtins.print'):
            live.open_window('btc',17863,'BTC',dry_run=True)
            launch.assert_not_called();service.assert_not_called()
    def test_preserves_open_windows_and_falls_back_missing_monitor(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'layouts').mkdir();data={'schema':'alpharch.live-native/1','windows':[{'window':dict(name='btc',port=17863,asset='BTC',feed='coinbase',view='candles',tf=60),'workspace':'31','monitor':'gone'}]};(root/'layouts/desk.json').write_text(json.dumps(data))
            def query(kind):return [{'name':'real'}] if kind=='monitors' else []
            with patch.object(live,'CONFIG',root),patch.object(live,'monitors',side_effect=query),patch('builtins.print') as output,patch.object(live.subprocess,'run') as run:
                live.load_layout('desk',True);self.assertIn('real',output.call_args[0][0]);run.assert_not_called()
            def active(kind):return [{'name':'real'}] if kind=='monitors' else [{'title':'Alpharch Live [btc]'}]
            with patch.object(live,'CONFIG',root),patch.object(live,'monitors',side_effect=active),patch('builtins.print') as output,patch.object(live.subprocess,'run') as run:
                live.load_layout('desk');self.assertIn('Already open',output.call_args[0][0]);run.assert_not_called()
    def test_layout_rejects_duplicate_and_shell_workspace(self):
        item={'window':dict(name='btc',port=17863,asset='BTC',feed='coinbase',view='candles',tf=60),'workspace':'31','monitor':None}
        with self.assertRaises(ValueError):live.validate_layout({'schema':'alpharch.live-native/1','windows':[item,item]})
        with self.assertRaises(ValueError):live.validate_layout({'schema':'alpharch.live-native/1','windows':[{**item,'workspace':'31;bad'}]})

if __name__=='__main__':unittest.main()
