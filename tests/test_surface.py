import unittest
from pathlib import Path

class SurfaceTests(unittest.TestCase):
    def test_controller_and_desktop_surfaces(self):
        root=Path(__file__).resolve().parents[1]/'static'
        self.assertTrue((root/'index.html').exists(), 'Controller surface missing')
        text=(root/'index.html').read_text(encoding='utf-8')
        for name in ('cross','circle','square','triangle','l1','r1','l3','r3','options','share'):
            self.assertIn(f'data-button="{name}"', text)
        self.assertIn('app.js',text)
        self.assertTrue((root/'host.html').exists())
