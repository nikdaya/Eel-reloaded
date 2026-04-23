# Eel-reloaded Roadmap

This roadmap tracks agreed improvements with practical status markers.

## High priority

- [x] Stabilize startup and integration timing behavior.
  - Increased server-ready wait timeout from 5s to configurable timeout (`EEL_SERVER_READY_TIMEOUT_SECONDS`, default 15s).
  - Added unit coverage for timeout failure path.
- [x] Tighten type safety for start options.
  - `OptionsDictT` now models runtime-required keys and optional `jinja_env` explicitly.
  - Removed mutable defaults in `start(...)` signature (`cmdline_args`, `geometry`).
- [x] Align release publishing with `pyproject.toml` build flow.
  - GitHub publish workflow now builds with `python -m build` (sdist + wheel), not `setup.py sdist`.

## Medium priority

- [x] Binary bridge ergonomics (`bytes` <-> `Uint8Array`) first implementation.
  - Python helpers: `to_uint8_array(...)`, `from_uint8_array(...)`.
  - JS helpers: `eel.toUint8Array(...)`, `eel.fromUint8Array(...)`.
  - Unit tests added for both Python and JS helper exposure.
- [ ] Add production-like app skeleton example.
  - Pending: sample project with logging strategy, reconnect handling, and error boundaries.
- [x] Extend security-related tests.
  - Added unit regression for static-file path traversal blocking.

## Notes

- iOS is not a first-class target for Eel-reloaded's architecture.
- Ubuntu/Linux desktop remains a supported and practical deployment target.
