"""A small Windows tray app for controlling media with a game controller."""

from __future__ import annotations

import ctypes
import json
import os
import queue
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pygame
from comtypes import CoInitialize, CoUninitialize
from PIL import Image, ImageDraw
import pystray
from pycaw.pycaw import AudioUtilities


APP_NAME = "Spotify Controller"
POLL_DELAY = 0.02
CONFIG_PATH = Path(os.getenv("APPDATA", Path.home())) / "SpotifyController" / "config.json"

# The labels are saved in the configuration file, keeping future UI changes simple.
BUTTONS = {
    "A": 0,
    "B": 1,
    "X": 2,
    "Y": 3,
    "LB": 4,
    "RB": 5,
    "View": 6,
    "Menu": 7,
    "Left Stick": 8,
    "Right Stick": 9,
}
DEFAULT_SETTINGS = {
    "enabled": True,
    "activation_button": "LB",
    "play_pause_button": "A",
    "volume_step": 5,
}

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def send_media_key(key_code: int) -> None:
    """Send a global Windows media key."""
    ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)


def direction_from_joystick(joystick: pygame.joystick.Joystick) -> tuple[int, int]:
    """Read the D-pad. Xbox controllers normally expose it as a hat."""
    if joystick.get_numhats():
        return joystick.get_hat(0)

    if joystick.get_numaxes() >= 2:
        x = int(round(joystick.get_axis(0)))
        y = int(round(joystick.get_axis(1)))
        return x, -y
    return 0, 0


def is_button_pressed(joystick: pygame.joystick.Joystick, button: int) -> bool:
    return 0 <= button < joystick.get_numbuttons() and bool(joystick.get_button(button))


class Settings:
    """Thread-safe, persistent settings for the window and controller worker."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values = DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self) -> None:
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if isinstance(saved, dict):
            if isinstance(saved.get("enabled"), bool):
                self._values["enabled"] = saved["enabled"]
            for key in ("activation_button", "play_pause_button"):
                if saved.get(key) in BUTTONS:
                    self._values[key] = saved[key]
            if isinstance(saved.get("volume_step"), int) and 1 <= saved["volume_step"] <= 25:
                self._values["volume_step"] = saved["volume_step"]

    def get(self) -> dict[str, object]:
        with self._lock:
            return self._values.copy()

    def update(self, values: dict[str, object]) -> None:
        with self._lock:
            self._values.update(values)
            snapshot = self._values.copy()

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


class ControllerWorker(threading.Thread):
    """Poll the game controller without blocking the Tkinter window."""

    def __init__(self, settings: Settings, updates: queue.Queue[tuple[str, str]]) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self.updates = updates
        self.stop_event = threading.Event()
        self._last_connection = ""
        self._endpoint = None

    def report(self, status: str, text: str) -> None:
        marker = f"{status}:{text}"
        if marker != self._last_connection or status == "action":
            self._last_connection = marker
            self.updates.put((status, text))

    def change_volume(self, amount: float) -> None:
        if self._endpoint is None:
            self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        current = self._endpoint.GetMasterVolumeLevelScalar()
        target = max(0.0, min(1.0, current + amount))
        self._endpoint.SetMasterVolumeLevelScalar(target, None)
        self.report("action", f"Volume: {round(target * 100)}%")

    def run(self) -> None:
        joystick: pygame.joystick.Joystick | None = None
        previous_direction = (0, 0)
        previous_play_pause = False
        CoInitialize()
        pygame.init()
        pygame.joystick.init()

        try:
            while not self.stop_event.is_set():
                pygame.event.pump()

                if pygame.joystick.get_count() == 0:
                    joystick = None
                    previous_direction = (0, 0)
                    previous_play_pause = False
                    self.report("connection", "No controller connected")
                    time.sleep(0.5)
                    continue

                if joystick is None or not joystick.get_init():
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
                    self.report("connection", f"Connected: {joystick.get_name()}")

                values = self.settings.get()
                if not values["enabled"]:
                    previous_direction = (0, 0)
                    previous_play_pause = False
                    self.report("connection", "Controls are paused")
                    time.sleep(POLL_DELAY)
                    continue

                activation_button = BUTTONS[str(values["activation_button"])]
                play_pause_button = BUTTONS[str(values["play_pause_button"])]
                activation_pressed = is_button_pressed(joystick, activation_button)
                direction = direction_from_joystick(joystick) if activation_pressed else (0, 0)

                if direction != previous_direction:
                    x, y = direction
                    if x == -1:
                        send_media_key(VK_MEDIA_PREV_TRACK)
                        self.report("action", "Previous track")
                    elif x == 1:
                        send_media_key(VK_MEDIA_NEXT_TRACK)
                        self.report("action", "Next track")
                    elif y == 1:
                        self.change_volume(int(values["volume_step"]) / 100)
                    elif y == -1:
                        self.change_volume(-int(values["volume_step"]) / 100)

                play_pause = activation_pressed and is_button_pressed(joystick, play_pause_button)
                if play_pause and not previous_play_pause:
                    send_media_key(VK_MEDIA_PLAY_PAUSE)
                    self.report("action", "Play/Pause")

                previous_direction = direction
                previous_play_pause = play_pause
                time.sleep(POLL_DELAY)
        except Exception as error:  # Keep the UI useful if a driver fails.
            self.report("connection", f"Controller error: {error}")
        finally:
            pygame.quit()
            CoUninitialize()

    def stop(self) -> None:
        self.stop_event.set()


class SpotifyControllerApp:
    def __init__(self) -> None:
        self.settings = Settings()
        self.updates: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker = ControllerWorker(self.settings, self.updates)
        self.root = tk.Tk()
        self.tray_icon: pystray.Icon | None = None

        self.enabled_var = tk.BooleanVar(value=bool(self.settings.get()["enabled"]))
        self.activation_var = tk.StringVar(value=str(self.settings.get()["activation_button"]))
        self.play_pause_var = tk.StringVar(value=str(self.settings.get()["play_pause_button"]))
        self.volume_var = tk.IntVar(value=int(self.settings.get()["volume_step"]))
        self.status_var = tk.StringVar(value="Starting controller listener…")
        self.action_var = tk.StringVar(value="Ready")

        self._build_window()
        self._start_tray_icon()
        self.worker.start()
        self.root.after(100, self._process_updates)

    def _build_window(self) -> None:
        self.root.title(APP_NAME)
        self.root.geometry("360x385")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=APP_NAME, font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(frame, textvariable=self.status_var, foreground="#167a35").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 14)
        )

        ttk.Checkbutton(
            frame,
            text="Enable controller media controls",
            variable=self.enabled_var,
            command=self.save_settings,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Activation button").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self.activation_var,
            values=list(BUTTONS),
            state="readonly",
            width=18,
        ).grid(row=3, column=1, sticky="ew", pady=6)

        ttk.Label(frame, text="Play / pause button").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self.play_pause_var,
            values=list(BUTTONS),
            state="readonly",
            width=18,
        ).grid(row=4, column=1, sticky="ew", pady=6)

        ttk.Label(frame, text="Volume step").grid(row=5, column=0, sticky="w", pady=6)
        ttk.Spinbox(frame, from_=1, to=25, textvariable=self.volume_var, width=8).grid(
            row=5, column=1, sticky="w", pady=6
        )

        ttk.Button(frame, text="Save settings", command=self.save_settings).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(12, 6)
        )
        ttk.Label(
            frame,
            text="Hold the activation button with the D-pad for media controls.\n"
            "Close this window to keep the app in the system tray.",
            foreground="#555555",
            justify="left",
            wraplength=320,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 5))
        ttk.Label(frame, textvariable=self.action_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    def save_settings(self) -> None:
        try:
            volume_step = int(self.volume_var.get())
        except (tk.TclError, ValueError):
            self.action_var.set("Volume step must be a number from 1 to 25")
            return

        if not 1 <= volume_step <= 25:
            self.action_var.set("Volume step must be between 1 and 25")
            return

        self.settings.update(
            {
                "enabled": self.enabled_var.get(),
                "activation_button": self.activation_var.get(),
                "play_pause_button": self.play_pause_var.get(),
                "volume_step": volume_step,
            }
        )
        self.action_var.set("Settings saved")

    def _process_updates(self) -> None:
        try:
            while True:
                kind, text = self.updates.get_nowait()
                if kind == "connection":
                    self.status_var.set(text)
                else:
                    self.action_var.set(text)
        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(100, self._process_updates)

    def _start_tray_icon(self) -> None:
        image = Image.new("RGBA", (64, 64), "#1DB954")
        draw = ImageDraw.Draw(image)
        draw.ellipse((13, 13, 51, 51), fill="white")
        draw.rectangle((36, 18, 40, 42), fill="#1DB954")
        draw.line((39, 18, 50, 21), fill="#1DB954", width=4)
        draw.ellipse((29, 38, 39, 48), fill="#1DB954")
        self.tray_icon = pystray.Icon(
            "spotify_controller",
            image,
            APP_NAME,
            menu=pystray.Menu(
                pystray.MenuItem("Show window", self._tray_show),
                pystray.MenuItem("Quit", self._tray_quit),
            ),
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _tray_show(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.root.after(0, self.show_window)

    def _tray_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.root.after(0, self.quit)

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self) -> None:
        self.root.withdraw()

    def quit(self) -> None:
        self.worker.stop()
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SpotifyControllerApp().run()
