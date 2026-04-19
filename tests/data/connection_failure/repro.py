from pathlib import Path
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[2]))

import eel


eel.init(str(EXAMPLE_DIR / "web"))


@eel.expose
def get_app_state():
    return {"status": "ok"}


eel.start("boot.html", size=(320, 200))
