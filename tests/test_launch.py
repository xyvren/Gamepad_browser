import unittest
from unittest.mock import patch

class LauncherTests(unittest.TestCase):
    def test_existing_server_opens_dashboard_without_second_process(self):
        from launch import main
        with patch('launch.is_running',return_value=True), patch('launch.webbrowser.open') as browser, patch('launch.subprocess.Popen') as process:
            main()
            browser.assert_called_once_with('http://127.0.0.1:8765/host')
            process.assert_not_called()
