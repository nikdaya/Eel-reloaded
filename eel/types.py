from __future__ import annotations
from typing import Any, Callable, Literal, TYPE_CHECKING, TypeAlias, TypedDict

# TYPE_CHECKING guards keep runtime dependencies on jinja2 and starlette optional.
if TYPE_CHECKING:
    from jinja2 import Environment as JinjaEnvironmentT
    from starlette.websockets import WebSocket as WebSocketT
else:
    JinjaEnvironmentT = Any
    WebSocketT = Any


StartPageT: TypeAlias = str | dict[str, str | int]


class OptionsDictT(TypedDict, total=False):
    mode: str | Literal[False] | None
    host: str
    port: int
    block: bool
    jinja_templates: str | None
    cmdline_args: list[str]
    size: tuple[int, int] | None
    position: tuple[int, int] | None
    geometry: dict[str, tuple[int, int]]
    close_callback: Callable[..., Any] | None
    app_mode: bool
    all_interfaces: bool
    disable_cache: bool
    default_path: str
    icon: str | Literal[False] | None
    shutdown_delay: float
    suppress_error: bool
    jinja_env: JinjaEnvironmentT
