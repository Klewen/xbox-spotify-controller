# Spotify Controller

Control Windows media with a game controller D-pad. It is designed for Spotify,
but its media controls work with any app that responds to Windows media keys.

## Controls

| Controller input | Action |
| --- | --- |
| Hold `LB` + D-pad Left | Previous track |
| Hold `LB` + D-pad Right | Next track |
| Hold `LB` + D-pad Up | Increase Windows master volume by 5% |
| Hold `LB` + D-pad Down | Decrease Windows master volume by 5% |
| Hold `LB` + `A` | Play / pause |

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

Keep the terminal open while using the controller. Press `Ctrl+C` to stop the
program.

> The volume controls adjust the Windows master volume. Track controls are sent
> to the active Windows media session, so they control Spotify while it is
> playing.
