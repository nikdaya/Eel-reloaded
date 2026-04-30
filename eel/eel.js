eel = {
  _host: window.location.origin,

  set_host: function (hostname) {
    eel._host = hostname;
  },

  expose: function (f, name) {
    if (name === undefined) {
      name = f.toString();
      let i = "function ".length,
        j = name.indexOf("(");
      name = name.substring(i, j).trim();
    }

    eel._exposed_functions[name] = f;
  },

  guid: function () {
    return eel._guid;
  },

  // These get dynamically added by library when file is served
  /** _py_functions **/
  /** _start_geometry **/
  /** _start_options **/

  _guid: ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) =>
    (
      c ^
      (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))
    ).toString(16),
  ),

  _exposed_functions: {},

  _mock_queue: [],

  _websocket: null,

  _websocket_state: "idle",

  _websocket_error: null,

  _websocket_open_timeout: 10000,

  _websocket_open_timer: null,

  _ready_promise: null,

  _ready_resolve: null,

  _ready_reject: null,

  _start_options: { disable_spinner: false },

  ready: function () {
    return eel._ready_promise;
  },

  set_connection_timeout: function (ms) {
    eel._websocket_open_timeout = ms;
  },

  toUint8Array: function (value) {
    if (value instanceof Uint8Array) {
      return value;
    }

    if (Array.isArray(value)) {
      return new Uint8Array(value);
    }

    throw new TypeError(
      "toUint8Array expects a Uint8Array or number[] payload.",
    );
  },

  fromUint8Array: function (value) {
    if (value instanceof Uint8Array) {
      return Array.from(value);
    }

    if (ArrayBuffer.isView(value)) {
      return Array.from(
        new Uint8Array(value.buffer, value.byteOffset, value.byteLength),
      );
    }

    throw new TypeError("fromUint8Array expects a Uint8Array-like payload.");
  },

  _mock_py_functions: function () {
    for (let i = 0; i < eel._py_functions.length; i++) {
      let name = eel._py_functions[i];
      eel[name] = function () {
        let call_object = eel._call_object(name, arguments);
        if (
          eel._websocket_state === "failed" ||
          eel._websocket_state === "closed"
        ) {
          return eel._call_return(call_object, eel._websocket_error);
        }
        eel._mock_queue.push(call_object);
        return eel._call_return(call_object);
      };
    }
  },

  _import_py_function: function (name) {
    let func_name = name;
    eel[name] = function () {
      let call_object = eel._call_object(func_name, arguments);
      if (
        eel._websocket == null ||
        eel._websocket.readyState !== WebSocket.OPEN
      ) {
        return eel._call_return(
          call_object,
          eel._websocket_error || new Error("Eel websocket is not open."),
        );
      }

      try {
        eel._websocket.send(eel._toJSON(call_object));
      } catch (error) {
        eel._handle_connection_closed(error);
        return eel._call_return(call_object, error);
      }

      return eel._call_return(call_object);
    };
  },

  _call_number: 0,

  _call_return_callbacks: {},

  _call_object: function (name, args) {
    let arg_array = [];
    for (let i = 0; i < args.length; i++) {
      arg_array.push(args[i]);
    }

    let call_id = (eel._call_number += 1) + Math.random();
    return { call: call_id, name: name, args: arg_array };
  },

  _sleep: function (ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },

  _toJSON: function (obj) {
    return JSON.stringify(obj, (k, v) => (v === undefined ? null : v));
  },

  _normalize_error: function (error, fallback_message) {
    if (error instanceof Error) {
      return error;
    }

    if (typeof error === "string" && error.length > 0) {
      return new Error(error);
    }

    return new Error(fallback_message);
  },

  _reset_ready_promise: function () {
    eel._ready_promise = new Promise(function (resolve, reject) {
      eel._ready_resolve = resolve;
      eel._ready_reject = reject;
    });
  },

  _clear_websocket_open_timer: function () {
    if (eel._websocket_open_timer != null) {
      window.clearTimeout(eel._websocket_open_timer);
      eel._websocket_open_timer = null;
    }
  },

  _reject_pending_calls: function (error) {
    let pending_calls = Object.keys(eel._call_return_callbacks);
    for (let i = 0; i < pending_calls.length; i++) {
      let call_id = pending_calls[i];
      let callbacks = eel._call_return_callbacks[call_id];
      delete eel._call_return_callbacks[call_id];

      if (callbacks.reject) {
        callbacks.reject(error);
      }
    }
  },

  _handle_connection_failure: function (error) {
    if (
      eel._websocket_state === "failed" ||
      eel._websocket_state === "closed"
    ) {
      return;
    }

    eel._clear_websocket_open_timer();
    eel._websocket_error = eel._normalize_error(
      error,
      "Eel websocket connection failed before opening.",
    );

    if (eel._websocket_state !== "open") {
      eel._websocket_state = "failed";
      if (eel._ready_reject != null) {
        eel._ready_reject(eel._websocket_error);
        eel._ready_reject = null;
        eel._ready_resolve = null;
      }
    } else {
      eel._websocket_state = "closed";
    }

    eel._mock_queue = [];
    eel._reject_pending_calls(eel._websocket_error);
  },

  _handle_connection_closed: function (error) {
    if (
      eel._websocket_state === "closed" ||
      eel._websocket_state === "failed"
    ) {
      return;
    }

    if (eel._websocket_state !== "open") {
      eel._handle_connection_failure(error);
      return;
    }

    eel._clear_websocket_open_timer();
    eel._websocket_state = "closed";
    eel._websocket_error = eel._normalize_error(
      error,
      "Eel websocket closed unexpectedly.",
    );
    eel._reject_pending_calls(eel._websocket_error);
  },

  _call_return: function (call, error = null) {
    return function (callback = null) {
      if (error != null) {
        if (callback != null) {
          return;
        }

        return Promise.reject(error);
      }

      if (callback != null) {
        eel._call_return_callbacks[call.call] = { resolve: callback };
      } else {
        return new Promise(function (resolve, reject) {
          eel._call_return_callbacks[call.call] = {
            resolve: resolve,
            reject: reject,
          };
        });
      }
    };
  },

  _position_window: function (page) {
    let size = eel._start_geometry["default"].size;
    let position = eel._start_geometry["default"].position;

    if (page in eel._start_geometry.pages) {
      size = eel._start_geometry.pages[page].size;
      position = eel._start_geometry.pages[page].position;
    }

    if (size != null) {
      window.resizeTo(size[0], size[1]);
    }

    if (position != null) {
      window.moveTo(position[0], position[1]);
    }
  },

  _disable_bootstrap_spinners: function () {
    const selectors = [
      "[data-eel-spinner]",
      "[data-loading='spinner']",
      ".eel-spinner",
      ".loading-spinner",
      ".spinner-overlay",
      "#spinner",
      "#loading",
      "#loading-spinner",
    ];

    for (let i = 0; i < selectors.length; i++) {
      let elements = document.querySelectorAll(selectors[i]);
      for (let j = 0; j < elements.length; j++) {
        let element = elements[j];
        element.setAttribute("aria-hidden", "true");
        element.style.display = "none";
      }
    }

    if (document.body != null) {
      document.body.classList.remove("loading", "is-loading", "spinner-active");
      document.body.setAttribute("data-eel-spinner-disabled", "true");
    }

    document.documentElement.classList.remove(
      "loading",
      "is-loading",
      "spinner-active",
    );
    document.documentElement.setAttribute("data-eel-spinner-disabled", "true");
  },

  _init: function () {
    eel._mock_py_functions();
    eel._reset_ready_promise();

    document.addEventListener("DOMContentLoaded", function (event) {
      if (eel._start_options && eel._start_options.disable_spinner === true) {
        eel._disable_bootstrap_spinners();
      }

      let page = window.location.pathname.substring(1);
      eel._position_window(page);

      let websocket_addr = (eel._host + "/eel").replace("http", "ws");
      websocket_addr += "?page=" + page;
      eel._websocket_state = "connecting";
      eel._websocket_error = null;
      eel._websocket = new WebSocket(websocket_addr);
      eel._websocket_open_timer = window.setTimeout(function () {
        eel._handle_connection_failure(
          new Error("Eel websocket connection timed out before opening."),
        );
        if (
          eel._websocket != null &&
          eel._websocket.readyState === WebSocket.CONNECTING
        ) {
          eel._websocket.close();
        }
      }, eel._websocket_open_timeout);

      eel._websocket.onopen = function () {
        eel._clear_websocket_open_timer();
        eel._websocket_state = "open";
        if (eel._ready_resolve != null) {
          eel._ready_resolve();
          eel._ready_resolve = null;
          eel._ready_reject = null;
        }

        for (let i = 0; i < eel._py_functions.length; i++) {
          let py_function = eel._py_functions[i];
          eel._import_py_function(py_function);
        }

        while (eel._mock_queue.length > 0) {
          let call = eel._mock_queue.shift();
          eel._websocket.send(eel._toJSON(call));
        }
      };

      eel._websocket.onerror = function () {
        eel._handle_connection_failure(
          new Error("Eel websocket connection failed."),
        );
      };

      eel._websocket.onclose = function (event) {
        let close_message = "Eel websocket closed";
        if (event && typeof event.code === "number") {
          close_message += " with code " + event.code;
        }
        close_message += ".";

        if (eel._websocket_state === "open") {
          eel._handle_connection_closed(new Error(close_message));
        } else {
          eel._handle_connection_failure(new Error(close_message));
        }
      };

      eel._websocket.onmessage = function (e) {
        let message = JSON.parse(e.data);
        if (message.hasOwnProperty("call")) {
          // Python making a function call into us
          if (message.name in eel._exposed_functions) {
            try {
              let return_val = eel._exposed_functions[message.name](
                ...message.args,
              );
              eel._websocket.send(
                eel._toJSON({
                  return: message.call,
                  status: "ok",
                  value: return_val,
                }),
              );
            } catch (err) {
              debugger;
              eel._websocket.send(
                eel._toJSON({
                  return: message.call,
                  status: "error",
                  error: err.message,
                  stack: err.stack,
                }),
              );
            }
          }
        } else if (message.hasOwnProperty("return")) {
          // Python returning a value to us
          if (message["return"] in eel._call_return_callbacks) {
            let callbacks = eel._call_return_callbacks[message["return"]];
            delete eel._call_return_callbacks[message["return"]];

            if (message["status"] === "ok") {
              callbacks.resolve(message.value);
            } else if (message["status"] === "error" && callbacks.reject) {
              callbacks.reject(message["error"]);
            }
          }
        } else {
          throw "Invalid message " + message;
        }
      };
    });
  },
};

eel._init();

if (typeof require !== "undefined") {
  // Avoid name collisions when using Electron, so jQuery etc work normally
  window.nodeRequire = require;
  delete window.require;
  delete window.exports;
  delete window.module;
}
