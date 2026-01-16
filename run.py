import os
import sys
import uvicorn
import webbrowser
import threading
import multiprocessing
import socket
import requests
import time
from fastapi.staticfiles import StaticFiles
from app.main import app


# --- SPLASH SCREEN IMPORT ---
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

# --- PORT LOGIC ---
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_free_port(start_port=8000, max_port=8010):
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    return None

def check_existing_instance(port=8000):
    """Checks if the app is already running on the default port."""
    try:
        if is_port_in_use(port):
            # Something is there, check if it is US
            response = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=1)
            if response.status_code == 200 and response.json().get("app") == "Dataforg":
                return True
    except:
        pass
    return False

# --- WINDOWED MODE FIX ---
class NullWriter:
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_browser(url):
    time.sleep(1.5) # Wait for server to boot
    webbrowser.open(url)
    # Close splash screen once browser launches
    if pyi_splash and pyi_splash.is_alive():
        pyi_splash.close()

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # 1. Check if already running
    if check_existing_instance(8000):
        # Close splash immediately
        if pyi_splash and pyi_splash.is_alive():
            pyi_splash.close()
        # Open browser to existing instance
        webbrowser.open("http://127.0.0.1:8000")
        sys.exit(0) # Stop this new instance

    # 2. Find a free port (8000, 8001, 8002...)
    port = find_free_port()
    if port is None:
        # Should almost never happen
        if pyi_splash: pyi_splash.close()
        sys.exit(1)

    # 3. Setup Static Files
    static_path = get_resource_path(os.path.join("app", "static"))
    if not os.path.exists(static_path):
        static_path = os.path.join(os.getcwd(), "app", "static")
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

    # 4. Launch Browser & Close Splash
    threading.Thread(target=start_browser, args=(f"http://127.0.0.1:{port}",), daemon=True).start()

    # 5. Run Server
    uvicorn.run(app, host="127.0.0.1", port=port, log_config=None)