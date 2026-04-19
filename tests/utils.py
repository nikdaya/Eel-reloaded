import contextlib
import os
import socket
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import psutil

# Path to the test data folder.
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_HOST = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS = 30.0
REPO_ROOT = Path(__file__).resolve().parents[1]


def _raise_startup_error(
    proc: subprocess.Popen[str], example_py: str, reason: str
) -> None:
    try:
        stdout, stderr = proc.communicate(timeout=1.0)
    except subprocess.TimeoutExpired:
        stdout = proc.stdout.read() if proc.stdout is not None else ""
        stderr = proc.stderr.read() if proc.stderr is not None else ""

    details = [reason, f"Example: {example_py}"]
    if stdout:
        details.append(f"stdout:\n{stdout}")
    if stderr:
        details.append(f"stderr:\n{stderr}")
    raise RuntimeError("\n\n".join(details))


def get_process_listening_port(proc):
    conn = None
    if platform.system() == "Windows":
        current_process = psutil.Process(proc.pid)
        processes = [current_process]

        # Older Eel test servers could spawn a child process on Windows. With the
        # modern ASGI runtime, the listening socket may stay in the parent process.
        while True:
            children = current_process.children(recursive=True)
            if (3, 6) <= sys.version_info < (3, 7):
                processes = [current_process]
            else:
                processes = [current_process, *children]

            for candidate in processes:
                connections = candidate.connections()
                if any(connection.status == "LISTEN" for connection in connections):
                    conn = next(
                        filter(
                            lambda connection: connection.status == "LISTEN",
                            connections,
                        )
                    )
                    break

            if conn is not None:
                break

            time.sleep(0.01)
    else:
        psutil_proc = psutil.Process(proc.pid)
        while not any(conn.status == "LISTEN" for conn in psutil_proc.connections()):
            time.sleep(0.01)

        conn = next(
            filter(lambda conn: conn.status == "LISTEN", psutil_proc.connections())
        )
    return conn.laddr.port


@contextlib.contextmanager
def get_eel_server(
    example_py,
    start_html,
    use_repo_code: bool = False,
    startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
):
    """Run an Eel example with the mode/port overridden so that no browser is launched and a random port is assigned"""
    test = None
    example_dir = os.path.abspath(os.path.dirname(example_py))

    port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_socket.bind((TEST_HOST, 0))
    eel_port = port_socket.getsockname()[1]
    port_socket.close()

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=example_dir, delete=False
        ) as test:
            # We want to run the examples unmodified to keep the test as realistic as possible, but all of the examples
            # want to launch browsers, which won't be supported in CI. The below script will configure eel to open on
            # a random port and not open a browser, before importing the Python example file - which will then
            # do the rest of the set up and start the eel server. This is definitely hacky, and means we can't
            # test mode/port settings for examples ... but this is OK for now.
            repo_path_setup = ""
            if use_repo_code:
                repo_path_setup = (
                    "import sys\n"
                    "from pathlib import Path\n\n"
                    f"sys.path.insert(0, str(Path(r'{REPO_ROOT}')))\n\n"
                )

            test.write(
                f"""
{repo_path_setup}import eel

_real_start = eel.start


def _test_start(*args, **kwargs):
    kwargs['mode'] = None
    kwargs['host'] = '{TEST_HOST}'
    kwargs['port'] = {eel_port}
    return _real_start(*args, **kwargs)


eel.start = _test_start

import {os.path.splitext(os.path.basename(example_py))[0]}
"""
            )
        proc = subprocess.Popen(
            [os.fspath(Path(os.sys.executable)), test.name],
            cwd=example_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        connected = False
        deadline = time.time() + startup_timeout_seconds
        while time.time() < deadline:
            if proc.poll() is not None:
                _raise_startup_error(
                    proc,
                    example_py,
                    f"Eel example exited early with code {proc.returncode}.",
                )

            try:
                with socket.create_connection((TEST_HOST, eel_port), timeout=0.2):
                    connected = True
                    break
            except OSError:
                time.sleep(0.1)

        if not connected:
            proc.terminate()
            _raise_startup_error(
                proc,
                example_py,
                f"Eel example never started listening on http://{TEST_HOST}:{eel_port}.",
            )

        if proc.poll() is not None:
            _raise_startup_error(
                proc,
                example_py,
                f"Eel example exited early with code {proc.returncode}.",
            )

        app_url = f"http://{TEST_HOST}:{eel_port}/{start_html}"
        http_ready = False
        deadline = time.time() + startup_timeout_seconds
        while time.time() < deadline:
            if proc.poll() is not None:
                _raise_startup_error(
                    proc,
                    example_py,
                    f"Eel example exited early with code {proc.returncode}.",
                )

            try:
                with urllib.request.urlopen(app_url, timeout=0.5) as response:
                    if 200 <= response.status < 400:
                        http_ready = True
                        break
            except Exception:
                time.sleep(0.1)

        if not http_ready:
            proc.terminate()
            _raise_startup_error(
                proc,
                example_py,
                f"Eel example never became HTTP-ready at {app_url}.",
            )

        yield app_url

        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)

    finally:
        if test and "proc" in locals() and proc.poll() is None:
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=5)
        if test:
            try:
                os.unlink(test.name)
            except FileNotFoundError:
                pass


def get_console_logs(driver, minimum_logs=0):
    console_logs = driver.get_log("browser")

    while len(console_logs) < minimum_logs:
        console_logs += driver.get_log("browser")
        time.sleep(0.1)

    return console_logs
