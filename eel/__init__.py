from __future__ import annotations
import traceback
import json as jsn
import re as rgx
import os
import sys
import socket
import time
import mimetypes
import asyncio
import threading
import concurrent.futures
from contextlib import asynccontextmanager
from typing import Any, Callable, Literal, cast
from eel.types import GeometryRectT, OptionsDictT, StartPageT, WebSocketT
import random as rnd
import importlib.resources as importlib_resources
import uvicorn
from starlette.routing import Route, WebSocketRoute
from starlette.responses import Response, FileResponse
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
import eel.browsers as brw


mimetypes.add_type("application/javascript", ".js")

_eel_js_reference = importlib_resources.files("eel") / "eel.js"
with importlib_resources.as_file(_eel_js_reference) as _eel_js_path:
    _eel_js: str = _eel_js_path.read_text(encoding="utf-8")

_eel_icon_reference = importlib_resources.files("eel") / "eel-icon.svg"
with importlib_resources.as_file(_eel_icon_reference) as _eel_icon_path:
    _eel_icon: str = _eel_icon_path.read_text(encoding="utf-8")

_websockets: list[tuple[Any, WebSocket]] = []
_websocket_send_locks: dict[int, asyncio.Lock] = {}
_call_return_values: dict[Any, Any] = {}
_call_return_callbacks: dict[
    float, tuple[Callable[..., Any], Callable[..., Any] | None]
] = {}
_call_number: int = 0
_exposed_functions: dict[Any, Any] = {}
_js_functions: list[Any] = []
_mock_queue: list[Any] = []
_mock_queue_done: set[Any] = set()
_shutdown: asyncio.TimerHandle | None = None
_loop: asyncio.AbstractEventLoop | None = None
_server: uvicorn.Server | None = None
_loop_ready = threading.Event()
_executor: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor()
)
_return_lock = threading.Lock()  # guards _call_return_values and _call_return_callbacks
root_path: str  # Later assigned as global by init()

# The maximum time (in milliseconds) that Python will try to retrieve a return value for functions executing in JS
# Can be overridden through `eel.init` with the kwarg `js_result_timeout` (default: 10000)
_js_result_timeout: int = 10000

# Attribute holding the start args from calls to eel.start()
_start_args: OptionsDictT = {}

# Extra Starlette routes injected via eel.start(extra_routes=[...])
_extra_routes: list = []


class Context:
    """Container for variables injected into Jinja template rendering."""

    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}

    def set(self, name: str, value: Any) -> None:
        self._variables[name] = value

    def get(self, name: str) -> Any:
        return self._variables.get(name)

    def get_all(self) -> dict[str, Any]:
        return self._variables.copy()


_context: Context = Context()

# == Temporary (suppressible) error message to inform users of breaking API change for v1.0.0 ===
api_error_message: str = """
----------------------------------------------------------------------------------
  'options' argument deprecated in v1.0.0, see https://github.com/ChrisKnott/Eel
  To suppress this error, add 'suppress_error=True' to start() call.
  This option will be removed in future versions
----------------------------------------------------------------------------------
"""
# ===============================================================================================


# Public functions


def expose(name_or_function: Callable[..., Any] | None = None) -> Callable[..., Any]:
    """Decorator to expose Python callables via Eel's JavaScript API.

    When an exposed function is called, a callback function can be passed
    immediately afterwards. This callback will be called asynchronously with
    the return value (possibly `None`) when the Python function has finished
    executing.

    Blocking calls to the exposed function from the JavaScript side are only
    possible using the :code:`await` keyword inside an :code:`async function`.
    These still have to make a call to the response, i.e.
    :code:`await eel.py_random()();` inside an :code:`async function` will work,
    but just :code:`await eel.py_random();` will not.

    :Example:

    In Python do:

    .. code-block:: python

        @expose
        def say_hello_py(name: str = 'You') -> None:
            print(f'{name} said hello from the JavaScript world!')

    In JavaScript do:

    .. code-block:: javascript

        eel.say_hello_py('Alice')();

    Expected output on the Python console::

        Alice said hello from the JavaScript world!

    """
    # Deal with '@eel.expose()' - treat as '@eel.expose'
    if name_or_function is None:
        return expose

    if isinstance(name_or_function, str):  # Called as '@eel.expose("my_name")'
        name = name_or_function

        def decorator(function: Callable[..., Any]) -> Any:
            _expose(name, function)
            return function

        return decorator
    else:
        function = name_or_function
        _expose(function.__name__, function)
        return function


def get_context() -> Context:
    """Return the global Jinja template context container."""
    return _context


# Regex to find JS functions exposed via eel.expose() or window.eel.expose().
# Handles: eel.expose(name), eel.expose("name"), eel.expose(expr, "name"),
#          eel.expose((function(e){}), "name"), window.eel.expose(name, 'alias')
_EXPOSE_RE: rgx.Pattern[str] = rgx.compile(
    r"(?:window\.)?eel\.expose\s*\("
    r"(?:.*?,\s*)?"  # optional: skip first arg (non-greedy, handles nested parens via backtracking)
    r"\s*['\"]?([\w$]+)['\"]?\s*"
    r"\)",
    rgx.DOTALL,
)


def _find_exposed_js_functions(contents: str) -> list[str]:
    """Find all JS function names exposed via eel.expose() in *contents*.

    Returns names in order of appearance, deduplicated while preserving order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for m in _EXPOSE_RE.finditer(contents):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _is_excluded_scan_path(scan_path: str, excluded_scan_paths: list[str]) -> bool:
    normalized_scan_path = os.path.normcase(os.path.normpath(scan_path))

    for excluded_scan_path in excluded_scan_paths:
        normalized_excluded_scan_path = os.path.normcase(
            os.path.normpath(os.path.join(root_path, excluded_scan_path))
        )
        if normalized_scan_path == normalized_excluded_scan_path:
            return True
        if normalized_scan_path.startswith(normalized_excluded_scan_path + os.sep):
            return True

    return False


def init(
    path: str,
    allowed_extensions: list[str] = [".js", ".html", ".txt", ".htm", ".xhtml", ".vue"],
    exclude_paths: list[str] | None = None,
    js_result_timeout: int = 10000,
) -> None:
    """Initialise Eel.

    This function should be called before :func:`start()` to initialise the
    parameters for the web interface, such as the path to the files to be
    served.

    :param path: Sets the path on the filesystem where files to be served to
        the browser are located, e.g. :file:`web`.
    :param allowed_extensions: A list of filename extensions which will be
        parsed for exposed eel functions which should be callable from python.
        Files with extensions not in *allowed_extensions* will still be served,
        but any JavaScript functions, even if marked as exposed, will not be
        accessible from python.
        *Default:* :code:`['.js', '.html', '.txt', '.htm', '.xhtml', '.vue']`.
    :param exclude_paths: Optional list of files or directories relative to the
        initialised web root that should be skipped while scanning for exposed
        JavaScript functions.
    :param js_result_timeout: How long Eel should be waiting to register the
        results from a call to Eel's JavaScript API before before timing out.
        *Default:* :code:`10000` milliseconds.
    """
    global root_path, _js_functions, _js_result_timeout
    root_path = _get_real_path(path)
    exclude_paths = exclude_paths or []

    js_functions = set()
    for root, _, files in os.walk(root_path):
        for name in files:
            if not any(name.endswith(ext) for ext in allowed_extensions):
                continue

            file_path = os.path.join(root, name)
            if _is_excluded_scan_path(file_path, exclude_paths):
                continue

            try:
                with open(file_path, encoding="utf-8") as file:
                    contents = file.read()
                    matches = _find_exposed_js_functions(contents)
                    js_functions.update(matches)
            except UnicodeDecodeError:
                pass  # Malformed file probably

    _js_functions = list(js_functions)
    for js_function in _js_functions:
        _mock_js_function(js_function)

    _js_result_timeout = js_result_timeout


def start(
    *start_urls: StartPageT,
    mode: str | Literal[False] | None = "chrome",
    host: str = "localhost",
    port: int = 8000,
    block: bool = True,
    jinja_templates: str | None = None,
    cmdline_args: list[str] = ["--disable-http-cache"],
    size: tuple[int, int] | None = None,
    position: tuple[int, int] | None = None,
    geometry: dict[str, tuple[int, int]] = {},
    close_callback: Callable[..., Any] | None = None,
    app_mode: bool = True,
    all_interfaces: bool = False,
    disable_cache: bool = True,
    default_path: str = "index.html",
    icon: str | Literal[False] | None = None,
    shutdown_delay: float = 1.0,
    suppress_error: bool = False,
    extra_routes: list | None = None,
) -> None:
    """Start the Eel app.

    Suppose you put all the frontend files in a directory called
    :file:`web`, including your start page :file:`main.html`, then the app
    is started like this:

    .. code-block:: python

        import eel
        eel.init('web')
        eel.start('main.html')

    This will start a webserver on the default settings
    (http://localhost:8000) and open a browser to
    http://localhost:8000/main.html.

    If Chrome or Chromium is installed then by default it will open that in
    *App Mode* (with the `--app` cmdline flag), regardless of what the OS's
    default browser is set to (it is possible to override this behaviour).

    :param mode: What browser is used, e.g. :code:`'chrome'`,
        :code:`'electron'`, :code:`'edge'`, :code:`'custom'`. Can also be
        `None` or `False` to not open a window. *Default:* :code:`'chrome'`.
    :param host: Hostname used for the web server. *Default:*
        :code:`'localhost'`.
    :param port: Port used for the web server. Use :code:`0` for port to be
        picked automatically. *Default:* :code:`8000`.
    :param block: Whether the call to :func:`start()` blocks the calling
        thread. *Default:* `True`.
    :param jinja_templates: Folder for :mod:`jinja2` templates, e.g.
        :file:`my_templates`. *Default:* `None`.
    :param cmdline_args: A list of strings to pass to the command starting the
        browser. For example, we might add extra flags to Chrome with
        :code:`eel.start('main.html', mode='chrome-app', port=8080,
        cmdline_args=['--start-fullscreen', '--browser-startup-dialog'])`.
        *Default:* :code:`[]`.
    :param size: Tuple specifying the (width, height) of the main window in
        pixels. *Default:* `None`.
    :param position: Tuple specifying the (left, top) position of the main
        window in pixels. *Default*: `None`.
    :param geometry: A dictionary of specifying the size/position for all
        windows. The keys should be the relative path of the page, and the
        values should be a dictionary of the form
        :code:`{'size': (200, 100), 'position': (300, 50)}`. *Default:*
        :code:`{}`.
    :param close_callback: A lambda or function that is called when a websocket
        or window closes (i.e. when the user closes the window). It should take
        two arguments: a string which is the relative path of the page that
        just closed, and a list of the other websockets that are still open.
        *Default:* `None`.
    :param app_mode: Whether to run Chrome/Edge in App Mode. You can also
        specify *mode* as :code:`mode='chrome-app'` as a shorthand to start
        Chrome in App Mode.
    :param all_interfaces: Whether to allow the server to listen on all interfaces.
    :param disable_cache: Sets the no-store response header when serving
        assets.
    :param default_path: The default file to retrieve for the root URL.
    :param icon: Fallback icon used when the served HTML page does not define
        its own ``<link rel="icon">``. Pass a web path/URL such as
        :code:`'/assets/app-icon.svg'` to use your own asset, leave as
        ``None`` to use the bundled Eel-reloaded icon, or pass ``False`` to
        disable automatic icon injection.
    :param shutdown_delay: Timer configurable for Eel's shutdown detection
        mechanism, whereby when any websocket closes, it waits *shutdown_delay*
        seconds, and then checks if there are now any websocket connections.
        If not, then Eel closes. In case the user has closed the browser and
        wants to exit the program. *Default:* :code:`1.0` seconds.
    :param suppress_error: Temporary (suppressible) error message to inform
        users of breaking API change for v1.0.0. Set to `True` to suppress
        the error message.
    :param extra_routes: A list of Starlette :class:`~starlette.routing.Route`
        or :class:`~starlette.routing.WebSocketRoute` objects to add to the
        ASGI app *before* Eel's catch-all static-file route. Use this to add
        custom HTTP endpoints to the same server. *Default:* ``None``.
    """
    global _extra_routes
    _extra_routes = list(extra_routes) if extra_routes else []
    if mode == "chrome-app":
        mode = "chrome"
        app_mode = True
    _start_args.update(
        {
            "mode": mode,
            "host": host,
            "port": port,
            "block": block,
            "jinja_templates": jinja_templates,
            "cmdline_args": cmdline_args,
            "size": size,
            "position": position,
            "geometry": geometry,
            "close_callback": close_callback,
            "app_mode": app_mode,
            "all_interfaces": all_interfaces,
            "disable_cache": disable_cache,
            "default_path": default_path,
            "icon": icon,
            "shutdown_delay": shutdown_delay,
            "suppress_error": suppress_error,
        }
    )

    if _start_args["port"] == 0:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        _start_args["port"] = sock.getsockname()[1]
        sock.close()

    if _start_args["jinja_templates"] is not None:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        if not isinstance(_start_args["jinja_templates"], str):
            raise TypeError("'jinja_templates' start_arg/option must be of type str")
        templates_path = os.path.join(root_path, _start_args["jinja_templates"])
        _start_args["jinja_env"] = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=select_autoescape(["html", "xml"]),
        )

    # verify shutdown_delay is correct value
    if not isinstance(_start_args["shutdown_delay"], (int, float)):
        raise ValueError(
            "`shutdown_delay` must be a number, "
            "got a {}".format(type(_start_args["shutdown_delay"]))
        )

    if _start_args["all_interfaces"] is True:
        HOST = "0.0.0.0"
    else:
        if not isinstance(_start_args["host"], str):
            raise TypeError("'host' start_arg/option must be of type str")
        HOST = _start_args["host"]

    global _server

    asgi_app = _build_asgi_app()
    config = uvicorn.Config(
        app=asgi_app,
        host=HOST,
        port=_start_args["port"],
        log_level="error",
    )
    server = uvicorn.Server(config)
    _server = server

    _loop_ready.clear()
    server_thread = threading.Thread(target=server.run, daemon=not _start_args["block"])
    server_thread.start()

    if not _loop_ready.wait(timeout=5.0):
        server.should_exit = True
        server_thread.join(timeout=5.0)
        raise RuntimeError("Eel server did not become ready within 5 seconds")

    try:
        # Launch the browser only after the ASGI server is ready to accept connections.
        show(*start_urls)
    except Exception:
        server.should_exit = True
        server_thread.join(timeout=5.0)
        raise

    if _start_args["block"]:
        server_thread.join()


def show(
    *start_urls: StartPageT,
    size: tuple[int, int] | None = None,
    position: tuple[int, int] | None = None,
) -> None:
    """Show the specified URL(s) in the browser.

    Suppose you have two files in your :file:`web` folder. The file
    :file:`hello.html` regularly includes :file:`eel.js` and provides
    interactivity, and the file :file:`goodbye.html` does not include
    :file:`eel.js` and simply provides plain HTML content not reliant on Eel.

    First, we defien a callback function to be called when the browser
    window is closed:

    .. code-block:: python

        def last_calls():
           eel.show('goodbye.html')

    Now we initialise and start Eel, with a :code:`close_callback` to our
    function:

    ..code-block:: python

        eel.init('web')
        eel.start('hello.html', mode='chrome-app', close_callback=last_calls)

    When the websocket from :file:`hello.html` is closed (e.g. because the
    user closed the browser window), Eel will wait *shutdown_delay* seconds
    (by default 1 second), then call our :code:`last_calls()` function, which
    opens another window with the :file:`goodbye.html` shown before our Eel app
    terminates.

    :param start_urls: One or more URLs to be opened.
    :param size: Tuple specifying the (width, height) of each opened Eel page.
        Stored in the per-page geometry map so the page can resize itself once
        :file:`eel.js` loads.
    :param position: Tuple specifying the (left, top) position of each opened
        Eel page. Stored in the per-page geometry map so the page can move
        itself once :file:`eel.js` loads.
    """
    if size is not None or position is not None:
        geometry = _start_args.setdefault("geometry", {})
        for page in start_urls:
            page_path = _get_geometry_page_path(page)
            if page_path is None:
                continue

            current_geometry = dict(geometry.get(page_path, {}))
            if size is not None:
                current_geometry["size"] = size
            if position is not None:
                current_geometry["position"] = position
            geometry[page_path] = cast(GeometryRectT, current_geometry)

    brw.open(list(start_urls), _start_args)


def _get_geometry_page_path(page: StartPageT) -> str | None:
    if isinstance(page, str):
        return page

    path = page.get("path")
    if isinstance(path, str):
        return path

    return None


def sleep(seconds: Union[int, float]) -> None:
    """Sleep for the given number of seconds.

    Safe to call from any Python function exposed via :func:`eel.expose`.
    Uses :func:`time.sleep` internally; exposed functions always run in a
    thread pool, so this never blocks the event loop.

    :param seconds: The number of seconds to sleep.
    """
    time.sleep(seconds)


def spawn(function: Callable[..., Any], *args: Any, **kwargs: Any) -> concurrent.futures.Future:  # type: ignore[type-arg]
    """Run *function* concurrently in a thread pool.

    Returns a :class:`concurrent.futures.Future` that resolves to the
    function's return value.

    :param function: The callable to run.
    :param args: Positional arguments forwarded to *function*.
    :param kwargs: Keyword arguments forwarded to *function*.
    """
    return _executor.submit(function, *args, **kwargs)


# ASGI app and route handlers


@asynccontextmanager
async def _lifespan(app: Starlette):  # type: ignore[type-arg]
    global _loop
    _loop = asyncio.get_running_loop()
    _loop_ready.set()
    yield


def _build_asgi_app() -> Starlette:
    routes = [
        Route("/eel.js", _eel_js_handler),
        Route("/eel-reloaded-icon.svg", _eel_icon_handler),
        Route("/favicon.ico", _favicon_handler),
        Route("/", _root_handler),
        WebSocketRoute("/eel", _websocket_handler),
        *_extra_routes,
        Route("/{path:path}", _static_handler),
    ]
    return Starlette(routes=routes, lifespan=_lifespan)


async def _eel_js_handler(request: Request) -> Response:
    start_geometry = {
        "default": {"size": _start_args["size"], "position": _start_args["position"]},
        "pages": _start_args["geometry"],
    }
    page = _eel_js.replace(
        "/** _py_functions **/", "_py_functions: %s," % list(_exposed_functions.keys())
    )
    page = page.replace(
        "/** _start_geometry **/", "_start_geometry: %s," % _safe_json(start_geometry)
    )
    headers = _cache_headers()
    return Response(content=page, media_type="application/javascript", headers=headers)


async def _eel_icon_handler(request: Request) -> Response:
    return Response(
        content=_eel_icon,
        media_type="image/svg+xml",
        headers=_cache_headers(),
    )


async def _favicon_handler(request: Request) -> Response:
    favicon_path = os.path.join(root_path, "favicon.ico")
    real_favicon = os.path.realpath(favicon_path)
    real_root = os.path.realpath(root_path)
    if real_favicon.startswith(real_root + os.sep) and os.path.isfile(real_favicon):
        response = FileResponse(real_favicon)
        for key, value in _cache_headers().items():
            response.headers[key] = value
        return response

    return await _eel_icon_handler(request)


async def _root_handler(request: Request) -> Response:
    if not isinstance(_start_args["default_path"], str):
        raise TypeError("'default_path' start_arg/option must be of type str")
    return await _serve_static(_start_args["default_path"])


async def _static_handler(request: Request) -> Response:
    path: str = request.path_params.get("path", "")
    return await _serve_static(path)


async def _serve_static(path: str) -> Response:
    if "jinja_env" in _start_args and "jinja_templates" in _start_args:
        if not isinstance(_start_args["jinja_templates"], str):
            raise TypeError("'jinja_templates' start_arg/option must be of type str")
        template_prefix = _start_args["jinja_templates"] + "/"
        if path.startswith(template_prefix):
            n = len(template_prefix)
            template = _start_args["jinja_env"].get_template(path[n:])
            return _build_html_response(template.render(**_context.get_all()))

    file_path = os.path.join(root_path, path)
    # Prevent path traversal (OWASP A01)
    real_file = os.path.realpath(file_path)
    real_root = os.path.realpath(root_path)
    if not real_file.startswith(real_root + os.sep) and real_file != real_root:
        return Response("Forbidden", status_code=403)
    if not os.path.isfile(real_file):
        return Response("Not Found", status_code=404)
    if path.endswith((".html", ".htm", ".xhtml")):
        with open(real_file, encoding="utf-8") as html_file:
            return _build_html_response(html_file.read())
    response = FileResponse(real_file)
    for key, value in _cache_headers().items():
        response.headers[key] = value
    return response


def _build_html_response(html: str) -> Response:
    return Response(
        content=_inject_icon_link(html),
        media_type="text/html",
        headers=_cache_headers(),
    )


def _inject_icon_link(html: str) -> str:
    icon_href = _get_icon_href()
    if icon_href is None:
        return html

    if rgx.search(r"<link[^>]+rel=[\"'][^\"']*icon[^\"']*[\"']", html, rgx.IGNORECASE):
        return html

    icon_link = f'<link rel="icon" href="{icon_href}">'
    head_close = rgx.search(r"</head\s*>", html, rgx.IGNORECASE)
    if head_close is not None:
        return (
            html[: head_close.start()] + icon_link + "\n" + html[head_close.start() :]
        )

    return icon_link + "\n" + html


def _get_icon_href() -> str | None:
    icon = _start_args.get("icon")
    if icon is False:
        return None
    if icon is None:
        return "/eel-reloaded-icon.svg"
    if not isinstance(icon, str):
        raise TypeError("'icon' start_arg/option must be of type str, False, or None")
    if "://" in icon or icon.startswith(("/", "data:")):
        return icon
    return "/" + icon.lstrip("/")


async def _websocket_handler(websocket: WebSocket) -> None:
    global _websockets
    await websocket.accept()
    _websocket_send_locks.setdefault(id(websocket), asyncio.Lock())

    for js_function in _js_functions:
        _import_js_function(js_function)

    page: str = websocket.query_params.get("page", "")
    if page not in _mock_queue_done:
        for call in _mock_queue:
            await _send(websocket, _safe_json(call))
        _mock_queue_done.add(page)

    _websockets.append((page, websocket))

    try:
        while True:
            try:
                msg = await websocket.receive_text()
            except (WebSocketDisconnect, RuntimeError):
                break
            message = jsn.loads(msg)
            asyncio.create_task(_process_message(message, websocket))
    finally:
        if (page, websocket) in _websockets:
            _websockets.remove((page, websocket))
        _websocket_send_locks.pop(id(websocket), None)
        _websocket_close(page)


# Private functions


async def _send(ws: WebSocket, msg: str) -> None:
    lock = _websocket_send_locks.setdefault(id(ws), asyncio.Lock())
    async with lock:
        for _ in range(100):
            try:
                await ws.send_text(msg)
                return
            except Exception:
                await asyncio.sleep(0.001)


async def _process_message(message: dict[str, Any], ws: WebSocket) -> None:
    if "call" in message:
        error_info: dict[str, Any] = {}
        try:
            func = _exposed_functions[message["name"]]
            loop = asyncio.get_running_loop()
            return_val = await loop.run_in_executor(
                _executor, lambda: func(*message["args"])
            )
            status = "ok"
        except Exception as e:
            err_traceback = traceback.format_exc()
            traceback.print_exc()
            return_val = None
            status = "error"
            error_info["errorText"] = repr(e)
            error_info["errorTraceback"] = err_traceback
        await _send(
            ws,
            _safe_json(
                {
                    "return": message["call"],
                    "status": status,
                    "value": return_val,
                    "error": error_info,
                }
            ),
        )
    elif "return" in message:
        call_id = message["return"]
        with _return_lock:
            if call_id in _call_return_callbacks:
                callback, error_callback = _call_return_callbacks.pop(call_id)
            else:
                _call_return_values[call_id] = message["value"]
                callback = None
                error_callback = None
        if callback is not None:
            if message["status"] == "ok":
                callback(message["value"])
            elif message["status"] == "error" and error_callback is not None:
                error_callback(message["error"], message["stack"])
    else:
        print("Invalid message received: ", message)


def _safe_json_default(obj: Any) -> Any:
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return list(bytes(obj))
    return None


def _safe_json(obj: Any) -> str:
    return jsn.dumps(obj, default=_safe_json_default)


def _get_real_path(path: str) -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, path)  # type: ignore # sys._MEIPASS is dynamically added by PyInstaller
    else:
        return os.path.abspath(path)


def __getattr__(name: str) -> Callable[..., Any]:
    """PEP 562 module-level __getattr__: any unknown attribute is treated as a
    JS function proxy.  This means ``eel.my_js_fn()`` always works even if the
    function was not discovered by :func:`init` (e.g. wrong CWD, or called
    before :func:`start` connects a WebSocket).
    """
    if name.startswith("_"):
        raise AttributeError(name)
    return lambda *args: _mock_call(name, args)


def _mock_js_function(f: str) -> None:
    exec('%s = lambda *args: _mock_call("%s", args)' % (f, f), globals())


def _import_js_function(f: str) -> None:
    exec('%s = lambda *args: _js_call("%s", args)' % (f, f), globals())


def _call_object(name: str, args: Any) -> dict[str, Any]:
    global _call_number
    _call_number += 1
    call_id = _call_number + rnd.random()
    return {"call": call_id, "name": name, "args": args}


def _mock_call(
    name: str, args: Any
) -> Callable[[Callable[..., Any] | None, Callable[..., Any] | None], Any]:
    call_object = _call_object(name, args)
    global _mock_queue
    _mock_queue += [call_object]
    return _call_return(call_object)


def _js_call(
    name: str, args: Any
) -> Callable[[Callable[..., Any] | None, Callable[..., Any] | None], Any]:
    call_object = _call_object(name, args)
    # Schedule broadcast on the event loop — safe to call from any thread.
    if _loop is not None:
        asyncio.run_coroutine_threadsafe(_broadcast(_safe_json(call_object)), _loop)
    return _call_return(call_object)


async def _broadcast(msg: str) -> None:
    """Send *msg* to all connected WebSocket clients (runs on the event loop)."""
    for _, ws in list(_websockets):  # snapshot to avoid mutation during iteration
        await _send(ws, msg)


def _call_return(
    call: dict[str, Any],
) -> Callable[[Callable[..., Any] | None, Callable[..., Any] | None], Any]:
    global _js_result_timeout
    call_id = call["call"]

    def return_func(
        callback: Callable[..., Any] | None = None,
        error_callback: Callable[..., Any] | None = None,
    ) -> Any:
        if callback is not None:
            with _return_lock:
                _call_return_callbacks[call_id] = (callback, error_callback)
        else:
            for _ in range(_js_result_timeout):
                with _return_lock:
                    if call_id in _call_return_values:
                        return _call_return_values.pop(call_id)
                time.sleep(0.001)  # runs in a thread executor, safe to block

    return return_func


def _expose(name: str, function: Callable[..., Any]) -> None:
    msg = 'Already exposed function with name "%s"' % name
    assert name not in _exposed_functions, msg
    _exposed_functions[name] = function


def _detect_shutdown() -> None:
    if len(_websockets) == 0:
        if _server is not None:
            _server.should_exit = True


def _websocket_close(page: str) -> None:
    global _shutdown

    close_callback = _start_args.get("close_callback")

    if close_callback is not None:
        if not callable(close_callback):
            raise TypeError(
                "'close_callback' start_arg/option must be callable or None"
            )
        sockets = [p for _, p in _websockets]
        close_callback(page, sockets)

    if _shutdown is not None:
        _shutdown.cancel()
    if _loop is not None:
        _shutdown = _loop.call_later(_start_args["shutdown_delay"], _detect_shutdown)


def _cache_headers() -> dict[str, str]:
    # https://stackoverflow.com/a/24748094/280852
    if _start_args.get("disable_cache"):
        return {"Cache-Control": "no-store"}
    return {}
