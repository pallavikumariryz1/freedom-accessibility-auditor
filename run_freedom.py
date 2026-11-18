import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def find_streamlit_entry() -> Path:
    frontend_dir = ROOT_DIR / "frontend"
    for candidate in ["streamlit_app_3.py", "streamlit_app.py"]:
        path = frontend_dir / candidate
        if path.exists():
            return path
    py_files = sorted(frontend_dir.glob("*.py"))
    if py_files:
        return py_files[0]
    raise FileNotFoundError(f"No Streamlit entry script found in {frontend_dir}")


def wait_for_backend(url: str, timeout_sec: int = 15) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    os.chdir(ROOT_DIR)
    (ROOT_DIR / "data" / "uploads").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "models").mkdir(parents=True, exist_ok=True)

    streamlit_entry = find_streamlit_entry()
    python_exe = sys.executable

    print("=" * 64)
    print("  FREEDOM ACCESSIBILITY AUDITOR — ONE-CLICK LAUNCHER")
    print("=" * 64)
    print(f"[1/2] Starting FastAPI Spatial Backend on http://127.0.0.1:8080 ...")

    backend_proc = subprocess.Popen(
        [
            python_exe,
            "-m",
            "uvicorn",
            "backend.fastapi_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
        ],
        cwd=str(ROOT_DIR),
    )

    if wait_for_backend("http://127.0.0.1:8080/health", timeout_sec=15):
        print("      -> FastAPI Backend ONLINE (http://127.0.0.1:8080/docs)")
    else:
        print("      -> Warning: Backend health check timed out; continuing launch...")

    print(f"[2/2] Starting Streamlit Frontend ({streamlit_entry.name}) on http://localhost:8501 ...")
    frontend_proc = subprocess.Popen(
        [
            python_exe,
            "-m",
            "streamlit",
            "run",
            str(streamlit_entry),
            "--server.port",
            "8501",
        ],
        cwd=str(ROOT_DIR),
    )

    print("\nPress Ctrl+C in this window to stop both servers cleanly.\n")
    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down FreeDom servers...")
    finally:
        for proc in (frontend_proc, backend_proc):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("All servers stopped.")


if __name__ == "__main__":
    main()
