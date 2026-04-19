from pathlib import Path
import sys

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parents[1]))

import eel
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route


async def custom_route(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Hello, World!")


eel.init(str(EXAMPLE_DIR / "web"))

eel.start("index.html", extra_routes=[Route("/custom", custom_route)])
