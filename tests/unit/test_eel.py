import asyncio
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
