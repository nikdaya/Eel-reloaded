from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel


eel.init(str(EXAMPLE_DIR / "web"))


@eel.expose(execution="main")
def choose_file() -> str:
    """Open a native file picker on the Python main thread.

    Tkinter dialogs require main-thread execution, so this function is
    intentionally exposed with execution="main".
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(title="Select a file")
    finally:
        root.destroy()

    return selected or ""


eel.start("index.html", size=(700, 280), block=True)
