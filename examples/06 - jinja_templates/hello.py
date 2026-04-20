from pathlib import Path
import random
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel

eel.init(str(EXAMPLE_DIR / "web"))  # Give folder containing web files

context = eel.get_context()
context.set("users", ["Alice", "Bob", "Charlie"])
context.set("title", "Hello from Eel!")


@eel.expose
def py_random():
    return random.random()


@eel.expose  # Expose this function to Javascript
def say_hello_py(x):
    print("Hello from %s" % x)


say_hello_py("Python World!")
eel.say_hello_js("Python World!")  # Call a Javascript function

eel.start("templates/hello.html", size=(300, 200), jinja_templates="templates")  # Start
