"""Control Windows media with an Xbox controller D-pad.

Left / right: previous / next track
Up / down: raise / lower Windows master volume
"""

from __future__ import annotations

import ctypes
import sys
import time

import pygame
from pycaw.pycaw import AudioUtilities


VOLUME_STEP = 0.05  # 5% per press
POLL_DELAY = 0.02

# Default Xbox controller mapping. These will become configurable in the UI.
ACTIVATION_BUTTON = 4  # Left bumper (LB)
PLAY_PAUSE_BUTTON = 0  # A

# Windows virtual-key codes
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


def send_media_key(key_code: int) -> None:
    """Send a global media key to Windows (Spotify receives it)."""
    ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP, 0)


def get_volume_endpoint():
    # Current pycaw versions provide EndpointVolume directly.
    return AudioUtilities.GetSpeakers().EndpointVolume


def change_volume(endpoint, amount: float) -> None:
    current = endpoint.GetMasterVolumeLevelScalar()
    target = max(0.0, min(1.0, current + amount))
    endpoint.SetMasterVolumeLevelScalar(target, None)
    print(f"Volume: {round(target * 100)}%")


def direction_from_joystick(joystick: pygame.joystick.Joystick) -> tuple[int, int]:
    """Read the D-pad. Xbox controllers normally report it as a hat."""
    if joystick.get_numhats():
        return joystick.get_hat(0)

    # Some drivers expose the D-pad as axes instead.
    if joystick.get_numaxes() >= 2:
        x = int(round(joystick.get_axis(0)))
        y = int(round(joystick.get_axis(1)))
        return x, -y
    return 0, 0


def is_button_pressed(joystick: pygame.joystick.Joystick, button: int) -> bool:
    """Safely return the state of a controller button."""
    return button < joystick.get_numbuttons() and bool(joystick.get_button(button))


def run() -> None:
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        sys.exit("No controller found. Connect it and run the program again.")

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    endpoint = get_volume_endpoint()
    previous_active_direction = (0, 0)
    previous_play_pause_active = False

    print(f"Connected controller: {joystick.get_name()}")
    print("Hold LB + D-pad: media controls | Hold LB + A: play/pause")
    print("Press Ctrl+C to exit")

    try:
        while True:
            pygame.event.pump()
            activation_pressed = is_button_pressed(joystick, ACTIVATION_BUTTON)
            direction = direction_from_joystick(joystick) if activation_pressed else (0, 0)

            # One action for each new D-pad press, rather than repeat on hold.
            if direction != previous_active_direction:
                x, y = direction
                if x == -1:
                    send_media_key(VK_MEDIA_PREV_TRACK)
                    print("Previous track")
                elif x == 1:
                    send_media_key(VK_MEDIA_NEXT_TRACK)
                    print("Next track")
                elif y == 1:
                    change_volume(endpoint, VOLUME_STEP)
                elif y == -1:
                    change_volume(endpoint, -VOLUME_STEP)

            play_pause_active = activation_pressed and is_button_pressed(
                joystick, PLAY_PAUSE_BUTTON
            )
            if play_pause_active and not previous_play_pause_active:
                send_media_key(VK_MEDIA_PLAY_PAUSE)
                print("Play/Pause")

            previous_active_direction = direction
            previous_play_pause_active = play_pause_active
            time.sleep(POLL_DELAY)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
