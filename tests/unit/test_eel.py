import asyncio
import json
import mimetypes
import threading
from pathlib import Path
from unittest import mock

import eel
import pytest
from tests.utils import TEST_DATA_DIR

# Directory for testing eel.__init__
INIT_DIR = TEST_DATA_DIR / "init_test"


@pytest.mark.parametrize(
    "js_code, expected_matches",
    [
        ('eel.expose(w,"say_hello_js")', ["say_hello_js"]),
        ('eel.expose(function(e){console.log(e)},"show_log_alt")', ["show_log_alt"]),
        (
            ' \t\nwindow.eel.expose((function show_log(e) {console.log(e)}), "show_log")\n',
            ["show_log"],
        ),
        (
            (INIT_DIR / "minified.js").read_text(),
            ["say_hello_js", "show_log_alt", "show_log"],
        ),
        ((INIT_DIR / "sample.html").read_text(), ["say_hello_js"]),
        ((INIT_DIR / "App.tsx").read_text(), ["say_hello_js", "show_log"]),
        ((INIT_DIR / "hello.html").read_text(), ["say_hello_js", "js_random"]),
        (
            "const funcName = (funcParam) => { console.log(funcParam); }; window.eel.expose(funcName, 'funcName');",
            ["funcName"],
        ),
        (
            "const a=(b)=>b;window.eel.expose(a,'getEmailsPortal');",
            ["getEmailsPortal"],
        ),
    ],
)
def test_exposed_js_functions(js_code, expected_matches):
    """Test the JS-function-name extractor against several specific test cases."""
    matches = eel._find_exposed_js_functions(js_code)
    assert (
        matches == expected_matches
    ), f"Expected {expected_matches} (found: {matches}) in: {js_code}"


def test_init():
    """Test eel.init() against a test directory and ensure that all JS functions are in the global _js_functions."""
    eel.init(path=INIT_DIR)
    result = eel._js_functions.sort()
    functions = ["show_log", "js_random", "show_log_alt", "say_hello_js"].sort()
    assert result == functions, f"Expected {functions} (found: {result}) in {INIT_DIR}"


def test_init_excludes_paths_from_js_scan():
    eel.init(path=INIT_DIR, exclude_paths=["hello.html"])

    assert sorted(eel._js_functions) == ["say_hello_js", "show_log", "show_log_alt"]


def test_get_context_returns_global_context_container():
    context = eel.get_context()
    sentinel = object()

    context.set("sentinel", sentinel)

    assert eel.get_context().get("sentinel") is sentinel


def test_jinja_template_render_uses_context_values(monkeypatch):
    rendered = {}

    class FakeTemplate:
        def render(self, **kwargs):
            rendered.update(kwargs)
            return "<html></html>"

    class FakeEnv:
        def get_template(self, name):
            assert name == "hello.html"
            return FakeTemplate()

    eel.get_context().set("title", "Hello from Eel!")
    eel.get_context().set("users", ["Alice", "Bob", "Charlie"])
    eel._start_args["jinja_env"] = FakeEnv()
    eel._start_args["jinja_templates"] = "templates"

    response = asyncio.run(eel._serve_static("templates/hello.html"))

    assert response.media_type == "text/html"
    assert rendered["title"] == "Hello from Eel!"
    assert rendered["users"] == ["Alice", "Bob", "Charlie"]


def test_react_build_style_expose_aliases_remain_discoverable():
    js_code = "window.eel.expose(minifiedSymbol,'getEmailsPortal')"

    assert eel._find_exposed_js_functions(js_code) == ["getEmailsPortal"]


def test_unknown_js_function_can_be_called_from_thread_before_connect(monkeypatch):
    monkeypatch.setattr(eel, "_mock_queue", [])

    worker = threading.Thread(target=eel.reload)
    worker.start()
    worker.join()

    assert eel._mock_queue[-1]["name"] == "reload"


def test_process_message_serializes_bytes_return_values(monkeypatch):
    sent = []

    @eel.expose
    def bytes_payload():
        return b"hello"

    async def capture_send(_ws, msg):
        sent.append(json.loads(msg))

    monkeypatch.setattr(eel, "_send", capture_send)

    asyncio.run(
        eel._process_message(
            {"call": 1, "name": "bytes_payload", "args": []},
            mock.Mock(),
        )
    )

    assert sent == [
        {"return": 1, "status": "ok", "value": [104, 101, 108, 108, 111], "error": {}}
    ]


def test_expose_execution_policy_is_registered():
    @eel.expose("execution_policy_main", execution="main")
    def _sample():
        return "ok"

    assert eel._exposed_function_execution["execution_policy_main"] == "main"


def test_process_message_execution_main_runs_on_main_thread(monkeypatch):
    sent = []

    @eel.expose("thread_probe_main", execution="main")
    def thread_probe_main():
        return threading.current_thread() is threading.main_thread()

    async def capture_send(_ws, msg):
        sent.append(json.loads(msg))

    monkeypatch.setattr(eel, "_send", capture_send)

    asyncio.run(
        eel._process_message(
            {"call": 101, "name": "thread_probe_main", "args": []},
            mock.Mock(),
        )
    )

    assert sent[0]["status"] == "ok"
    assert sent[0]["value"] is True


def test_process_message_default_worker_runs_outside_main_thread(monkeypatch):
    sent = []

    @eel.expose("thread_probe_worker")
    def thread_probe_worker():
        return threading.current_thread() is threading.main_thread()

    async def capture_send(_ws, msg):
        sent.append(json.loads(msg))

    monkeypatch.setattr(eel, "_send", capture_send)

    asyncio.run(
        eel._process_message(
            {"call": 102, "name": "thread_probe_worker", "args": []},
            mock.Mock(),
        )
    )

    assert sent[0]["status"] == "ok"
    assert sent[0]["value"] is False


def test_process_message_execution_main_fails_if_event_loop_is_not_main_thread(
    monkeypatch,
):
    sent = []

    @eel.expose("thread_probe_wrong_loop", execution="main")
    def thread_probe_wrong_loop():
        return "ok"

    async def capture_send(_ws, msg):
        sent.append(json.loads(msg))

    monkeypatch.setattr(eel, "_send", capture_send)

    def run_in_background_thread():
        asyncio.run(
            eel._process_message(
                {"call": 103, "name": "thread_probe_wrong_loop", "args": []},
                mock.Mock(),
            )
        )

    worker = threading.Thread(target=run_in_background_thread)
    worker.start()
    worker.join()

    assert sent[0]["status"] == "error"
    assert "main thread" in sent[0]["error"]["errorText"]


def test_broadcast_serializes_send_per_websocket(monkeypatch):
    class FakeWebSocket:
        def __init__(self):
            self.inflight = 0
            self.max_inflight = 0
            self.messages = []

        async def send_text(self, msg):
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
            await asyncio.sleep(0)
            self.messages.append(msg)
            self.inflight -= 1

    websocket = FakeWebSocket()
    monkeypatch.setattr(eel, "_websockets", [("index.html", websocket)])
    monkeypatch.setattr(eel, "_websocket_send_locks", {})

    async def main():
        await asyncio.gather(
            *(eel._broadcast(f"message-{index}") for index in range(10))
        )

    asyncio.run(main())

    assert websocket.max_inflight == 1
    assert len(websocket.messages) == 10


def test_start_waits_for_server_before_show(monkeypatch):
    order = []

    class FakeServer:
        def __init__(self, config):
            self.config = config
            self.should_exit = False

        def run(self):
            order.append("run")
            eel._loop_ready.set()

    monkeypatch.setattr(eel, "_build_asgi_app", lambda: object())
    monkeypatch.setattr(eel.uvicorn, "Server", FakeServer)
    monkeypatch.setattr(eel, "show", lambda *start_urls: order.append("show"))

    eel.start("index.html", mode=False, block=False)

    assert order == ["run", "show"]


def test_start_timeout_error_mentions_configured_seconds(monkeypatch):
    class FakeServer:
        def __init__(self, config):
            self.config = config
            self.should_exit = False

        def run(self):
            return None

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            return None

        def join(self, timeout=None):
            return None

    class NeverSetEvent:
        def clear(self):
            return None

        def wait(self, timeout=None):
            return False

    monkeypatch.setattr(eel, "_build_asgi_app", lambda: object())
    monkeypatch.setattr(eel.uvicorn, "Server", FakeServer)
    monkeypatch.setattr(eel.threading, "Thread", FakeThread)
    monkeypatch.setattr(eel, "_loop_ready", NeverSetEvent())
    monkeypatch.setattr(eel, "_server_ready_timeout_seconds", 1.25)

    with pytest.raises(RuntimeError, match="1.2 seconds"):
        eel.start("index.html", mode=False, block=False)


def test_serve_static_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(eel, "root_path", str(tmp_path))
    eel._start_args["disable_cache"] = True

    response = asyncio.run(eel._serve_static("..\\outside.txt"))

    assert response.status_code == 403


def test_show_stores_geometry_for_string_pages(monkeypatch):
    opened = {}
    eel._start_args["geometry"] = {}

    monkeypatch.setattr(
        eel.brw,
        "open",
        lambda start_pages, options: opened.update(
            {"start_pages": start_pages, "options": options.copy()}
        ),
    )

    eel.show("slider.html", size=(400, 200), position=(40, 40))

    assert opened["start_pages"] == ["slider.html"]
    assert eel._start_args["geometry"]["slider.html"] == {
        "size": (400, 200),
        "position": (40, 40),
    }


def test_show_stores_geometry_for_dict_pages(monkeypatch):
    opened = {}
    eel._start_args["geometry"] = {}

    monkeypatch.setattr(
        eel.brw,
        "open",
        lambda start_pages, options: opened.update(
            {"start_pages": start_pages, "options": options.copy()}
        ),
    )

    eel.show({"path": "slider.html", "port": 9000}, size=(500, 300))

    assert opened["start_pages"] == [{"path": "slider.html", "port": 9000}]
    assert eel._start_args["geometry"]["slider.html"] == {"size": (500, 300)}


def test_websocket_close_with_callback_still_schedules_shutdown(monkeypatch):
    scheduled = {}
    callback = mock.Mock()

    class FakeLoop:
        def call_later(self, delay, func):
            scheduled["delay"] = delay
            scheduled["func"] = func
            return "handle"

    monkeypatch.setattr(eel, "_loop", FakeLoop())
    monkeypatch.setattr(eel, "_shutdown", None)
    monkeypatch.setattr(eel, "_websockets", [])
    eel._start_args["close_callback"] = callback
    eel._start_args["shutdown_delay"] = 1.5

    eel._websocket_close("index.html")

    callback.assert_called_once_with("index.html", [])
    assert scheduled == {"delay": 1.5, "func": eel._detect_shutdown}


def test_detect_shutdown_requests_server_exit(monkeypatch):
    server = mock.Mock()

    monkeypatch.setattr(eel, "_server", server)
    monkeypatch.setattr(eel, "_websockets", [])

    eel._detect_shutdown()

    assert server.should_exit is True


def test_inject_icon_link_uses_default_icon():
    eel._start_args["icon"] = None
    html = "<html><head><title>Test</title></head><body>Hello</body></html>"

    result = eel._inject_icon_link(html)

    assert '<link rel="icon" href="/eel-reloaded-icon.svg">' in result


def test_inject_icon_link_preserves_existing_icon():
    eel._start_args["icon"] = "/custom-icon.svg"
    html = (
        '<html><head><link rel="icon" href="/existing.ico"></head>'
        "<body>Hello</body></html>"
    )

    result = eel._inject_icon_link(html)

    assert result == html


def test_inject_icon_link_can_be_disabled():
    eel._start_args["icon"] = False
    html = "<html><head><title>Test</title></head><body>Hello</body></html>"

    result = eel._inject_icon_link(html)

    assert result == html


def test_get_icon_href_normalizes_relative_paths():
    eel._start_args["icon"] = "assets/app-icon.svg"

    assert eel._get_icon_href() == "/assets/app-icon.svg"


def test_favicon_handler_falls_back_to_bundled_icon(tmp_path, monkeypatch):
    eel._start_args["disable_cache"] = True
    monkeypatch.setattr(eel, "root_path", str(tmp_path))

    response = asyncio.run(eel._favicon_handler(mock.Mock()))

    assert response.media_type == "image/svg+xml"
    assert b"<svg" in response.body


def test_runtime_package_does_not_use_pkg_resources():
    source = Path(eel.__file__).read_text(encoding="utf-8")

    assert "pkg_resources" not in source
    assert "importlib.resources" in source


def test_eel_js_exposes_connection_failure_apis():
    assert "ready: function" in eel._eel_js
    assert "set_connection_timeout: function" in eel._eel_js
    assert "_handle_connection_failure: function" in eel._eel_js


def test_binary_bridge_helpers_roundtrip():
    payload = b"\x00\x01\x7f\xff"
    as_list = eel.to_uint8_array(payload)

    assert as_list == [0, 1, 127, 255]
    assert eel.from_uint8_array(as_list) == payload


def test_eel_js_exposes_binary_bridge_helpers():
    assert "toUint8Array: function" in eel._eel_js
    assert "fromUint8Array: function" in eel._eel_js


def test_wasm_mimetype_is_registered():
    assert mimetypes.guess_type("module.wasm")[0] == "application/wasm"
