#!/usr/bin/env python3
"""
WebPageButtonPlugin for Dynaframe Pro.

A GPIO button shows web pages on top of the slideshow:
- Short press, browser closed: opens the first configured page full screen (kiosk window).
- Short press, browser open: switches to the next page. After the last page it starts again
  with the first one, or closes the browser if CloseAfterLastPage is enabled.
- Long press (LongPressSeconds, default 2 s): closes the browser, the slideshow is visible again.

With only one configured page, a short press toggles it (open / close).

The pages are shown by a separate browser process (Chromium or Firefox), so the plugin does not
depend on the DynaFrame engine API. Closing the window (instead of minimizing it) works the same
on X11 and Wayland; a page is reloaded every time it is shown.
"""

import os
import sys
import traceback
from datetime import datetime

# lgpio (the gpiozero backend on the Pi 5) creates a notify pipe file in the current
# working directory. Switch to a directory that is guaranteed to be writable first.
_plugin_dir = os.environ.get("DYNAFRAME_PLUGIN_DIR") or os.path.dirname(os.path.abspath(__file__))
try:
    os.chdir(_plugin_dir)
except Exception:
    pass

_crash_log_path = os.path.join(_plugin_dir, "crash.log")


def _write_crash_log(exc_type, exc_value, exc_tb):
    try:
        with open(_crash_log_path, "a") as f:
            f.write(f"\n=== Crash at {datetime.now().isoformat()} ===\n")
            f.write(f"cwd={os.getcwd()}\n")
            f.write(f"sys.executable={sys.executable}\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _write_crash_log

import atexit
import glob
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from gpiozero import Button

sys.path.insert(0, str(Path(__file__).parent.parent))
from dynaframe_plugin_base import create_plugin

plugin = create_plugin()

_PROFILE_DIR = os.path.join(_plugin_dir, "browser-profile")
_BROWSER_LOG = os.path.join(_plugin_dir, "browser.log")
_DEBOUNCE_SECONDS = 0.4

_lock = threading.Lock()
_shutdown_event = threading.Event()
_proc = None
_index = -1          # index of the page that is currently shown (-1 = none)
_last_press = 0.0
_long_pressed = False


# --------------------------------------------------------------------------
# GPIO chip detection (the chip number differs between kernels, e.g. gpiochip0,
# gpiochip4 or gpiochip15, but gpiozero only tries 4 and 0)
# --------------------------------------------------------------------------
def _find_gpio_pin_factory():
    try:
        import lgpio
        from gpiozero.pins.lgpio import LGPIOFactory
    except Exception:
        return None

    chips = []
    for path in glob.glob("/dev/gpiochip*"):
        suffix = path[len("/dev/gpiochip"):]
        if suffix.isdigit():
            chips.append(int(suffix))

    for chip in sorted(chips):
        try:
            handle = lgpio.gpiochip_open(chip)
        except Exception:
            continue
        try:
            info = lgpio.gpio_get_chip_info(handle)
        except Exception:
            info = None
        finally:
            try:
                lgpio.gpiochip_close(handle)
            except Exception:
                pass
        if isinstance(info, (list, tuple)) and len(info) >= 4 and str(info[3]).startswith("pinctrl-"):
            try:
                factory = LGPIOFactory(chip=chip)
            except Exception:
                continue
            plugin.log(f"GPIO chip found: gpiochip{chip} ({info[3]}).")
            return factory
    return None


# --------------------------------------------------------------------------
# Browser handling
# --------------------------------------------------------------------------
def normalize_url(raw):
    url = str(raw or "").strip()
    if not url:
        return ""
    if "://" not in url:
        # Accept "host", "host/path" and "host:port/path", reject "scheme:payload" such as javascript:...
        head = url.split("/", 1)[0]
        if ":" in head and not re.fullmatch(r"[^:]+:\d+", head):
            return ""
        url = "https://" + url
    if urlparse(url).scheme not in ("http", "https", "file"):
        return ""
    return url


def _display_server():
    value = str(plugin.get_setting("DisplayServer", "wayland") or "wayland").strip().lower()
    return value if value in ("auto", "wayland", "x11") else "wayland"


def build_env():
    env = os.environ.copy()
    runtime = env.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    if os.path.isdir(runtime):
        env["XDG_RUNTIME_DIR"] = runtime

    server = _display_server()
    wayland_socket = os.path.join(runtime, env.get("WAYLAND_DISPLAY") or "wayland-0")

    if server == "x11":
        env.pop("WAYLAND_DISPLAY", None)
        env["DISPLAY"] = env.get("DISPLAY") or ":0"
    elif server == "wayland":
        env["WAYLAND_DISPLAY"] = "wayland-0"
    else:
        if not env.get("DISPLAY") and not env.get("WAYLAND_DISPLAY"):
            if os.path.exists(wayland_socket):
                env["WAYLAND_DISPLAY"] = "wayland-0"
            else:
                env["DISPLAY"] = ":0"

    xauth = os.path.expanduser("~/.Xauthority")
    if not env.get("XAUTHORITY") and os.path.exists(xauth):
        env["XAUTHORITY"] = xauth
    return env


def find_browser():
    override = str(plugin.get_setting("BrowserCommand", "") or "").strip()
    if override:
        parts = shlex.split(override)
        if parts and shutil.which(parts[0]):
            return [shutil.which(parts[0])] + parts[1:]
        plugin.log(f"BrowserCommand '{override}' was not found.", level="error")
        return None
    for name in ("chromium", "chromium-browser", "google-chrome", "firefox"):
        path = shutil.which(name)
        if path:
            return [path]
    plugin.log("No supported browser found (chromium, chromium-browser, google-chrome, firefox).", level="error")
    return None


def build_command(url):
    base = find_browser()
    if not base:
        return None
    os.makedirs(_PROFILE_DIR, exist_ok=True)
    name = os.path.basename(base[0]).lower()
    extra = shlex.split(str(plugin.get_setting("ExtraBrowserArgs", "") or ""))

    if "firefox" in name:
        return base + ["--kiosk", "--no-remote", "--profile", _PROFILE_DIR] + extra + [url]

    # Same flags as the manually tested command
    #   WAYLAND_DISPLAY=wayland-0 chromium --ozone-platform=wayland --kiosk \
    #       --noerrdialogs --password-store=basic <url>
    # plus a dedicated profile (so the plugin controls its own browser instance instead of
    # handing the URL to an already running Chromium), --no-first-run for that fresh profile
    # and --disable-session-crashed-bubble because closing the window ends the process.
    args = []
    server = _display_server()
    if server in ("wayland", "x11"):
        args.append(f"--ozone-platform={server}")
    args += [
        "--kiosk",
        "--noerrdialogs",
        "--password-store=basic",
        "--no-first-run",
        "--disable-session-crashed-bubble",
        f"--user-data-dir={_PROFILE_DIR}",
    ]
    return base + args + extra + [url]


def _clear_stale_locks():
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lock", ".parentlock"):
        try:
            os.remove(os.path.join(_PROFILE_DIR, name))
        except OSError:
            pass


def _kill_leftovers():
    """Stop browser processes of this plugin that survived an earlier run."""
    try:
        subprocess.run(["pkill", "-f", "--", _PROFILE_DIR], timeout=5,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def is_open():
    return _proc is not None and _proc.poll() is None


def get_urls():
    raw = str(plugin.get_setting("Urls", "") or "").strip()
    if not raw:
        raw = str(plugin.get_setting("Url", "") or "").strip()  # setting name of version 0.1
    urls = []
    for part in re.split(r"[\s;]+", raw):
        if not part:
            continue
        url = normalize_url(part)
        if url:
            urls.append(url)
        else:
            plugin.log(f"Ignoring invalid address: {part}", level="error")
    return urls


def open_page(url):
    global _proc
    cmd = build_command(url)
    if not cmd:
        return False
    _kill_leftovers()
    _clear_stale_locks()
    try:
        with open(_BROWSER_LOG, "w") as log_file:
            _proc = subprocess.Popen(
                cmd,
                env=build_env(),
                cwd=_plugin_dir,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except Exception as exc:
        _proc = None
        plugin.log(f"Could not start the browser: {exc}", level="error")
        return False
    plugin.log(f"Opened {url} (pid {_proc.pid}).")
    try:
        plugin.report_activity("Web page opened", url)
    except Exception:
        pass
    return True


def close_page(quiet=False):
    global _proc, _index
    proc, _proc = _proc, None
    _index = -1
    if proc is None:
        return
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
    if not quiet:
        plugin.log("Web page closed.")
        try:
            plugin.report_activity("Web page closed", "")
        except Exception:
            pass


def show_page(urls, index):
    """Show urls[index]; an open browser window is closed first."""
    global _index
    if is_open():
        close_page(quiet=True)
    if open_page(urls[index]):
        _index = index
        plugin.log(f"Showing page {index + 1} of {len(urls)}.")
    else:
        _index = -1


def on_short_press():
    global _last_press
    now = time.monotonic()
    with _lock:
        if now - _last_press < _DEBOUNCE_SECONDS:
            return
        _last_press = now
        try:
            urls = get_urls()
            if not urls:
                plugin.log("The Urls setting contains no valid http(s) address.", level="error")
                return
            if not is_open():
                current = -1
            else:
                current = _index
            next_index = current + 1
            if next_index >= len(urls):
                close_after_last = str(plugin.get_setting("CloseAfterLastPage", False)).lower() == "true"
                if current >= 0 and (close_after_last or len(urls) == 1):
                    close_page()
                    return
                next_index = 0
            show_page(urls, next_index)
        except Exception as exc:
            plugin.log(f"Short press failed: {exc}", level="error")


def on_long_press():
    with _lock:
        try:
            if is_open():
                close_page()
        except Exception as exc:
            plugin.log(f"Long press failed: {exc}", level="error")


def on_held():
    global _long_pressed
    _long_pressed = True
    on_long_press()


def on_released():
    global _long_pressed
    if _long_pressed:
        _long_pressed = False
        return
    on_short_press()


def _shutdown(*_args):
    with _lock:
        close_page()
    _shutdown_event.set()


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
def main():
    gpio_pin = int(plugin.get_setting("GpioPin", 20))
    long_press = max(0.5, float(plugin.get_setting("LongPressSeconds", 2)))

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    atexit.register(close_page)
    _kill_leftovers()

    button = Button(
        gpio_pin,
        pull_up=True,
        bounce_time=0.05,
        hold_time=long_press,
        hold_repeat=False,
        pin_factory=_find_gpio_pin_factory(),
    )
    button.when_held = on_held
    button.when_released = on_released

    plugin.log(f"WebPageButtonPlugin ready on GPIO{gpio_pin} (long press = {long_press} s).")
    plugin.ready()
    _shutdown_event.wait()


if __name__ == "__main__":
    main()
