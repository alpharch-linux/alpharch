import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from alpharch_omarchy_theme import OmarchyTheme


class ThemeTests(unittest.TestCase):
    def test_metadata_reload_and_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            now = [0]
            reader = OmarchyTheme(folder, lambda: now[0])
            self.assertEqual(reader.snapshot(), {'available': False})
            current, legacy = reader.roots
            (current / 'theme').mkdir(parents=True)
            data = 'background="#07120a"\nforeground="#ffffff"\naccent="#44ffaa"\n'
            (current / 'theme/colors.toml').write_text(data + 'command="never execute"\n')
            (current / 'theme.name').write_text('My theme')
            self.assertFalse(reader.snapshot()['available'])
            now[0] += 2
            self.assertEqual(reader.snapshot()['name'], 'My theme')
            self.assertNotIn('command', reader.snapshot()['colors'])
            (legacy / 'theme').mkdir(parents=True)
            (legacy / 'theme/colors.toml').write_text(data.replace('#07120a', '#f8f8f8'))
            (current / 'theme/colors.toml').unlink()
            now[0] += 2
            self.assertEqual(reader.snapshot()['colors']['background'], '#f8f8f8')

    def test_rejects_invalid_or_oversized_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            now = [0]
            reader = OmarchyTheme(folder, lambda: now[0])
            root = reader.roots[0]
            (root / 'theme').mkdir(parents=True)
            path = root / 'theme/colors.toml'
            for value in ['not TOML', 'background="url(evil)"\nforeground="#ffffff"\naccent="#123456"', '#' * 16385]:
                path.write_text(value)
                now[0] += 2
                self.assertEqual(reader.snapshot(), {'available': False})


if __name__ == '__main__':
    unittest.main()
