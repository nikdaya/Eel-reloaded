# Eel-reloaded v0.19.0

Release date: 2026-04-22

This release modernizes the runtime stack, simplifies dependencies, and improves reliability and security while preserving the existing runtime import path (`import eel`).

## Highlights

- Async web stack migration:
  - Replaced bottle + gevent with starlette + uvicorn.
  - Native asyncio architecture with no gevent monkey patching.
- Leaner dependency model:
  - Replaced pyparsing usage with stdlib `re` for exposed JS function discovery.
  - Removed importlib_resources and typing_extensions backports.
- Improved reliability of Python-JS bridge:
  - Better failure handling for pending JS calls when websocket never opens or closes unexpectedly.
  - Added explicit bootstrap controls via `eel.ready()` and `eel.set_connection_timeout(ms)`.
  - Thread-safe protection for internal return value/callback maps and event-loop-safe scheduling.
- Security hardening:
  - Static file path traversal protection (rejects paths escaping configured root).
- Packaging and distribution updates:
  - Project now uses `pyproject.toml` build metadata.
  - Distribution name is `eel-reloaded` while runtime import remains `eel`.
- UX polish:
  - Default bundled favicon when pages do not define one.
  - `eel.start(icon=...)` can override or disable icon behavior.

## Breaking changes

- Minimum supported Python version is now 3.12.
  - Python 3.7, 3.8, 3.9, 3.10, and 3.11 are no longer supported.

## Migration notes

- Install/upgrade with the new distribution name:
  - `pip install -U eel-reloaded`
- Keep your application imports unchanged:
  - `import eel`
- If frontend startup races with bridge calls, initialize explicitly:
  - Load `/eel.js` in the page.
  - Await `eel.ready()` before first bridge use.

## Reference

- Changelog entry: `CHANGELOG.md` -> section `0.19.0`
- Previous release: `v0.18.2`
