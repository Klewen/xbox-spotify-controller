# Spotify Controller

Control Windows media with a game controller D-pad. It is designed for Spotify,
but its media controls work with any app that responds to Windows media keys.

## Controls

| D-pad | Action |
| --- | --- |
| Left | Previous track |
| Right | Next track |
| Up | Increase Windows master volume by 5% |
| Down | Decrease Windows master volume by 5% |

## Requirements

- Windows
- Python 3.10 or newer
- A controller recognised by Windows (Xbox controllers are supported; other
  controllers may work when their D-pad is exposed normally)

## Installation

```powershell
py -m pip install -r requirements.txt
```

## Usage

Open Spotify, connect your controller, then run:

```powershell
py spotify_controller.py
```

Keep the terminal open while using the controller. Press `Ctrl+C` to stop the
program.

> The volume controls adjust the Windows master volume. Track controls are sent
> to the active Windows media session, so they control Spotify while it is
> playing.
