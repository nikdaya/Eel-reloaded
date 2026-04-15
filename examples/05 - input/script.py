from pathlib import Path
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel

eel.init(str(EXAMPLE_DIR / "web"))  # Give folder containing web files


@eel.expose  # Expose this function to Javascript
def handleinput(x):
    print("%s" % x)


eel.say_hello_js("connected!")  # Call a Javascript function

eel.start("main.html", size=(500, 200))  # Start
