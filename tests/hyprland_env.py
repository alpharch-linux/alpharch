import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lib'))
from alpharch_hyprland_env import desktop_env


class HyprlandEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = self.tmp.name
        folder = Path(self.runtime)/'hypr'/'current-session'
        folder.mkdir(parents=True)
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(folder/'.socket.sock'))
        self.addCleanup(self.socket.close)
        self.desktop = {'XDG_RUNTIME_DIR':self.runtime,
                        'HYPRLAND_INSTANCE_SIGNATURE':'current-session',
                        'WAYLAND_DISPLAY':'wayland-1', 'PATH':'/usr/share/omarchy/bin:/usr/bin'}

    def manager(self):
        text='\n'.join(k+'='+v for k,v in self.desktop.items())
        return subprocess.CompletedProcess([],0,text+'\nUNRELATED_SECRET=not-for-import\n','')

    def test_valid_caller_session_needs_no_discovery(self):
        with patch.dict(os.environ,self.desktop,clear=True),patch('alpharch_hyprland_env.subprocess.run') as run:
            self.assertEqual(desktop_env(),self.desktop)
            run.assert_not_called()

    def test_service_started_before_desktop_recovers_session_and_launcher_path(self):
        base={'XDG_RUNTIME_DIR':self.runtime,'ALPHARCH_HOME':'/private/config','HTTPS_PROXY':'existing-proxy'}
        with patch.dict(os.environ,base,clear=True),patch('alpharch_hyprland_env.subprocess.run',return_value=self.manager()):
            result=desktop_env()
            self.assertEqual(result,{**base,**self.desktop})
            self.assertNotIn('UNRELATED_SECRET',result)
            self.assertEqual(dict(os.environ),base,'Do not mutate other service threads')

    def test_previous_login_signature_is_replaced(self):
        with patch.dict(os.environ,{**self.desktop,'HYPRLAND_INSTANCE_SIGNATURE':'old-session'},clear=True),patch('alpharch_hyprland_env.subprocess.run',return_value=self.manager()):
            self.assertEqual(desktop_env()['HYPRLAND_INSTANCE_SIGNATURE'],'current-session')

    def test_single_running_instance_without_manager_import(self):
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,json.dumps([
            {'instance':'current-session','wl_socket':'wayland-1'}]),'')]
        with patch.dict(os.environ,{'XDG_RUNTIME_DIR':self.runtime},clear=True),patch('alpharch_hyprland_env.subprocess.run',side_effect=replies):
            result=desktop_env()
            self.assertEqual(result['HYPRLAND_INSTANCE_SIGNATURE'],'current-session')
            self.assertEqual(result['WAYLAND_DISPLAY'],'wayland-1')

    def test_multiple_desktops_are_not_guessed(self):
        base={'XDG_RUNTIME_DIR':self.runtime}
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,json.dumps([
            {'instance':'current-session','wl_socket':'wayland-1'},
            {'instance':'another-session','wl_socket':'wayland-2'}]),'')]
        with patch.dict(os.environ,base,clear=True),patch('alpharch_hyprland_env.subprocess.run',side_effect=replies):
            self.assertEqual(desktop_env(),base)

    def test_unavailable_desktop_does_not_break_classic(self):
        base={'XDG_RUNTIME_DIR':self.runtime}
        with patch.dict(os.environ,base,clear=True),patch('alpharch_hyprland_env.subprocess.run',side_effect=FileNotFoundError):
            self.assertEqual(desktop_env(),base)

    def test_desktop_can_become_ready_after_first_check(self):
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'[]',''),self.manager()]
        with patch.dict(os.environ,{'XDG_RUNTIME_DIR':self.runtime},clear=True),patch('alpharch_hyprland_env.subprocess.run',side_effect=replies):
            self.assertNotIn('HYPRLAND_INSTANCE_SIGNATURE',desktop_env())
            self.assertEqual(desktop_env()['WAYLAND_DISPLAY'],'wayland-1')


if __name__=='__main__':
    unittest.main()
