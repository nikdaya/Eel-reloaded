# Eel-reloaded

> [!IMPORTANT]
> Eel-reloaded is a modernization fork of the original Eel project. It keeps the familiar `import eel` API for small HTML/JS desktop-style apps, while updating the runtime for modern Python and a maintained ASGI stack.

![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
![Maintained](https://img.shields.io/badge/maintenance-active-brightgreen?style=for-the-badge)

Eel-reloaded is a small Python library for building desktop-style HTML/JS apps with full access to Python code and packages.

> **Eel-reloaded hosts a local webserver, then lets you annotate functions in Python so that they can be called from Javascript, and vice versa.**

If you are already comfortable with Python and web development, jump directly to [examples/04 - file_access](examples/04%20-%20file_access) for a minimal end-to-end app.

<!-- TOC -->

- [Eel-reloaded](#eel-reloaded)
  - [Quick Start](#quick-start)
  - [When to use Eel-reloaded](#when-to-use-eel-reloaded)
  - [Screenshots](#screenshots)
  - [What's new in Eel-reloaded](#whats-new-in-eel-reloaded)
  - [Support The Project](#support-the-project)
  - [Intro](#intro)
  - [Install](#install)
  - [Usage](#usage)
    - [Directory Structure](#directory-structure)
    - [Starting the app](#starting-the-app)
    - [App options](#app-options)
    - [Exposing functions](#exposing-functions)
    - [Hello, World!](#hello-world)
    - [Return values](#return-values)
      - [Callbacks](#callbacks)
      - [Synchronous returns](#synchronous-returns)
  - [Asynchronous Python](#asynchronous-python)
  - [Building distributable binary with PyInstaller](#building-distributable-binary-with-pyinstaller)
  - [Microsoft Edge](#microsoft-edge)
  - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)

<!-- /TOC -->

## Quick Start

Install and run a first app in under a minute:

```shell
pip install eel-reloaded
```

```python
import eel

eel.init("web")
eel.start("main.html")
```

Then add `eel.js` in your page and expose a Python function:

```html
<script type="text/javascript" src="/eel.js"></script>
```

```python
@eel.expose
def ping(name):
    return f"Hello {name}!"
```

```javascript
await eel.ping("Eel")();
```

## When to use Eel-reloaded

Eel-reloaded is a good fit when you want:

- a desktop-style app UI built with HTML, CSS and JavaScript
- direct Python access (filesystem, scripts, existing business logic)
- faster iteration than Electron-level application scaffolding
- a lightweight utility app for internal teams or power users

Eel-reloaded is probably not the best fit when you need:

- a heavy multi-window desktop platform with deep native integrations
- highly locked-down sandboxing requirements
- full browser-engine bundling guarantees out of the box

## Screenshots

Classic native-style file picker example:

<p align="center"><img src="examples/04%20-%20file_access/Screenshot.png" width="520" alt="File access example screenshot" /></p>

React example with Python and browser console interaction:

<p align="center"><img src="examples/07%20-%20CreateReactApp/Demo.png" width="900" alt="React example screenshot" /></p>

## Intro

Python has many GUI options, but when your UI is web-based you often end up writing unnecessary plumbing between browser code and backend logic. Eel-reloaded is designed to remove most of that boilerplate.

The project keeps the simple Eel programming model while modernizing the runtime. You write frontend code with standard HTML/CSS/JavaScript, expose Python functions with decorators, and call both sides over a lightweight local bridge.

Compared to heavier desktop stacks, Eel-reloaded is intentionally focused on small and medium desktop-style applications: internal tools, operator consoles, data entry apps, automation dashboards, and utility frontends for existing Python code.

This fork preserves the original ergonomics while replacing the legacy Bottle/Gevent stack with Starlette, Uvicorn, and `asyncio`, and by actively maintaining compatibility fixes and quality-of-life improvements.

Source code for this fork lives at [nikdaya/Eel-reloaded](https://github.com/nikdaya/Eel-reloaded).

## What's new in Eel-reloaded

Eel-reloaded is an actively maintained fork of the now-archived [python-eel/Eel](https://github.com/python-eel/Eel) project. The table below summarises the key differences:

| Feature                                | Original Eel             | Eel-reloaded                                   |
| -------------------------------------- | ------------------------ | ---------------------------------------------- |
| Web server runtime                     | Bottle + Gevent          | **Starlette + Uvicorn (ASGI / asyncio)**       |
| Python version                         | 3.6+                     | **3.12+**                                      |
| `bytes` / `bytearray` return values    | silently `null` in JS    | **serialised to `list[int]` (lossless)**       |
| Concurrent WebSocket sends             | potential race condition | **per-socket `asyncio.Lock`**                  |
| JS proxy calls from background threads | may deadlock             | **thread-safe, queued before connect**         |
| Jinja2 template context                | not supported            | **`context=` kwarg on `jinja_templates`**      |
| Window geometry                        | `size` + `position` only | **full `geometry` dict per page**              |
| `eel.ready()` on JS side               | not available            | **Promise resolving when WS is usable**        |
| Pending JS calls on timeout            | hang forever             | **rejected with a clear error**                |
| Init scan exclusions                   | not available            | **`exclude_paths=` in `eel.init()`**           |
| Custom HTTP routes                     | not available            | **`extra_routes=` in `eel.start()`**           |
| Resource loading                       | `pkg_resources`          | **`importlib.resources`** (stdlib)             |
| Default favicon                        | none                     | **bundled SVG icon, configurable via `icon=`** |
| Maintenance status                     | archived                 | **actively maintained ✓**                      |

## Support The Project

If Eel-reloaded is useful in your work, sponsorship helps keep maintenance moving: issue triage, compatibility updates, tests, releases, and documentation all take recurring time.

The repository is already configured for GitHub's native funding links through `.github/FUNDING.yml`. Public donation links are intentionally left unset until they point to the actual Eel-reloaded maintainers rather than the archived upstream project.

If you want to support the project now:

- open an issue proposing the funding platform you would use most (`GitHub Sponsors`, `Ko-fi`, `Open Collective`, `Patreon`)
- mention whether your company would consider recurring sponsorship for maintenance
- reach out before funding is enabled if you want to sponsor a specific fix, feature, or release cadence

Once maintainer accounts are finalized, the GitHub `Sponsor` button can be enabled without further README restructuring.

## Install

Install from PyPI with `pip`:

```shell
pip install eel-reloaded
```

The distribution name is `eel-reloaded`, while the import path remains `eel` for compatibility. To include support for HTML templating, currently using [Jinja2](https://pypi.org/project/Jinja2/#description):

```shell
pip install "eel-reloaded[jinja2]"
```

## Usage

### Directory Structure

An Eel-reloaded application will be split into a frontend consisting of various web-technology files (.html, .js, .css) and a backend consisting of various Python scripts.

All the frontend files should be put in a single directory (they can be further divided into folders inside this if necessary).

```
my_python_script.py     <-- Python scripts
other_python_module.py
static_web_folder/      <-- Web folder
  main_page.html
  css/
    style.css
  img/
    logo.png
```

### Starting the app

Suppose you put all the frontend files in a directory called `web`, including your start page `main.html`, then the app is started like this;

```python
import eel
eel.init('web')
eel.start('main.html')
```

This will start a webserver on the default settings (http://localhost:8000) and open a browser to http://localhost:8000/main.html.

If Chrome or Chromium is installed then by default it will open in that in App Mode (with the `--app` cmdline flag), regardless of what the OS's default browser is set to (it is possible to override this behaviour).

If you have a large frontend bundle and do not need Python to call JS functions exposed from every asset, pass `exclude_paths=[...]` to `eel.init()` to skip selected files or directories while Eel-reloaded scans for `eel.expose(...)` declarations.

### App options

Pass options to `eel.start()` as keyword arguments.

Example:

```python
eel.start(
    "main.html",
    mode="chrome",
    app_mode=True,
    port=0,
    size=(1200, 800),
    cmdline_args=["--start-fullscreen"],
)
```

#### Server and network

| Option           | Type                                    | Default        | Description                                                          |
| ---------------- | --------------------------------------- | -------------- | -------------------------------------------------------------------- |
| `host`           | `str`                                   | `'localhost'`  | Hostname used by the web server.                                     |
| `port`           | `int`                                   | `8000`         | Port used by the web server. Use `0` for auto-pick.                  |
| `all_interfaces` | `bool`                                  | `False`        | Listen on all interfaces instead of localhost only.                  |
| `default_path`   | `str`                                   | `'index.html'` | File served for `/`.                                                 |
| `disable_cache`  | `bool`                                  | `True`         | Serve assets with `Cache-Control: no-store`.                         |
| `extra_routes`   | `list[Route \| WebSocketRoute] \| None` | `None`         | Extra Starlette routes inserted before Eel's static catch-all route. |

#### Browser and window behavior

| Option         | Type                                    | Default                    | Description                                                                                                |
| -------------- | --------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `mode`         | `str \| None \| False`                  | `'chrome'`                 | Browser backend (`'chrome'`, `'electron'`, `'edge'`, `'msie'`, `'custom'`) or no window when `None/False`. |
| `app_mode`     | `bool`                                  | `True`                     | Launch Chrome/Edge in app-style window mode.                                                               |
| `cmdline_args` | `list[str]`                             | `['--disable-http-cache']` | Extra command-line flags for browser startup.                                                              |
| `size`         | `tuple[int, int] \| None`               | `None`                     | Main window `(width, height)` in pixels.                                                                   |
| `position`     | `tuple[int, int] \| None`               | `None`                     | Main window `(left, top)` in pixels.                                                                       |
| `geometry`     | `dict[str, dict[str, tuple[int, int]]]` | `{}`                       | Per-page window geometry, e.g. `{'page.html': {'size': (200, 100), 'position': (300, 50)}}`.               |
| `icon`         | `str \| None \| False`                  | `None`                     | Fallback favicon URL/path (`None` uses bundled icon, `False` disables injection).                          |

#### Lifecycle and templates

| Option            | Type               | Default | Description                                                                                   |
| ----------------- | ------------------ | ------- | --------------------------------------------------------------------------------------------- |
| `block`           | `bool`             | `True`  | Whether `eel.start()` blocks the calling thread.                                              |
| `jinja_templates` | `str \| None`      | `None`  | Folder used for Jinja2 templates.                                                             |
| `close_callback`  | `Callable \| None` | `None`  | Callback called when a websocket/page closes. Receives `(closed_page, remaining_websockets)`. |
| `shutdown_delay`  | `float`            | `1.0`   | Delay before automatic shutdown check after socket close.                                     |
| `suppress_error`  | `bool`             | `False` | Suppress transitional compatibility warning for old API usage.                                |



### Exposing functions

In addition to the files in the frontend folder, a Javascript library will be served at `/eel.js`. You should include this in any pages:

```html
<script type="text/javascript" src="/eel.js"></script>
```

Including this library creates an `eel` object which can be used to communicate with the Python side.

The frontend bridge now exposes `eel.ready()` and `eel.set_connection_timeout(ms)`. `eel.ready()` resolves when the websocket is usable and rejects if the initial connection fails, while pending `await eel.some_python_call()()` calls are now rejected instead of hanging forever when the websocket never opens.

Any functions in the Python code which are decorated with `@eel.expose` like this...

```python
@eel.expose
def my_python_function(a, b):
    print(a, b, a + b)
```

...will appear as methods on the `eel` object on the Javascript side, like this...

```javascript
console.log("Calling Python...");
eel.my_python_function(1, 2); // This calls the Python function that was decorated
```

By default, exposed Python functions run in a worker thread (`execution="worker"`).
For APIs that must run on Python's main thread (for example Tkinter dialogs), set:

```python
@eel.expose(execution="main")
def choose_file_native():
  ...
```

Use `execution="main"` only for UI APIs that require it. Running heavy work in main-thread mode can block the event loop and delay websocket responses.

For a full working example, see [examples/11 - main_thread_file_picker](examples/11%20-%20main_thread_file_picker).

Similarly, any Javascript functions which are exposed like this...

```javascript
eel.expose(my_javascript_function);
function my_javascript_function(a, b, c, d) {
  if (a < b) {
    console.log(c * d);
  }
}
```

can be called from the Python side like this...

```python
print('Calling Javascript...')
eel.my_javascript_function(1, 2, 3, 4)  # This calls the Javascript function
```

The exposed name can also be overridden by passing in a second argument. If your app minifies JavaScript during builds, this may be necessary to ensure that functions can be resolved on the Python side:

```javascript
eel.expose(someFunction, "my_javascript_function");
```

When passing complex objects as arguments, bear in mind that internally they are converted to JSON and sent down a websocket (a process that potentially loses information).

### Hello, World!

> See full example in: [examples/01 - hello_world](examples/01%20-%20hello_world)

Putting this together into a **Hello, World!** example, we have a short HTML page, `web/hello.html`:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Hello, World!</title>

    <!-- Include eel.js - note this file doesn't exist in the 'web' directory -->
    <script type="text/javascript" src="/eel.js"></script>
    <script type="text/javascript">
      eel.expose(say_hello_js); // Expose this function to Python
      function say_hello_js(x) {
        console.log("Hello from " + x);
      }

      say_hello_js("Javascript World!");
      eel.say_hello_py("Javascript World!"); // Call a Python function
    </script>
  </head>

  <body>
    Hello, World!
  </body>
</html>
```

and a short Python script `hello.py`:

```python
import eel

# Set web files folder and optionally specify which file types to check for eel.expose()
#   *Default allowed_extensions are: ['.js', '.html', '.txt', '.htm', '.xhtml']
eel.init('web', allowed_extensions=['.js', '.html'], exclude_paths=['build/static'])

@eel.expose                         # Expose this function to Javascript
def say_hello_py(x):
    print('Hello from %s' % x)

say_hello_py('Python World!')
eel.say_hello_js('Python World!')   # Call a Javascript function

eel.start('hello.html')             # Start (this blocks and enters loop)
```

If we run the Python script (`python hello.py`), then a browser window will open displaying `hello.html`, and we will see...

```
Hello from Python World!
Hello from Javascript World!
```

...in the terminal, and...

```
Hello from Javascript World!
Hello from Python World!
```

...in the browser console (press F12 to open).

You will notice that in the Python code, the Javascript function is called before the browser window is even started - any early calls like this are queued up and then sent once the websocket has been established.

### Return values

While we want to think of our code as comprising a single application, the Python interpreter and the browser window run in separate processes. This can make communicating back and forth between them a bit of a mess, especially if we always had to explicitly _send_ values from one side to the other.

Eel supports two ways of retrieving _return values_ from the other side of the app, which helps keep the code concise.

To prevent hanging forever on the Python side, a timeout has been put in place for trying to retrieve values from
the JavaScript side, which defaults to 10000 milliseconds (10 seconds). This can be changed with the `_js_result_timeout` parameter to `eel.init`. There is no corresponding timeout on the JavaScript side.

#### Callbacks

When you call an exposed function, you can immediately pass a callback function afterwards. This callback will automatically be called asynchronously with the return value when the function has finished executing on the other side.

For example, if we have the following function defined and exposed in Javascript:

```javascript
eel.expose(js_random);
function js_random() {
  return Math.random();
}
```

Then in Python we can retrieve random values from the Javascript side like so:

```python
def print_num(n):
    print('Got this from Javascript:', n)

# Call Javascript function, and pass explicit callback function
eel.js_random()(print_num)

# Do the same with an inline lambda as callback
eel.js_random()(lambda n: print('Got this from Javascript:', n))
```

(It works exactly the same the other way around).

#### Synchronous returns

In most situations, the calls to the other side are to quickly retrieve some piece of data, such as the state of a widget or contents of an input field. In these cases it is more convenient to just synchronously wait a few milliseconds then continue with your code, rather than breaking the whole thing up into callbacks.

To synchronously retrieve the return value, simply pass nothing to the second set of brackets. So in Python we would write:

```python
n = eel.js_random()()  # This immediately returns the value
print('Got this from Javascript:', n)
```

You can only perform synchronous returns after the browser window has started (after calling `eel.start()`), otherwise obviously the call will hang.

In Javascript, the language doesn't allow us to block while we wait for a callback, except by using `await` from inside an `async` function. So the equivalent code from the Javascript side would be:

```javascript
async function run() {
  // Inside a function marked 'async' we can use the 'await' keyword.

  let n = await eel.py_random()(); // Must prefix call with 'await', otherwise it's the same syntax
  console.log("Got this from Python: " + n);
}

run();
```

## Asynchronous Python

Eel-reloaded now runs on Starlette, Uvicorn and `asyncio`. Exposed Python functions are executed in a thread pool so the ASGI event loop stays responsive while your application code runs. There is no Gevent monkey-patching in the runtime anymore.

For most cases you should still avoid using raw `time.sleep()` in the main control flow and prefer the helpers exposed by Eel-reloaded. `eel.sleep()` remains the convenient cross-example sleep primitive, and `eel.spawn()` now returns a standard `concurrent.futures.Future` instead of a Gevent greenlet.

In this example...

```python
import eel
eel.init('web')

def my_other_thread():
    while True:
        print("I'm a thread")
        eel.sleep(1.0)                  # Use eel.sleep(), not time.sleep()

eel.spawn(my_other_thread)

eel.start('main.html', block=False)     # Don't block on this call

while True:
    print("I'm a main loop")
    eel.sleep(1.0)                      # Use eel.sleep(), not time.sleep()
```

...we would then have three concurrent execution contexts running;

1. Eel-reloaded's internal server thread for serving the web folder
2. The `my_other_thread` method, repeatedly printing **"I'm a thread"**
3. The main Python thread, which would be stuck in the final `while` loop, repeatedly printing **"I'm a main loop"**

## Building distributable binary with PyInstaller

If you want to package your app into a program that can be run on a computer without a Python interpreter installed, you should use **PyInstaller**.

1. Configure a virtualenv with desired Python version and minimum necessary Python packages
2. Install PyInstaller `pip install PyInstaller`
3. In your app's folder, run `python -m eel [your_main_script] [your_web_folder]` (for example, you might run `python -m eel hello.py web`)
4. This will create a new folder `dist/`
5. Valid PyInstaller flags can be passed through, such as excluding modules with the flag: `--exclude module_name`. For example, you might run `python -m eel file_access.py web --exclude win32com --exclude numpy --exclude cryptography`
6. When happy that your app is working correctly, add `--onefile --noconsole` flags to build a single executable file

Consult the [documentation for PyInstaller](http://PyInstaller.readthedocs.io/en/stable/) for more options.

## Microsoft Edge

For Windows 10 users, Microsoft Edge (`eel.start(.., mode='edge')`) is installed by default and a useful fallback if a preferred browser is not installed. See the examples:

- A Hello World example using Microsoft Edge: [examples/01 - hello_world-Edge/](examples/01%20-%20hello_world-Edge)
- Example implementing browser-fallbacks: [examples/07 - CreateReactApp/eel_CRA.py](examples/07%20-%20CreateReactApp/eel_CRA.py)

## Troubleshooting

Common issues and quick checks:

- `await eel.some_call()()` hangs in JavaScript:
  Ensure the page includes `/eel.js`, then call `await eel.ready()` before first bridge usage.
- Python call times out waiting for JavaScript return value:
  Increase `_js_result_timeout` in `eel.init(...)` when your frontend call is intentionally slow.
- Exposed JS functions are not found after frontend build/minification:
  Use explicit alias form, e.g. `window.eel.expose(fn, 'stable_name')`.
- App exits when you refresh a page during development:
  Use `shutdown_delay` in `eel.start(...)` to tolerate short websocket reconnect windows.
- Browser opens but app UI does not load:
  Verify `eel.init('web_folder')` path and `default_path` / `start` URL names.
- Edge app mode behavior differs across machines:
  Test with `mode='edge', app_mode=True` and keep browser flags in `cmdline_args` explicit for reproducibility.
- `RuntimeError: main thread is not in main loop` when calling native dialogs (Tkinter):
  Expose that function with `@eel.expose(execution="main")` and run `eel.start(..., block=True)` from the Python main thread. See [examples/11 - main_thread_file_picker](examples/11%20-%20main_thread_file_picker).

If the issue persists, open an issue with:

- OS and Python version
- browser and version
- minimal reproducible snippet (Python + HTML/JS)
- traceback / console errors

## Contributing

Contributions of all kinds are welcome - bug fixes, new features, tests, documentation improvements, and new examples.

### Getting started

```shell
git clone https://github.com/nikdaya/Eel-reloaded.git
cd Eel-reloaded
pip install -e ".[jinja2]"
pip install -r requirements-test.txt
pytest tests/unit/          # fast, no browser required
```

The integration tests in `tests/integration/` require a local Chrome/Chromium install and run the real browser. Use `tox` to run the full test matrix.

### Areas actively looking for help

- **Browser tests**: integration tests for Edge, Firefox (via `mode='custom'`), and Electron are sparse. More coverage is welcome.
- **WebSocket stress tests**: the per-socket send-lock mitigates concurrent-send races but a proper load-testing harness would help validate the fix under real traffic.
- **Typing**: `eel/types.py` has partial type annotations; improving coverage helps IDEs and mypy.
- **Examples**: additional examples showing React (Vite), Vue, or Svelte frontends.
- **Upstream issue triage**: many open issues in the original repo have not been evaluated for relevance in this ASGI-based fork. Checking them and noting which are fixed, obsolete, or still applicable is a big help.

### Code conventions

- Format with `black` (line length 99, configured in `pyproject.toml`).
- Tests live in `tests/unit/` (pytest, no browser) and `tests/integration/` (Selenium).
- Commits follow conventional commits (`fix:`, `feat:`, `test:`, `style:`, `docs:`).

Please open an issue before starting large changes so we can coordinate.
