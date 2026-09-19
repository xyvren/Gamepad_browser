"""Runner that launches server in subprocess and executes all acceptance tests."""
import subprocess
import time
import sys

def main():
    print("Starting background server for acceptance tests...")
    proc = subprocess.Popen([
        sys.executable, "server.py", "--diagnostic", "--port", "8765", "--https-port", "8766"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait for server to bind
    time.sleep(2)
    
    try:
        print("\n--- Running tests/verify_menu.py ---")
        subprocess.check_call([sys.executable, "tests/verify_menu.py"])
        
        print("\n--- Running tests/verify_scaling.py ---")
        subprocess.check_call([sys.executable, "tests/verify_scaling.py"])
        
        print("\n--- Running tests/verify_gyro_haptics.py ---")
        subprocess.check_call([sys.executable, "tests/verify_gyro_haptics.py"])
        
        print("\nALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == '__main__':
    main()
