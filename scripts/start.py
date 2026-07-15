import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"
BACKEND_SRC_DIR = PROJECT_ROOT / "src" / "backend"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "3000")

processes: list[subprocess.Popen] = []


def project_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [str(BACKEND_SRC_DIR)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def run_step(command: list[str], cwd: Path = PROJECT_ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(command)}")
    return subprocess.run(command, cwd=cwd, check=check)


def python_command() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def ensure_paths() -> None:
    if not (PROJECT_ROOT / "pyproject.toml").exists():
        raise SystemExit(f"Could not find pyproject.toml under {PROJECT_ROOT}")
    if not BACKEND_SRC_DIR.exists():
        raise SystemExit(f"Could not find backend source directory: {BACKEND_SRC_DIR}")
    if not FRONTEND_DIR.exists():
        raise SystemExit(f"Could not find frontend directory: {FRONTEND_DIR}")


def ensure_port_available(host: str, port: str, service_name: str) -> None:
    try:
        port_number = int(port)
    except ValueError as exc:
        raise SystemExit(f"{service_name} port must be a number, got: {port}") from exc

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        if sock.connect_ex((host, port_number)) == 0:
            raise SystemExit(
                f"{service_name} port {host}:{port} is already in use. "
                "Stop the existing process or set BACKEND_PORT/FRONTEND_PORT before running the script."
            )


def ensure_ports_available() -> None:
    ensure_port_available(BACKEND_HOST, BACKEND_PORT, "Backend")
    ensure_port_available("127.0.0.1", FRONTEND_PORT, "Frontend")


def ensure_frontend_dependencies() -> None:
    if (FRONTEND_DIR / "node_modules").exists():
        return
    print("Frontend dependencies are missing. Installing with npm install...")
    run_step(["npm", "install"], cwd=FRONTEND_DIR)


def start_postgres() -> None:
    print("Starting Postgres with Docker Compose...")
    try:
        run_step(["docker", "compose", "up", "-d", "postgres"])
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "Could not start Docker Postgres. Make sure Docker Desktop is running, "
            "then retry: python scripts/start.py"
        ) from exc


def wait_for_memory_schema() -> None:
    print("Checking Postgres and creating memory schema if needed...")
    code = (
        "from dotenv import load_dotenv; "
        "load_dotenv(); "
        "from supportagent.rag.vector_store import get_connection; "
        "from supportagent.memory import create_memory_schema; "
        "conn=get_connection(); "
        "create_memory_schema(conn); "
        "conn.close(); "
        "print('memory schema ok')"
    )
    for attempt in range(1, 16):
        result = subprocess.run(
            [python_command(), "-c", code],
            cwd=PROJECT_ROOT,
            env=project_env(),
            check=False,
        )
        if result.returncode == 0:
            return
        print(f"Postgres is not ready yet ({attempt}/15). Waiting...")
        time.sleep(2)
    raise SystemExit("Postgres did not become ready. Check docker compose logs postgres.")


def start_backend() -> subprocess.Popen:
    print(f"Starting FastAPI backend on http://{BACKEND_HOST}:{BACKEND_PORT}")
    process = subprocess.Popen(
        [
            python_command(),
            "-m",
            "uvicorn",
            "supportagent.api:app",
            "--reload",
            "--host",
            BACKEND_HOST,
            "--port",
            BACKEND_PORT,
        ],
        cwd=PROJECT_ROOT,
        env=project_env(),
        start_new_session=True,
    )
    processes.append(process)
    return process


def start_frontend() -> subprocess.Popen:
    print(f"Starting Next.js frontend on http://localhost:{FRONTEND_PORT}")
    env = project_env()
    env["BACKEND_API_URL"] = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    env["PORT"] = FRONTEND_PORT
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        env=env,
        start_new_session=True,
    )
    processes.append(process)
    return process


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass


def cleanup() -> None:
    print("\nStopping services...")
    for process in processes:
        terminate_process(process)


def monitor() -> None:
    print("\nSupportAgent is starting.")
    print(f"Frontend: http://localhost:{FRONTEND_PORT}")
    print(f"Backend:  http://{BACKEND_HOST}:{BACKEND_PORT}")
    print("Press Ctrl+C to stop backend and frontend. Postgres stays running.\n")
    try:
        while True:
            time.sleep(1)
            for process in processes:
                if process.poll() is not None:
                    raise SystemExit(f"A service exited with code {process.returncode}.")
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


def main() -> None:
    os.chdir(PROJECT_ROOT)
    ensure_paths()
    ensure_ports_available()
    ensure_frontend_dependencies()
    start_postgres()
    wait_for_memory_schema()
    start_backend()
    start_frontend()
    monitor()


if __name__ == "__main__":
    main()
