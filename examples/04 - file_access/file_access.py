import os
from pathlib import Path
import random
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel

eel.init(str(EXAMPLE_DIR / "web"))


@eel.expose
def pick_file(folder):
    if os.path.isdir(folder):
        return random.choice(os.listdir(folder))
    else:
        return "Not valid folder"


eel.start("file_access.html", size=(320, 120))
