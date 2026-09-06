#!/usr/bin/env python3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
import alpharch_desktop as desktop

class DesktopTools(unittest.TestCase):
    def test_brain_only_opens_help_without_model(self):
        with patch.object(desktop.shutil,'which',return_value='/bin/terminal'):
            args=desktop.command('brain',{})
            self.assertEqual(args[-1],'help');self.assertNotIn('claude',args)
    def test_unknown_action_cannot_be_a_shell_command(self):
        with self.assertRaises(ValueError):desktop.command('rm -rf /',{})
    def test_replay_is_known_regular_file_and_paused(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(desktop,'TAPES',Path(folder)),patch.object(desktop,'free_port',return_value=17870):
            (Path(folder)/'actual.jsonl').write_text('{}\n');(Path(folder)/'link.jsonl').symlink_to(Path(folder)/'actual.jsonl')
            for name in ('../actual.jsonl','link.jsonl','missing.jsonl'):
                with self.assertRaises(ValueError):desktop.command('replay',{'file':name})
            args=desktop.command('replay',{'file':'actual.jsonl'});self.assertIn('--start-paused',args);self.assertNotIn('--exchange',args)
    def test_record_is_supported_source_and_visible_terminal(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(desktop,'TAPES',Path(folder)),patch.object(desktop.shutil,'which',return_value='/bin/terminal'),patch.object(desktop,'free_port',return_value=17870):
            with self.assertRaises(ValueError):desktop.command('record',{'asset':'NQ','feed':'coinbase'})
            args=desktop.command('record',{'asset':'BTC','feed':'hyperliquid','tick':1});self.assertEqual(args[0],'/bin/terminal');self.assertIn('hyperliquid',args);self.assertIn('perp',args)
    def test_catalog_does_not_launch_anything(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(desktop,'TAPES',Path(folder)),patch.object(desktop.subprocess,'Popen') as launch:
            result=desktop.launch({'action':'catalog'});self.assertIn('journal',result['available']);launch.assert_not_called()

if __name__=='__main__':unittest.main()
