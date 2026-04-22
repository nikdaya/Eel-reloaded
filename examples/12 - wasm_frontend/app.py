from pathlib import Path
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel


eel.init(str(EXAMPLE_DIR / "web"))
eel.start("index.html", size=(980, 720))
