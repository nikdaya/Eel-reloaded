# Temporary Upstream Triage

Delete this file after the upstream items below have been either implemented in Eel-reloaded, explicitly rejected, or moved into permanent tracking.

## Pull Requests To Review First

### High Priority

| PR | Title | Why it matters for Eel-reloaded | Notes |
| --- | --- | --- | --- |
| #761 | Fix JS memory leak + modernize `eel.js` | Strong candidate for the current JS bridge; touches only `eel/__init__.py` and `eel/eel.js`. | Compare carefully against local JS bridge changes already added in `eel-reloaded`. |
| #760 | Fixes #757 | Minimal fix for the JS-side callback retention leak. | Already effectively covered in the current fork: callbacks are deleted before `resolve/reject` in `eel.js`. |
| #697 | Increase initialisation speed by optionally excluding files to scan | Direct response to `eel.init()` slowness on large frontend bundles. | In progress in the fork via `exclude_paths` support for init-time JS scanning. |
| #612 | Run Edge in app mode | Small, local feature improvement in `eel/edge.py`. | Already effectively present in the current fork. |
| #626 | Edge Build with `--noconsole` Crash Fix | Potentially valuable packaging/runtime fix with narrow scope. | In progress in the fork via safer Edge subprocess stream handling. |

### Medium Priority

| PR | Title | Why it matters for Eel-reloaded | Notes |
| --- | --- | --- | --- |
| #681 | Make Eel work with Microsoft Edge on Linux | Useful platform support extension with limited surface area. | In progress in the fork via direct Linux executable discovery with `shutil.which`. |
| #756 | Pass Arguments to jinja Template | Useful feature for Jinja users. | Implemented in the fork via `eel.get_context()` and template context injection. |
| #687 | Add websocket reconnect functionality | May improve resilience after backend restarts. | High behavioral risk because the fork already changed websocket failure handling. |

### Low Priority / Likely Skip For Now

| PR | Title | Notes |
| --- | --- | --- |
| #671 | Add Vite React Example | Example-only value, low runtime impact. |
| #743 | Add archival notice | Not relevant for the maintained fork. |
| #387 / #373 / #261 / #328 / #338 / #368 | Older PRs | Likely too tied to the legacy architecture or too stale to port directly. |

## Issues To Track Alongside The PRs

### High Priority

| Issue | Title | Why it matters for Eel-reloaded | Related PR |
| --- | --- | --- | --- |
| #757 | Memory leak: allocated data got in JS from Python is never freed | Real bug with clear repro; matches current JS bridge area. | #760, #761 |
| #689 | `init` function is considerable slowness | Important for users shipping large SPA bundles. | #697 |
| #650 | Cannot read properties of undefined (reading `send`) | Historically important websocket startup/failure issue. | Current fork already guards JS sends behind `WebSocket.OPEN` and rejects failed calls instead of throwing on undefined send. |
| #561 | Browser pops up before server is properly initialized | Classic startup race. | Implemented in the fork by launching the browser only after server readiness. |
| #692 | `shutdown_delay` doesn't work | Relevant because shutdown semantics changed in the fork. | Implemented in the fork by scheduling shutdown even when `close_callback` is present. |

### Medium Priority

| Issue | Title | Why it matters for Eel-reloaded | Related PR |
| --- | --- | --- | --- |
| #690 | Icon issue | Likely at least partially addressed by the new fallback favicon behavior. | Re-tested in the fork with fallback favicon handler coverage. |
| #718 | Edge Chromium App mode | Good UX improvement on Windows. | #612 |
| #703 | Eel with threading doesn't recognize exposed functions | Still worth validating on the fork because threading behavior changed with the ASGI migration. | None yet |
| #702 | Eel sometimes takes infinitely long to render a webpage | Startup/render stability issue; may overlap with websocket readiness changes. | Possibly adjacent to #687 |
| #674 | Eel unable to parse arrow functions after `npm run build` | Still relevant for modern frontend workflows. | None yet |
| #732 | Javascript function in React doesn't work after build in Prod | Likely related to static JS scanning and build output shape. | Possibly adjacent to #697 and existing CRA docs |

### Lower Priority / Reassess Later

| Issue | Title | Notes |
| --- | --- | --- |
| #751 | Error in `eel.show` with specified coordinates and dimensions | Likely API gap/bug, but not as urgent as memory or startup behavior. |
| #753 | `eel.expose()` does not work with a dynamic js function name | Could require analyzer changes; lower short-term value. |
| #536 | Invalid frame header under heavy websocket load | Important, but may need dedicated repro and may not match the new runtime failure mode exactly. |
| #610 | Program still running after user closes the window | Re-test first, because shutdown handling has already changed in the fork. Likely only addressable at the server loop level, not arbitrary user threads. |

## Recommended Implementation Order

1. Finish and validate PR `#756`-style Jinja template context support.
2. Re-test React/build issues `#674` and `#732` against the current fork.
3. Revisit PR `#761` only for non-invasive improvements that still add value beyond the already-ported leak fix.
4. Leave PR `#687` until the websocket lifecycle is more settled.

## Cleanup Reminder

Delete `UPSTREAM_TRIAGE_TEMP.md` once these items have been implemented, rejected, or moved into a permanent issue tracker / project board.