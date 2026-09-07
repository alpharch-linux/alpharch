import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lib'))
import alpharch_native as native


class NativeDeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name)/'hyprland'
        self.patches = [patch.object(native, 'STORE', self.store), patch.object(native.live, 'ensure_server'),
                        patch.object(native, 'visit'), patch.object(native, 'open_window'),
                        patch.object(native.live, 'monitors', side_effect=lambda kind: [{'id':1,'name':'DP-1'}] if kind=='monitors' else [])]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)
        self.chart = {'id':1, 'asset':'BTC', 'feed':'coinbase', 'view':'candles', 'tf':60,
                      'aggregation':{'kind':'range','size':40}, 'historyBars':700, 'historyDays':14,
                      'intervalFavorites':['1m','5m','4h','40R'], 'studies':[{'id':'rsi','period':14}],
                      'drawings':[{'type':'hline','points':[{'t':1,'p':100}]}],
                      'x':.3, 'y':.2, 'w':.5, 'h':.6}
        self.doc = {'name':'SPECIMEN chart settings', 'palette':'pit', 'charts':[self.chart]}

    def client(self, key='chart-a', workspace='alpharch', monitor=1):
        return {'title':f'Alpharch Hyprland [{key}]', 'workspace':{'name':workspace}, 'monitor':monitor}

    def test_launch_uses_separate_identity_and_preserves_all_chart_settings(self):
        original = copy.deepcopy(self.doc)
        result = native.action({'action':'open','document':self.doc},17866)
        key = result['opened'][0]
        self.assertRegex(key,r'^chart-[a-f0-9]{12}$')
        doc = native.read('windows',key)
        self.assertEqual(doc['charts'][0], {**self.chart,'x':0,'y':0,'w':1,'h':1})
        self.assertEqual(self.doc,original)
        native.open_window.assert_called_once_with(key,17866,'9')
        self.assertFalse((self.store.parent/'live').exists())

    def test_new_chart_uses_its_parent_workspace(self):
        with patch.object(native,'clients',return_value=[self.client(workspace='trading-left')]):
            native.action({'action':'open','document':self.doc,'source':'chart-a'},17866)
        self.assertEqual(native.open_window.call_args.args[2],'trading-left')

    def test_window_controls_use_the_recovered_desktop_environment(self):
        env={'HYPRLAND_INSTANCE_SIGNATURE':'current','WAYLAND_DISPLAY':'wayland-1'}
        # setUp mocks these operations for layout tests; exercise their originals here.
        for operation,args in ((native.place,({'address':'0x123'},'9')),
                               (self.patches[2].temp_original,('9',)),
                               (native.focus,({'address':'0x123'},))):
            with patch.object(native.live,'desktop_env',return_value=env),patch.object(native.subprocess,'run') as run:
                operation(*args)
                self.assertEqual(run.call_args.kwargs['env'],env)

    def test_default_desk_does_not_take_an_occupied_workspace(self):
        with patch.object(native.live,'monitors',side_effect=lambda kind: [{'id':9}] if kind=='workspaces' else []):
            self.assertEqual(native.home_workspace(),'8')

    def test_save_and_restore_missing_monitor_preserves_live_charts(self):
        native.write('windows','chart-a',self.doc)
        with patch.object(native,'clients',return_value=[self.client(monitor=99)]):
            native.save_layout('morning')
        saved = native.read('layouts','morning')
        self.assertEqual(saved['windows'][0]['document'],self.doc)
        native.load_layout('morning',17863)
        native.open_window.assert_called_once_with('chart-a',17863,'alpharch','DP-1')
        updated = {**self.doc,'name':'Unsaved live edits'}
        native.write('windows','chart-a',updated)
        native.open_window.reset_mock()
        with patch.object(native,'clients',return_value=[self.client()]):
            native.load_layout('morning',17863)
        self.assertEqual(native.read('windows','chart-a'),updated)
        native.open_window.assert_not_called()

    def test_entire_restore_validated_before_any_window_is_changed(self):
        native.write('layouts','bad',{'schema':'alpharch.hyprland/1','windows':[
            {'name':'valid','document':self.doc,'workspace':'2'},
            {'name':'../escape','document':self.doc,'workspace':'2'}]})
        with self.assertRaises(ValueError): native.load_layout('bad',17863)
        native.open_window.assert_not_called()
        self.assertFalse((self.store/'windows').exists())

    def test_write_cannot_create_id_or_escape_store(self):
        for key in ('../escape','a/b','a;echo bad','',None):
            with self.assertRaises(ValueError): native.action({'action':'write','window':key,'document':self.doc},17863)
        with self.assertRaises(ValueError): native.action({'action':'write','window':'unknown','document':self.doc},17863)
        native.write('windows','chart-a',self.doc)
        modified={**self.doc,'name':'Changed chart'}
        native.action({'action':'write','window':'chart-a','document':modified},17863)
        self.assertEqual(native.action({'action':'read','window':'chart-a'},17863)['document'],modified)
        self.assertEqual((self.store/'windows/chart-a.json').stat().st_mode & 0o777,0o600)

    def test_limits_offline_and_non_finite_documents(self):
        for value in (None,{}, {**self.doc,'charts':[self.chart]*9}, {**self.doc,'charts':[{'x':float('nan')}]}, {**self.doc,'charts':[{'label':'x'*61000}]}):
            with self.assertRaises(ValueError): native.document(value)
        with self.assertRaises(ValueError): native.document({**self.doc,'charts':[self.chart]*2},single=True)
        with patch.object(native.live,'monitors',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Classic desk'):native.action({'action':'open','document':self.doc},17863)
        with patch.object(native,'clients',return_value=[self.client(f'chart-{i}') for i in range(12)]):
            with self.assertRaises(ValueError): native.action({'action':'open','document':self.doc},17863)
        for port in (True,0,65536,'17863'):
            with self.assertRaises(ValueError): native.action({'action':'catalog'},port)
        with self.assertRaises(ValueError):native.action({'action':'exec','command':'touch /tmp/unsafe'},17863)

    def test_no_symlink_overwrite_and_blank_window_supported(self):
        native.write('windows','chart-a',self.doc)
        (self.store/'windows/link.json').symlink_to(self.store/'windows/chart-a.json')
        with self.assertRaises(ValueError):native.write('windows','link',{})
        with self.assertRaises(ValueError):native.read('windows','link')
        result=native.launch_document({**self.doc,'charts':[]},17863)
        self.assertEqual(len(result['opened']),1)
        self.assertEqual(native.read('windows',result['opened'][0])['charts'],[])


if __name__=='__main__':unittest.main()
