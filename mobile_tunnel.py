import re
import subprocess
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent
CF_BIN = ROOT_DIR / "cloudflared.exe"


def is_port_open(url: str) -> bool:
    try:
        return requests.get(url, timeout=1).status_code == 200
    except Exception:
        return False


def launch_mobile_https():
    print("================================================================")
    print("  FREEDOM MOBILE FIELD MODE — LIVE HTTPS SMARTPHONE TUNNEL")
    print("================================================================")

    backend_proc = None
    if is_port_open("http://127.0.0"):
        print("[1/3] FastAPI Backend ALREADY ONLINE on port 8080")
    else:
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.fastapi_app:app", "--host", "127.0.0.1", "--port", "8080"],
            cwd=str(ROOT_DIR),
        )
        for _ in range(25):
            if is_port_open("http://127.0.0"):
                print("[1/3] FastAPI Backend ONLINE on port 8080")
                break
            time.sleep(0.5)

    frontend_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app_3.py",
            "--server.port", "8501", "--server.address", "0.0.0.0",
        ],
        cwd=str(ROOT_DIR),
    )
    time.sleep(2.5)
    print("[2/3] Streamlit Frontend ONLINE on port 8501")

    if not CF_BIN.exists():
        print(f"[3/3] '{CF_BIN}' not found. Run the Invoke-WebRequest command first.")
        return

    cf_proc = subprocess.Popen(
        [str(CF_BIN), "tunnel", "--url", "http://127.0.0.1:8501"],
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    public_url = ""
    for _ in range(40):
        line = cf_proc.stdout.readline() if cf_proc.stdout else ""
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            public_url = match.group(0)
            break

    if public_url:
        print("================================================================")
        print("[3/3] OPEN THIS HTTPS URL ON YOUR SMARTPHONE CAMERA:")
        print(f"      >>>  {public_url}  <<<")
        print("================================================================")
    else:
        print("[3/3] Cloudflare Tunnel started—check output for https://...trycloudflare.com")

    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down FreeDom Mobile Field Mode...")
        cf_proc.terminate()
        frontend_proc.terminate()
        if backend_proc:
            backend_proc.terminate()


if __name__ == "__main__":
    launch_mobile_https()
