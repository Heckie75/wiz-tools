# wiz-tool

A simple Python CLI tool for controlling and querying Wiz lighting devices over the local network.

## Features

- Scan the local network for Wiz devices
- Read the current state of devices
- Turn devices on/off
- Set color temperature, dimming, and RGB color
- Activate predefined scenes and adjust scene speed
- Print raw device data and JSON output
- Support alias-based device identification via `~/.known_wizs`

## Requirements

- Python 3.11 or newer
- Network access to Wiz devices

## Installation

No installation required. Run the `wiz.py` script directly.

```bash
python wiz.py --help
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

## Combining commands

Multiple commands can be combined in a single call. The tool will execute them in the order provided.

```bash
./wiz.py 192.168.178.33 --on --temp 3000 --dimming 80 --scene Romance
```

### Example commands

- Query device status:
  ```bash
  ./wiz.py 192.168.178.33 --status
  ```

- Turn the device on:
  ```bash
  ./wiz.py 192.168.178.33 --on
  ```

- Turn the device off:
  ```bash
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

## License

No license information is included in this project.
