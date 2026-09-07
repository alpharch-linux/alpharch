#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location('reporting', Path(__file__).resolve().parents[1] / 'lib/alpharch_install_reporting.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sent = []
        self.r = m.Reporter(self.temp.name, lambda x: self.sent.append(x.copy()) or True)
    def finish(self, build='a'*40, existing=False, choice='ask', prompt=None):
        return self.r.finish('1.8.0-alpha.1', build, existing, choice, prompt)
    def test_default_and_decline_do_not_send_or_make_id(self):
        self.finish()
        self.assertEqual(self.sent, [])
        self.assertNotIn('pending', self.r.state)
        self.assertFalse(self.r.enabled)
    def test_explicit_optin_and_three_event_types(self):
        self.finish(choice='on')
        self.finish(existing=True)
        self.finish(build='b'*40, existing=True)
        self.assertEqual([r['kind'] for r in self.sent], ['install','reinstall','update'])
        self.assertEqual(set(self.sent[0]), {'schema','event_id','kind','version','build'})
    def test_choice_persists_and_is_not_reprompted(self):
        self.finish(prompt=lambda: True)
        def bad(): raise AssertionError('asked again')
        other = m.Reporter(self.temp.name, lambda x: True)
        other.finish('1.8.0-alpha.1','a'*40,True,prompt=bad)
        self.assertTrue(other.enabled)
    def test_off_purges_failed_reports_and_never_retries(self):
        self.r.send = lambda x: False
        self.finish(choice='on')
        self.assertEqual(len(self.r.state['pending']),1)
        self.r.set_enabled(False)
        self.r.send = lambda x: self.fail('network while off')
        self.finish(existing=True)
        self.assertNotIn('pending',self.r.state)
    def test_retry_preserves_event_id(self):
        self.r.send = lambda x: False
        self.finish(choice='on')
        saved = self.r.state['pending'][0].copy()
        r = m.Reporter(self.temp.name, lambda x: self.sent.append(x.copy()) or True)
        r.finish('1.8.0-alpha.1','b'*40,True)
        self.assertEqual(self.sent[0],saved)
        self.assertEqual(len(self.sent),2)
        self.assertEqual(r.state['pending'],[])
    def test_enable_does_not_send_old_receipts(self):
        self.finish()
        self.r.set_enabled(True)
        self.assertEqual(self.sent,[])
        self.finish(existing=True)
        self.assertEqual([x['kind'] for x in self.sent],['reinstall'])
    def test_old_install_is_update_not_fresh(self):
        self.finish(existing=True,choice='on')
        self.assertEqual(self.sent[0]['kind'],'update')
    def test_queue_bounded(self):
        self.r.send=lambda x: False
        for i in range(20): self.finish(choice='on',existing=True)
        self.assertEqual(len(self.r.state['pending']),10)
    def test_corrupt_consent_defaults_off(self):
        self.r.config_path.parent.mkdir(parents=True)
        self.r.config_path.write_text('not json')
        self.r=m.Reporter(self.temp.name,lambda x: self.fail('no consent'))
        self.finish()
        self.assertFalse(self.r.enabled)
    def test_state_has_private_permissions(self):
        self.finish(choice='on')
        self.assertEqual(self.r.state_path.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.r.config_path.stat().st_mode & 0o777,0o600)
    def test_edited_queue_cannot_leak_extra_fields(self):
        self.r.send=lambda x: False
        self.finish(choice='on')
        self.r.state['pending'][0]['account']='private'
        self.r.send=lambda x: self.sent.append(x.copy()) or True
        self.finish(existing=True)
        self.assertEqual(len(self.sent),1)
        self.assertNotIn('account',self.sent[0])
    def test_network_failure_is_bounded_and_not_a_success(self):
        report={'schema':1,'event_id':'c4670267-352a-4509-a7b3-40ef6691acb2','kind':'install','version':'1.8.0-alpha.1','build':'a'*40}
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],7,'','offline')) as run:
            self.assertFalse(m.transmit(report))
            args=run.call_args.args[0]
            self.assertIn('--max-time',args)
            self.assertIn('=https',args)
            self.assertNotIn('--location',args)
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired('curl',3)):
            self.assertFalse(m.transmit(report))
    def test_malformed_version_cannot_send(self):
        with self.assertRaises(ValueError):self.r.finish('secret@example.com','a'*40,False,'on')
        self.assertEqual(self.sent,[])

if __name__=='__main__':unittest.main()
