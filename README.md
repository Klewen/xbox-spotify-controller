# Spotify Controller

Control Windows media with a game controller D-pad. It is designed for Spotify,
but its media controls work with any app that responds to Windows media keys.
The compact desktop window lets you select the controller button combinations;
closing it keeps the app running in the Windows system tray.

## Controls

| Controller input | Action |
| --- | --- |
| Hold the activation button + D-pad Left | Previous track |
| Hold the activation button + D-pad Right | Next track |
| Hold the activation button + D-pad Up | Increase Windows master volume |
| Hold the activation button + D-pad Down | Decrease Windows master volume |
| Hold the activation button + selected button | Play / pause |

The default mapping is `LB` as the activation button and `A` for play/pause.
Both buttons and the volume step can be changed in the app.

## Requirements

- Windows
- Python 3.10 or newer
- An Xbox controller recognised by Windows (the default button mapping is for
  Xbox controllers)

## Installation

```powershell
py -m pip install -r requirements.txt
```

## Usage

Open Spotify, connect your controller, then run:

```powershell
py spotify_controller.py
```

Close the window to keep the app running in the system tray. Right-click its
tray icon and choose **Quit** when you want to stop it.

> The volume controls adjust the Windows master volume. Track controls are sent
> to the active Windows media session, so they control Spotify while it is
> playing.
