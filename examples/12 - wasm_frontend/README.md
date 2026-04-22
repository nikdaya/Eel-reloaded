# Example 12 - wasm_frontend

This example demonstrates frontend WebAssembly (WASM) in Eel-reloaded.

What it shows:

- loading a `.wasm` asset served by Eel's static handler
- calling an exported WASM function from JavaScript
- a tiny benchmark (`JS add` vs `WASM add`) for quick feedback
- graceful fallback messaging if WebAssembly is unavailable

Run:

```bash
python app.py
```

Then click "Run benchmark" in the UI.

Notes:

- This example focuses on browser-side WASM.
- Python remains native and unchanged (`import eel`).
