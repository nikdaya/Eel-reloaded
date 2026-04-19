from __future__ import annotations
import platform
import subprocess as sps
import sys

from eel.types import OptionsDictT

name: str = "Edge"


def _get_subprocess_stream(stream: Any) -> Any:
    if stream is None:
        return sps.PIPE
    return stream


def run(_path: str, options: OptionsDictT, start_urls: list[str]) -> None:
    if not isinstance(options["cmdline_args"], list):
        raise TypeError("'cmdline_args' option must be of type List[str]")
    args: list[str] = options["cmdline_args"]
    stdout = _get_subprocess_stream(sys.stdout)
    stderr = _get_subprocess_stream(sys.stderr)
    if options["app_mode"]:
        cmd = "start msedge --app={} ".format(start_urls[0])
        cmd = cmd + (" ".join(args))
        sps.Popen(cmd, stdout=stdout, stderr=stderr, stdin=sps.PIPE, shell=True)
    else:
        cmd = "start msedge --new-window " + (" ".join(args)) + " " + (start_urls[0])
        sps.Popen(cmd, stdout=stdout, stderr=stderr, stdin=sps.PIPE, shell=True)


def find_path() -> bool:
    if platform.system() == "Windows":
        return True

    return False
