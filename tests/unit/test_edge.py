from unittest import mock

import eel.edge as edge


def test_run_uses_pipe_when_stdout_is_unavailable():
    options = {"cmdline_args": [], "app_mode": True}

    with (
        mock.patch.object(edge.sys, "stdout", None),
        mock.patch.object(edge.sys, "stderr", None),
        mock.patch.object(edge.sps, "Popen") as popen,
    ):
        edge.run("unused", options, ["http://localhost:8000/"])

    popen.assert_called_once()
    _, kwargs = popen.call_args
    assert kwargs["stdout"] == edge.sps.PIPE
    assert kwargs["stderr"] == edge.sps.PIPE
    assert kwargs["shell"] is True


def test_run_opens_edge_in_app_mode():
    options = {"cmdline_args": ["--start-fullscreen"], "app_mode": True}

    with mock.patch.object(edge.sps, "Popen") as popen:
        edge.run("unused", options, ["http://localhost:8000/"])

    command = popen.call_args.args[0]
    assert "start msedge --app=http://localhost:8000/" in command


def test_run_opens_edge_in_new_window_mode():
    options = {"cmdline_args": ["--inprivate"], "app_mode": False}

    with mock.patch.object(edge.sps, "Popen") as popen:
        edge.run("unused", options, ["http://localhost:8000/"])

    command = popen.call_args.args[0]
    assert "start msedge --new-window --inprivate http://localhost:8000/" == command