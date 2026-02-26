# pyvisca-gui

A graphical user interface for controlling serial VISCA PTZ cameras, built with Dear PyGui.

## Description

pyvisca-gui provides a modern, cross-platform GUI for controlling serial VISCA-compatible PTZ cameras. It supports both direct serial ports and ethernet-serial gateway devices.

## Installation

```bash
# Install the package (recommended)
uv pip install -e .

# Or with regular pip
pip install -e .

# Or install requirements directly
uv pip install -r requirements.txt
```

## Usage

```bash
# Run with default connection (192.168.1.32:8234)
pyvisca-gui

# Specify connection string
pyvisca-gui 192.168.1.100:2217
pyvisca-gui /dev/ttyUSB0
```

### Development Mode

```bash
# Run directly without installing
python -m pyvisca_gui.main [connection]
```

## Features

- **Pan/Tilt Control**: Directional movement with adjustable speeds (0-24)
- **Zoom Control**: Zoom in/out with adjustable speed (0-7)
- **Focus Control**: Near/far focus with adjustable speed (0-7)
- **Status Monitoring**: Real-time camera status display
- **Activity Logging**: Timestamped command log
- **Auto-Reconnect**: Automatic reconnection on connection loss

## Connection Formats

- **RFC-2217** or **Raw TCP**: `192.168.1.100:2217`
- **Serial port**: `/dev/ttyUSB0` (Linux) or `COM1` (Windows)

## Controls

### Mouse
- Click buttons for all camera controls
- Adjust speeds using `<`/`>` buttons in Settings window

### Keyboard
- **Arrow keys**: Pan/tilt movement
- **Space**: Stop all movement
- **`+`/`-`**: Zoom in/out
- **`[`/`]`**: Focus near/far
- **`,`/`.`**: Adjust pan speed
- **`<`/`>`**: Adjust tilt speed
- **`a`/`d`**: Adjust zoom speed
- **`s`/`f`**: Adjust focus speed
- **`h`**: Home position
- **`p`**: Toggle power
- **`r`**: Reset camera
- **`c`**: Clear buffer
- **`f`**: Autofocus
- **`b`**: Cycle white balance (Auto/Indoor/Outdoor)
- **`0`-`9`**: Recall presets
- **Ctrl+q**: Exit

## Configuration

Settings are automatically saved to `~/.config/pyvisca-gui/config.json`, including:
- Last connection string
- Speed settings (pan, tilt, zoom, focus)
- Auto-connect preference

## Requirements

- Python 3.10+
- Dear PyGui 2.2+
- pyvisca (from workspace)

## License

GPL-3.0
