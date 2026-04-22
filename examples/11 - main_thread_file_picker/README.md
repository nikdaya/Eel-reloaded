# Example 11 - main_thread_file_picker

This example demonstrates how to expose a Python function that must run on the main thread.

Why this matters:

- Native Tkinter dialogs (`askopenfilename`, `askdirectory`, etc.) require the Python main thread.
- Eel defaults exposed function execution to worker threads.
- Use `@eel.expose(execution="main")` for these specific APIs.

Run:

```bash
python app.py
```

Then click "Choose file" to open the native file picker.

Important notes:

- Keep `eel.start(..., block=True)` so the event loop runs on the main thread.
- Use main-thread execution only for APIs that require it. CPU-bound tasks should stay on `execution="worker"`.
