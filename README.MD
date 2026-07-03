# wiz-tools

A Python CLI tool for controlling and querying Wiz lighting devices over the local network.

## Features

- Scan the local network for Wiz devices
- Read device state, power usage, and full device configuration
- Turn devices on/off
- Set color temperature, dimming, RGB color, and scenes
- Adjust scene speed
- run light programs
- Print raw device data or structured JSON output
- Support alias-based device identification via `~/.known_wizs`
- Target devices by home, room, or group when sending broadcast-style commands

## Requirements

- Python 3.11 or newer
- Network access to Wiz devices

## Installation

No installation is required. Run the script directly:

```bash
python3 wiz.py --help
```

## Usage

```bash
./wiz.py <ip_1/alias_1> [<ip_2/alias_2>] ... --<command> [<param> ...]
```

## Multiple devices

Multiple devices can be controlled in a single request by listing more than one IP address or alias before the command list.

```bash
./wiz.py 192.168.178.33 192.168.178.34 --on --dimming 80
```

When running a program across several devices, you can add a phase shift to create a time delay between them. The value is interpreted as the number of seconds between successive devices.

```bash
./wiz.py 192.168.178.33 192.168.178.34 192.168.178.35 --program infinite 10 80 30
```

In that example, the second device starts 30 seconds ahead and so on.

## Combining commands

Multiple commands can be combined in a single call. The tool will execute them in the order provided.

```bash
./wiz.py 192.168.178.33 --on --temp 3000 --dimming 80 --scene Romance
```

## Multiple devices

Multiple devices can be controlled at once by listing more than one IP address or alias before the command list.

```bash
./wiz.py 192.168.178.33 192.168.178.34 --on --dimming 80
```

## Example commands

- Query device status:
  ```bash
  ./wiz.py 192.168.178.33 --status
  ```

- Turn the device on/off:
  ```bash
  ./wiz.py 192.168.178.33 --on
  ./wiz.py 192.168.178.33 --off
  ```

- Set color temperature:
  ```bash
  ./wiz.py 192.168.178.33 --temp 3000
  ```

- Set dimming level:
  ```bash
  ./wiz.py 192.168.178.33 --dimming 80
  ```

- Set RGB color:
  ```bash
  ./wiz.py 192.168.178.33 --color 255 100 50
  ```

- Set a scene:
  ```bash
  ./wiz.py 192.168.178.33 --scene Romance
  ```

- Set scene speed:
  ```bash
  ./wiz.py 192.168.178.33 --speed 100
  ```

- Run a program:
  ```bash
  ./wiz.py 192.168.178.33 --program doze 2
  ./wiz.py 192.168.178.33 --program sunrise 10 80
  ```

  Program durations can be specified as minutes or as `HH:MM` (up to `24:00`). The optional third argument sets a dimming override.

- Print full device state:
  ```bash
  ./wiz.py 192.168.178.33 --dump --print
  ```

- Print JSON output:
  ```bash
  ./wiz.py 192.168.178.33 --json
  ```

- Scan the network for Wiz devices:
  ```bash
  ./wiz.py --scan
  ```

- Print known aliases:
  ```bash
  ./wiz.py --aliases
  ```

## Alias file example

The CLI supports an alias file stored at `~/.known_wizs`. Each line should contain the device IP address followed by a label, separated by whitespace.

Example `~/.known_wizs`:

```text
192.168.178.33 living-room
192.168.178.34 kitchen
192.168.178.35 bedroom
```

Then you can use aliases instead of IP addresses:

```bash
./wiz.py living-room --status
```

If an alias string matches part of a saved alias label, all matching devices are controlled automatically.

```bash
./wiz.py room --off
```

This would match both `living-room` and `bedroom` if those aliases exist in `~/.known_wizs`.

## Notes

- Use `--log DEBUG` to enable detailed debug output.
- Alias support uses a local file at `~/.known_wizs`.
- programs include `interval`, `fade`, `wakeup`, `doze`, `ambient`, `rgb`, `gbr`, `brg`, `bgr`, `rbg`, `grb`, `random`, `infinite`, `warm-to-cold`, `cold-to-warm`, `sunrise`, `sunset`, and `sunrise-sunset`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for the full text.
