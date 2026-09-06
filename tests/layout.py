#!/usr/bin/env python3
import unittest
from unittest.mock import patch
from workstation import module, ROOT
layout=module('layout',ROOT/'bin/trade-layout')

class LayoutTests(unittest.TestCase):
    def test_rejects_shell_desktop_and_duplicate_ports(self):
        item=dict(exchange='coinbase',symbol='BTC-USD',port=17860,tick=10,bucket=60,desktop='1')
        with self.assertRaises(ValueError):layout.validate({'schema':'alpharch.desk/1','engines':[item,item]})
        with self.assertRaises(ValueError):layout.validate({'schema':'alpharch.desk/1','engines':[{**item,'desktop':'1;danger'}]})
    def test_monitor_fallback_and_safe_dry_run(self):
        data={'schema':'alpharch.desk/1','engines':[dict(exchange='coinbase',symbol='BTC-USD',port=17860,tick=10,bucket=60,desktop='1',monitor='MISSING')]}
        with patch.object(layout,'hypr',return_value=[{'name':'AVAILABLE'}]),patch('builtins.print') as out,patch.object(layout.subprocess,'Popen') as launch:
            layout.restore(data,dry_run=True)
            self.assertIn('AVAILABLE',out.call_args[0][0]);launch.assert_not_called()

if __name__=='__main__':unittest.main()
