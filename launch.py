"""Open the existing server, or start it in a visible console."""
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

URL='http://127.0.0.1:8765/host'
def is_running():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/status',timeout=1) as r:
            return json.load(r).get('mode') in ('xinput','diagnostic')
    except (OSError,ValueError): return False

def main():
    if not is_running():
        subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))],cwd=Path(__file__).parent,creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform=='win32' else 0)
        for _ in range(40):
            if is_running(): break
            time.sleep(.25)
        else: raise SystemExit('Server gagal mulai. Periksa pesan di jendela server.')
    webbrowser.open(URL)

if __name__=='__main__': main()
