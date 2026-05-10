#!/usr/bin/python3
import json
import logging
import os
import re
import socket
import sys


_REG_255 = r"(1?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"
_REG_TEMP = r"^(2[2-9]\d{2}|[3-5]\d{3}|6[0-4]\d{2}|6500)$"
_REG_DIMMING = r"^([1-9][0-9]|100)$"

logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s\t%(message)s"
)
LOGGER = logging.getLogger("wiz")


class WizDeviceException(Exception):
    """Custom exception class for errors related to Wiz devices."""

    def __init__(self, message: str) -> None:

        self.message = message


class DeviceInfo():

    def __init__(self) -> None:
        self.device_mac: str = None
        self.module_name: str = None
        self.flash_info: list = []

    @staticmethod
    def from_json(json_data: dict[str, str | int | list]) -> 'DeviceInfo':
        """Factory method to create a DeviceInfo instance from a JSON response dictionary."""

        info = DeviceInfo()
        info.device_mac = json_data.get("devMac")
        info.module_name = json_data.get("moduleName")
        info.flash_info = json_data.get("flash", [])
        return info

    def to_dict(self) -> dict[str, str | int | list]:

        return {
            "device_mac": self.device_mac,
            "module_name": self.module_name,
            "flash_info": self.flash_info
        }

    def __str__(self):
        return f"DeviceInfo(device_mac={self.device_mac}, module_name={self.module_name}, flash_info={self.flash_info})"


class SystemConfig():

    def __init__(self) -> None:
        self.mac: str = None
        self.home_id: str = None
        self.room_id: str = None
        self.region: str = None
        self.module_name: str = None
        self.firmware_version: str = None
        self.group_id: int = 0
        self.ping: int = 0
        self.acc_udp_prop_rate: int = 0

    @staticmethod
    def from_json(json_data: dict[str, str | int]) -> 'SystemConfig':
        """Factory method to create a SystemConfig instance from a JSON response dictionary."""

        config = SystemConfig()
        config.mac = json_data.get("mac")
        config.home_id = json_data.get("homeId")
        config.room_id = json_data.get("roomId")
        config.region = json_data.get("rgn")
        config.module_name = json_data.get("moduleName")
        config.firmware_version = json_data.get("fwVersion")
        config.group_id = json_data.get("groupId", 0)
        config.ping = json_data.get("ping", 0)
        config.acc_udp_prop_rate = json_data.get("accUdpPropRate", 0)
        return config

    def to_dict(self) -> dict[str, str | int]:

        return {
            "mac": self.mac,
            "home_id": self.home_id,
            "room_id": self.room_id,
            "region": self.region,
            "module_name": self.module_name,
            "firmware_version": self.firmware_version,
            "group_id": self.group_id,
            "ping": self.ping,
            "acc_udp_prop_rate": self.acc_udp_prop_rate
        }

    def getter_method(self):

        return "getSystemConfig"

    def __str__(self):
        return f"SystemConfig(mac={self.mac}, home_id={self.home_id}, room_id={self.room_id}, region={self.region}, module_name={self.module_name}, firmware_version={self.firmware_version}, group_id={self.group_id}, ping={self.ping}, acc_udp_prop_rate={self.acc_udp_prop_rate})"


class UserConfig():

    def __init__(self) -> None:

        self.fade_in: int = 0
        self.fade_out: int = 0
        self.default_dimming: int = 0
        self.operation_mode: int = 0
        self.power_on_state: bool = False
        self.min_dimming: int = 0
        self.tap_sensor: int = 0
        self.auto_update: int = 0
        self.devices_count: int = 0
        self.dim_to_warm_points: list = []
        self.wizard_config1: dict = {}
        self.wizard_config2: dict = {}
        self.ap_stack_enabled: bool = False
        self.config_timestamp: int = 0

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool | list | dict]) -> 'UserConfig':
        """Factory method to create a UserConfig instance from a JSON response dictionary."""

        config = UserConfig()
        config.fade_in = json_data.get("fadeIn", 0)
        config.fade_out = json_data.get("fadeOut", 0)
        config.default_dimming = json_data.get("dftDim", 0)
        config.operation_mode = json_data.get("opMode", 0)
        config.power_on_state = json_data.get("po", False)
        config.min_dimming = json_data.get("minDimming", 0)
        config.tap_sensor = json_data.get("tapSensor", 0)
        config.auto_update = json_data.get("autoUpd", 0)
        config.devices_count = json_data.get("devices", 0)
        config.dim_to_warm_points = json_data.get("dim2WarmPoints", [])
        config.wizard_config1 = json_data.get("wizc1", {})
        config.wizard_config2 = json_data.get("wizc2", {})
        config.ap_stack_enabled = json_data.get("apStkEn", False)
        config.config_timestamp = json_data.get("confTs", 0)

        return config

    def to_dict(self) -> dict[str, str | int | bool | list | dict]:

        return {
            "fadeIn": self.fade_in,
            "fadeOut": self.fade_out,
            "dftDim": self.default_dimming,
            "opMode": self.operation_mode,
            "po": self.power_on_state,
            "minDimming": self.min_dimming,
            "tapSensor": self.tap_sensor,
            "autoUpd": self.auto_update,
            "devices": self.devices_count,
            "dim2WarmPoints": self.dim_to_warm_points,
            "wizc1": self.wizard_config1,
            "wizc2": self.wizard_config2,
            "apStkEn": self.ap_stack_enabled,
            "confTs": self.config_timestamp
        }

    def __str__(self):
        return f"UserConfig(fade_in={self.fade_in}, fade_out={self.fade_out}, default_dimming={self.default_dimming}, operation_mode={self.operation_mode}, power_on_state={self.power_on_state}, min_dimming={self.min_dimming}, tap_sensor={self.tap_sensor}, auto_update={self.auto_update}, devices_count={self.devices_count}, dim_to_warm_points={self.dim_to_warm_points}, wizard_config1={self.wizard_config1}, wizard_config2={self.wizard_config2}, ap_stack_enabled={self.ap_stack_enabled}, config_timestamp={self.config_timestamp})"


class Pilot():
    """Represents the pilot information of a Wiz device, including state, RSSI, dimming level, light color, and scene."""

    WHITE_WARMEST = 2200
    WHITE_WARM = 2700
    WHITE_DAYLIGHT = 4200
    WHITE_COLD = 6500

    SCENE_COLORS = 0
    SCENE_OCEAN = 1
    SCENE_ROMANCE = 2
    SCENE_SUNSET = 3
    SCENE_PARTY = 4
    SCENE_FIREPLACE = 5
    SCENE_COZY = 6
    SCENE_FOREST = 7
    SCENE_PASTEL_COLORS = 8
    SCENE_WAKE_UP = 9
    SCENE_BEDTIME = 10
    SCENE_WARM_WHITE = 11
    SCENE_DAYLIGHT = 12
    SCENE_COOL_WHITE = 13
    SCENE_NIGHT_LIGHT = 14
    SCENE_FOCUS = 15
    SCENE_RELAX = 16
    SCENE_TRUE_COLORS = 17
    SCENE_TV_TIME = 18
    SCENE_PLANT_GROWTH = 19
    SCENE_SPRING = 20
    SCENE_SUMMER = 21
    SCENE_FALL = 22
    SCENE_DEEP_DIVE = 23
    SCENE_JUNGLE = 24
    SCENE_MOJITO = 25
    SCENE_CLUB = 26
    SCENE_CHRISTMAS = 27
    SCENE_HALLOWEEN = 28
    SCENE_CANDLELIGHT = 29
    SCENE_GOLDEN_WHITE = 30
    SCENE_PULSE = 31
    SCENE_STEAMPUNK = 32
    SCENE_DIWALI = 33
    SCENE_34 = 34
    SCENE_LIGHT_ALARM = 35
    SCENE_SNOWY_SKY = 36
    SCENE_DIM_TO_WARM = 40
    SCENE_RHYTHM = 1000

    SCENES_LIST = [
        "Colors",
        "Ocean",
        "Romance",
        "Sunset",
        "Party",
        "Fireplace",
        "Cozy",
        "Forest",
        "Pastel Colors",
        "Wake-up",
        "Bedtime",
        "Warm White",
        "Daylight",
        "Cool White",
        "Night light",
        "Focus",
        "Relax",
        "True colors",
        "TV time",
        "Plant growth",
        "Spring",
        "Summer",
        "Fall",
        "Deep dive",
        "Jungle",
        "Mojito",
        "Club",
        "Christmas",
        "Halloween",
        "Candlelight",
        "Golden white",
        "Pulse",
        "Steampunk",
        "Diwali",
        "(unknown)",
        "Light alarm",
        "Snowy sky",
        "Dim to warm",
        "Rhythm"
    ]

    SCENE_HAS_DIMMING = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16,
                         17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33, 36]
    SCENE_HAS_SPEED = [1, 2, 3, 4, 5, 8, 20, 21, 22,
                       23, 24, 25, 26, 27, 28, 31, 32, 33, 36]
    SCENE_HAS_RGB = [0]
    SCENE_HAS_TEMPERATURE = [0, 11, 12, 13, 40]

    def __init__(self) -> None:

        self.state: bool = False
        self.temp: int = 0
        self.r: int = 0
        self.g: int = 0
        self.b: int = 0
        self.dimming: int = 0

        self.sceneId: int = 0
        self.speed: int = 0

        self.rssi: int = 0
        self.mac: str = None

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool], pilot: 'Pilot' = None) -> 'Pilot':
        """Factory method to create a Pilot instance from a JSON response dictionary."""

        pilot = pilot or Pilot()
        if "state" in json_data:
            pilot.state = json_data["state"]

        if "temp" in json_data:
            pilot.temp = json_data["temp"]

        if "r" in json_data:
            pilot.r = json_data["r"]

        if "g" in json_data:
            pilot.g = json_data["g"]

        if "b" in json_data:
            pilot.b = json_data["b"]

        if "dimming" in json_data:
            pilot.dimming = json_data["dimming"]

        if "sceneId" in json_data:
            pilot.sceneId = json_data["sceneId"]

        if "speed" in json_data:
            pilot.speed = json_data["speed"]

        if "rssi" in json_data:
            pilot.rssi = json_data["rssi"]

        if "mac" in json_data:
            pilot.mac = json_data["mac"]

        return pilot

    def isOff(self) -> bool:
        """Determine if the light is off based on its state and color values. A light is considered off if its state is False or if all color values (red, green, blue, and temperature) are zero."""

        return not self.state

    def color_str(self) -> str:

        if self.isOff():
            return "off"

        # If temp is set, show temperature and ignore RGB values (since they are not relevant in white mode)
        if self.temp and not (self.r or self.g or self.b):
            return f"temperature ({self.temp})"

        r = int(self.r & 0xFF)
        g = int(self.g & 0xFF)
        b = int(self.b & 0xFF)

        # Basic palette of common color names
        palette = [
            ("white", (255, 255, 255)),
            ("red", (255, 0, 0)),
            ("orange", (255, 165, 0)),
            ("yellow", (255, 255, 0)),
            ("green", (0, 255, 0)),
            ("cyan", (0, 255, 255)),
            ("blue", (0, 0, 255)),
            ("violet", (238, 130, 238)),
            ("magenta", (255, 0, 255)),
            ("pink", (255, 192, 203))
        ]

        # Find nearest palette color by squared Euclidean distance
        best_name = "unknown"
        best_dist = None
        for name, (pr, pg, pb) in palette:
            dr = r - pr
            dg = g - pg
            db = b - pb
            dist = dr * dr + dg * dg + db * db
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_name = name

        qualifier = ""
        if self.dimming < 40:
            qualifier = " (very dim)"
        elif self.dimming < 96:
            qualifier = " (dim)"

        # Return the name and hex code for clarity
        return f"{best_name.capitalize()}{qualifier} rgb({r}, {g}, {b})"

    @staticmethod
    def scene_list() -> 'list[str]':

        scenes = list()
        for i, s in enumerate(Pilot.SCENES_LIST):
            if i == 37:
                scenes.append(f"{s} ({Pilot.SCENE_DIM_TO_WARM})")
            elif i == 38:
                scenes.append(f"{s} ({Pilot.SCENE_RHYTHM})")
            else:
                scenes.append(f"{s} ({i})")

        return scenes

    def scene_str(self) -> str:
        """Get the human-readable name of a scene based on its integer identifier. Handles special cases for certain scene values and falls back to a predefined list of scene names."""

        if self.sceneId == Pilot.SCENE_RHYTHM:
            return f"Rhythm (Pilot.SCENE_RHYTHM, speed: {self.speed})"
        elif self.sceneId == Pilot.SCENE_DIM_TO_WARM:
            return f"Dim to Warm (Pilot.SCENE_DIM_TO_WARM, temp: {self.temp}, dimming: {self.dimming})"

        try:
            return f"{Pilot.SCENES_LIST[self.sceneId]} ({self.sceneId}, speed: {self.speed})"

        except IndexError:
            return "Unknown Scene"

    def to_dict(self) -> dict[str, str | int | bool]:

        return {
            "state": self.state,
            "temp": self.temp,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "dimming": self.dimming,
            "sceneId": self.sceneId,
            "speed": self.speed,
            "rssi": self.rssi,
            "mac": self.mac
        }

    def __str__(self):
        return f"Pilot(state={self.state}, temp={self.temp}, r={self.r}, g={self.g}, b={self.b}, dimming={self.dimming}, sceneId={self.sceneId}, speed={self.speed}, rssi={self.rssi}, mac={self.mac})"


class WiZListener():
    """Listener iWiZnterface for handling events related to Wiz device discovery and connection. Users can subclass this to implement custom behavior on events."""

    def onDiscoverFound(self, device: 'WizDevice') -> None:
        """Called when a new Wiz device is discovered during scanning. The device parameter is a WizDevice instance representing the discovered device."""

        pass


class WizDevice():
    """Represents a single Wiz device with its properties and state."""

    def __init__(self, ip_address: str = None) -> None:

        self.ip_address: str = ip_address

        self.device_info: DeviceInfo = None
        self.system_config: SystemConfig = None
        self.user_config: UserConfig = None
        self.pilot: Pilot = None

    def withDeviceInfo(self, device_info: DeviceInfo) -> 'WizDevice':
        self.device_info = device_info
        return self

    def withSystemConfig(self, system_config: SystemConfig) -> 'WizDevice':
        self.system_config = system_config
        return self

    def withUserConfig(self, user_config: UserConfig) -> 'WizDevice':
        self.user_config = user_config
        return self

    def withPilot(self, pilot: Pilot) -> 'WizDevice':
        self.pilot = pilot
        return self

    @staticmethod
    def formatted_mac(mac: str) -> str:
        """Format a MAC address string to a standardized format with colons. Handles both colon-separated and non-separated MAC address formats."""

        if mac and ":" in mac:
            return mac.upper()
        elif mac and len(mac) == 12:
            return ":".join(mac[i:i+2] for i in range(0, 12, 2)).upper()
        else:
            return "n/a"

    def to_dict(self) -> dict[str, str | dict]:

        return {
            "ip_address": self.ip_address,
            "device_info": self.device_info.to_dict() if self.device_info else None,
            "system_config": self.system_config.to_dict() if self.system_config else None,
            "user_config": self.user_config.to_dict() if self.user_config else None,
            "pilot": self.pilot.to_dict() if self.pilot else None
        }

    def __str__(self):
        return f"WizDevice(ip_address={self.ip_address}, device_info={self.device_info}, system_config={self.system_config}, user_config={self.user_config}, pilot={self.pilot})"


class Alias():
    """Manages aliases for Wiz devices, allowing users to associate human-readable names with device IP addresses. Aliases are loaded from a file and can be resolved to IP addresses."""

    _KNOWN_DEVICES_FILE = ".known_wizs"
    IP_PATTERN = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    MAC_PATTERN = r"([0-9a-fA-F]{2}[:]?){6}"

    def __init__(self) -> None:

        self.aliases: 'dict[str,str]' = dict()
        try:
            # Determine the user home directory differently on Windows and POSIX.
            # This allows the alias file to be loaded from %USERPROFILE% on Windows
            # or $HOME on Linux/macOS.
            filename = os.path.join(os.environ['USERPROFILE'] if os.name == "nt" else os.environ['HOME']
                                    if "HOME" in os.environ else "~", Alias._KNOWN_DEVICES_FILE)

            if os.path.isfile(filename):
                with open(filename, "r", encoding="utf-8") as ins:
                    for line in ins:
                        _m = re.match(
                            r"^(%s) +(.*)$" % Alias.IP_PATTERN, line)
                        if _m:
                            self.aliases[_m.groups()[0]] = _m.groups()[1]

        except Exception as e:
            LOGGER.error(f"Error while loading known devices file: {e}")

    def resolve(self, label: str) -> 'set[str]':
        """Resolve a label to a set of IP addresses. If the label is an IP address, it is returned as a single-item set. If the label is an alias, all associated IP addresses are returned. If no matches are found, None is returned."""

        if re.match(Alias.IP_PATTERN, label):
            if label:
                return {label}
            else:
                return None

        elif re.match(Alias.MAC_PATTERN, label):
            devices = WizDeviceController.discover_wiz_devices(
                broadcast_address="255.255.255.255")
            ip_addresses = {
                d.ip_address for d in devices if d.mac and d.formatted_mac() == label.upper()}
            return ip_addresses if ip_addresses else None

        else:
            ip_addresses = {alias
                            for alias in self.aliases if label in self.aliases[alias]}
            if ip_addresses:
                LOGGER.debug(
                    f"Found IP addresses for aliases: {', '.join(ip_addresses)}")
            else:
                LOGGER.debug("No aliases found")

            return ip_addresses if ip_addresses else None

    def __str__(self) -> str:
        """String representation of the Alias instance, showing all known aliases and their associated IP addresses."""

        return "\n".join([f"{a}\t{self.aliases[a]}" for a in self.aliases])


class WizDeviceController():
    """Controller class for managing multiple Wiz devices, handling discovery, connection, and command execution."""

    def __init__(self, addresses: 'list[str]', listener: WiZListener = None) -> None:

        self.addresses: 'list[str]' = addresses
        self.devices: 'list[WizDevice]' = [
            WizDevice(ip_address=a) for a in addresses]

        self._listener = listener

        self.commands: dict[str, dict] = None
        self.resetCommands()

    def resetCommands(self):

        self.commands: dict[str, dict] = {
            "getDevInfo": None,
            "getSystemConfig": None,
            "getUserConfig": None,
            "getPilot": None,
            "setPilot": None
        }

    @staticmethod
    def discover_wiz_devices(broadcast_address="255.255.255.255", timeout=1, listener: WiZListener = None) -> 'list[WizDevice]':
        """Discover Wiz devices on the local network by sending a UDP broadcast message and listening for responses. Returns a list of discovered WizDevice instances."""

        UDP_PORT = 38899
        discovery_message = {"method": "getSystemConfig", "params": {}}

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', UDP_PORT))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        devices = []

        try:
            LOGGER.debug(
                f"Sending discovery message to {broadcast_address}:{UDP_PORT}")
            sock.sendto(json.dumps(discovery_message).encode(
                'utf-8'), (broadcast_address, UDP_PORT))

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = json.loads(data.decode('utf-8'))

                    if "result" in response:
                        device = WizDevice(ip_address=addr[0]).withSystemConfig(
                            SystemConfig.from_json(response["result"]))
                        devices.append(device)
                        if listener:
                            listener.onDiscoverFound(device)
                        LOGGER.debug(f"Device found: {device}")
                except socket.timeout:
                    break

        except Exception as e:
            LOGGER.error(f"Error during discovery: {e}")
        finally:
            sock.close()

        return devices

    def getDevInfo(self) -> None:

        self.commands["getDevInfo"] = {}

    def getSystemConfig(self) -> None:

        self.commands["getSystemConfig"] = {}

    def getUserConfig(self) -> None:

        self.commands["getUserConfig"] = {}

    def getPilot(self) -> None:

        self.commands["getPilot"] = {}

    def setPilot(self, properties: dict[str, str | int]) -> None:

        if self.commands["setPilot"] is None:
            self.commands["setPilot"] = {}

        for p in properties:
            self.commands["setPilot"][p] = properties[p]

    def withState(self, state: bool) -> None:

        self.setPilot(properties={"state": state})

    def withTemp(self, temp: int) -> None:

        self.setPilot(properties={"temp": temp})

    def withDimming(self, dimming: int) -> None:

        self.setPilot(properties={"dimming": dimming})

    def withColor(self, red: int, green: int, blue: int) -> None:

        self.setPilot(properties={"r": red, "g": green, "b": blue})

    def withScene(self, scene: str) -> None:

        if scene.isdigit():
            sceneId = int(scene)
        else:
            normalized_scene = scene.strip().lower().replace("-", " ")
            scene_map = {
                s.lower(): i
                for i, s in enumerate(Pilot.SCENES_LIST)
            }
            if normalized_scene in scene_map:
                sceneId = scene_map[normalized_scene]
            elif normalized_scene == "dim to warm":
                sceneId = Pilot.SCENE_DIM_TO_WARM
            elif normalized_scene == "rhythm":
                sceneId = Pilot.SCENE_RHYTHM
            else:
                raise WizDeviceException(f"Unknown scene '{scene}'")

        self.setPilot(properties={"sceneId": sceneId})

    def withSpeed(self, speed: int) -> None:

        self.setPilot(properties={"speed": speed})

    def perform(self) -> None:

        UDP_PORT = 38899
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(.5)

        def _request(ip_address: str, payload: dict[str, str | int | dict[str, str | int]]):

            LOGGER.debug(
                f">>> Sending message {payload} to {ip_address}:{UDP_PORT}")

            try:
                sock.sendto(json.dumps(payload).encode(
                    "utf-8"), (ip_address, UDP_PORT))
                data, addr = sock.recvfrom(1024)
                response = json.loads(data.decode("utf-8"))
                LOGGER.debug(
                    f"<<< Received response from {addr[0]}: {response}")

            except socket.timeout:
                response = {
                    "error": "Timeout while waiting for response from device."}

            except Exception as e:
                LOGGER.error(f"Error during communication: {e}")
                response = {"error": f"Error during communication: {e}"}

            return response

        try:
            for device in self.devices:
                for command in self.commands:

                    params = self.commands[command]
                    if params is not None:

                        payload = {
                            "method": command,
                            "params": params
                        }

                        response = _request(
                            ip_address=device.ip_address, payload=payload)
                        if response and "result" in response:

                            if command == "getDevInfo":
                                device = device.withDeviceInfo(DeviceInfo.from_json(response["result"]))
                            elif command == "getSystemConfig":
                                device = device.withSystemConfig(SystemConfig.from_json(response["result"]))
                            elif command == "getUserConfig":
                                device = device.withUserConfig(UserConfig.from_json(response["result"]))
                            elif command == "getPilot":
                                device = device.withPilot(Pilot.from_json(response["result"]))
                            elif response["result"]["success"] == True:
                                device = device.withPilot(Pilot.from_json(params, pilot=device.pilot))
        finally:
            sock.close()
            self.resetCommands()


class WizDeviceCLI():
    """Command-line interface for interacting with Wiz devices. Parses command-line arguments, executes commands, and provides help information."""

    _USAGE = "usage"
    _DESCR = "descr"
    _REGEX = "regex"
    _TYPES = "types"

    _COMMAND = "command"
    _ARGS = "args"
    _PARAMS = "params"

    COMMANDS: dict[str, dict[str, str | None]] = {
        "aliases": {
            _USAGE: "--aliases",
            _DESCR: "print known aliases from .known_wizs file",
            _REGEX: None,
            _TYPES: None
        },
        "scan": {
            _USAGE: "--scan",
            _DESCR: "scan for Wiz devices",
            _REGEX: None,
            _TYPES: None
        },
        "status": {
            _USAGE: "--status",
            _DESCR: "just read and print the basic information of wiz device",
            _REGEX: None,
            _TYPES: None
        },
        "on": {
            _USAGE: "--on",
            _DESCR: "turn device on",
            _REGEX: None,
            _TYPES: None
        },
        "off": {
            _USAGE: "--off",
            _DESCR: "turn device off",
            _REGEX: None,
            _TYPES: None
        },
        "toggle": {
            _USAGE: "--toggle",
            _DESCR: "turn off / on",
            _REGEX: None,
            _TYPES: None
        },
        "temp": {
            _USAGE: "--temp <temp>",
            _DESCR: "set temperature for white\n- <temp> value 2200 - 6500",
            _REGEX: r"^%s$" % (_REG_TEMP),
            _TYPES: [int]
        },
        "dimming": {
            _USAGE: "--dimming <dimming>",
            _DESCR: "set dimming for light\n- <dimming> value 10 - 100",
            _REGEX: r"^%s$" % (_REG_DIMMING),
            _TYPES: [int]
        },
        "color": {
            _USAGE: "--color <red> <green> <blue>",
            _DESCR: "set color, each value 0 - 255",
            _REGEX: r"^%s %s %s$" % (_REG_255, _REG_255, _REG_255),
            _TYPES: [int, int, int]
        },
        "scene": {
            _USAGE: "--scene <id/name>",
            _DESCR: "set scene by name or id\n- %s" % "\n- ".join(Pilot.scene_list()),
            _REGEX: r"^(%s|%s|%s|%s)$" % (str(Pilot.SCENE_DIM_TO_WARM), str(Pilot.SCENE_RHYTHM), "|".join([str(i) for i in range(len(Pilot.SCENES_LIST) - 2)]), "|".join(Pilot.SCENES_LIST)),
            _TYPES: [str]
        },
        "speed": {
            _USAGE: "--speed <speed>",
            _DESCR: "set speed for scene, speed 10 - 200",
            _REGEX: r"^([1-9][0-9]|1[0-9][0-9]|200)$",
            _TYPES: [int]
        },
        "help": {
            _USAGE: "--help [<command>]",
            _DESCR: "prints help optionally for given command",
            _REGEX: r"^([a-z-]+)?$",
            _TYPES: None
        },
        "dump": {
            _USAGE: "--dump",
            _DESCR: "request full state of bulb",
            _REGEX: None,
            _TYPES: None
        },
        "print": {
            _USAGE: "--print",
            _DESCR: "prints collected data of bulb",
            _REGEX: None,
            _TYPES: None
        },
        "json": {
            _USAGE: "--json",
            _DESCR: "prints information in json format",
            _REGEX: None,
            _TYPES: None
        },
        "log": {
            _USAGE: "--log <DEBUG|INFO|WARNING|ERROR>",
            _DESCR: "set loglevel",
            _REGEX: r"^(DEBUG|INFO|WARNING|ERROR)$",
            _TYPES: [str]
        }
    }

    def __init__(self, argv: 'list[str]') -> None:

        self.alias: Alias = Alias()
        try:

            # Remove the script name from argv so only user provided arguments remain.
            argv.pop(0)
            if "--log" in sys.argv:
                # Parse a runtime log level option from the command line.
                _idx_log = sys.argv.index("--log")
                numeric_level = logging.getLevelName(
                    sys.argv[_idx_log + 1].upper())
                if isinstance(numeric_level, int):
                    LOGGER.setLevel(numeric_level)
                argv.pop(_idx_log)
                argv.pop(_idx_log)

            if argv and (argv[0] == "--help" or argv[0] == "-h"):
                if len(argv) == 2:
                    print(self._build_help(
                        command=argv[1], header=True), file=sys.stderr)
                else:
                    self.print_help()

            elif argv and argv[0] == "--scan":
                self.scan()

            elif argv and argv[0] == "--aliases":
                print(str(self.alias))

            else:
                addresses, commands = self.parse_args(sys.argv)
                if addresses and commands:
                    self.process(addresses=addresses, commands=commands)
                elif not addresses:
                    raise WizDeviceException(
                        message="Mac address or alias unknown")

        except WizDeviceException as e:
            LOGGER.error(e.message)

        except TimeoutError:
            LOGGER.error(
                f"TimeoutError! Maybe too many connections simultaneously?")

        except KeyboardInterrupt:
            pass

    def _build_help(self, command: str | None = None, header: bool = False, msg: str = "") -> None:

        s = ""

        if header == True:
            s = """Mipow Bulb bluetooth command line interface for Linux / Raspberry Pi / Windows

USAGE:   wiz.py <ip_1/alias_1> [<ip_2/alias_2>] ... --<command_1> [<param_1> <param_2> ... --<command_2> ...]
         <ip_N>    : IP address of device
         <alias_N> : you can use aliases instead of IP addresses if there is a ~/.known_wizs file
         <command> : a list of commands and parameters
         """

        if msg != "":
            s += "\n " + msg

        if command is not None and command in WizDeviceCLI.COMMANDS:
            s += "\n " + \
                WizDeviceCLI.COMMANDS[command][WizDeviceCLI._USAGE].ljust(32)
            for i, d in enumerate(WizDeviceCLI.COMMANDS[command][WizDeviceCLI._DESCR].split("\n")):
                s += ("\n " + (" " * 32) + d if i > 0 or len(WizDeviceCLI.COMMANDS[command]
                                                             [WizDeviceCLI._USAGE]) >= 32 else d)

        if msg != "":
            s += "\n"

        return s

    def scan(self) -> None:

        class ScanListener(WiZListener):

            def __init__(self, alias: Alias) -> None:
                self.alias: Alias = alias
                self._seen: 'set[WizDevice]' = set()

            def onDiscoverFound(self, device: WizDevice) -> None:
                alias = self.alias.aliases[device.ip_address] if self.alias and device.ip_address in self.alias.aliases else ""
                print(
                    f"{WizDevice.formatted_mac(device.system_config.mac)}\t{device.ip_address}\t{alias}", flush=True)

        print("MAC\t\tIP Address\tAlias", flush=True)
        WizDeviceController.discover_wiz_devices(
            broadcast_address="255.255.255.255", listener=ScanListener(self.alias))

    def print_help(self):

        help = self._build_help(header=True)

        help += "\n\nBasic commands:"
        help += self._build_help(command="status")
        help += self._build_help(command="on")
        help += self._build_help(command="off")

        help += "\n\nSet light:"
        help += self._build_help(command="temp")
        help += self._build_help(command="dimming")
        help += self._build_help(command="color")

        help += "\n\nSet scene:"
        help += self._build_help(command="scene")
        help += self._build_help(command="speed")

        help += "\n\nOther commands:"
        help += self._build_help(command="dump")
        help += self._build_help(command="print")
        help += self._build_help(command="json")
        help += self._build_help(command="log")
        help += self._build_help(command="help")

        help += "\n\nSetup commands:"
        help += self._build_help(command="scan")
        help += self._build_help(command="aliases")

        help += "\n"
        print(help, file=sys.stderr)

    def print(self, devices: 'list[WizDevice]', json_: bool = False) -> None:

        if json_:
            print(json.dumps([b.to_dict() for b in devices], indent=2))
        else:
            for device in devices:
                self.printDevice(device)

    def printDevice(self, device: WizDevice) -> None:

        print(f"Device {device.ip_address} ({WizDevice.formatted_mac(device.device_info.device_mac) if device.device_info and device.device_info.device_mac else 'Unknown'}):")

        alias = self.alias.aliases[device.ip_address] if self.alias and device.ip_address in self.alias.aliases else ""
        if alias:
            print(f"\n  Alias:                 {alias}")

        if device.pilot:
            print(f"\n  Light State:")
            print(
                f"    State:               {'OFF' if device.pilot.isOff() else 'ON'}")
            print(f"    Dimming:             {device.pilot.dimming}%")

            if device.pilot.temp:
                print(
                    f"    Temperature:         {device.pilot.temp} K")

            elif device.pilot.r:
                print(
                    f"    Color:               {device.pilot.color_str()}")

            if device.pilot.sceneId:
                print(
                    f"    Scene:               {device.pilot.scene_str()}")

            print(f"    RSSI:                {device.pilot.rssi} dBm")

        if device.user_config:
            print(f"\n  User Configuration:")
            print(
                f"    Power On State:      {'ON' if device.user_config.power_on_state else 'OFF'}")
            print(f"    Fade In:             {device.user_config.fade_in} ms")
            print(f"    Fade Out:            {device.user_config.fade_out} ms")
            print(
                f"    Default Dimming:     {device.user_config.default_dimming}%")
            print(
                f"    Minimum Dimming:     {device.user_config.min_dimming}%")
            print(
                f"    Dim to Warm Points:  {device.user_config.dim_to_warm_points}")
            print(
                f"    Operation Mode:      {device.user_config.operation_mode}")
            print(f"    Tap Sensor:          {device.user_config.tap_sensor}")
            print(f"    Auto Update:         {device.user_config.auto_update}")
            print(
                f"    Devices Count:       {device.user_config.devices_count}")
            print(
                f"    Wizard Config 1:     {device.user_config.wizard_config1}")
            print(
                f"    Wizard Config 2:     {device.user_config.wizard_config2}")
            print(
                f"    AP Stack Enabled:    {'Yes' if device.user_config.ap_stack_enabled else 'No'}")
            print(
                f"    Config Timestamp:    {device.user_config.config_timestamp}")

        if device.system_config:
            print(f"\n  System Configuration:")
            print(f"    Home ID:             {device.system_config.home_id}")
            print(f"    Room ID:             {device.system_config.room_id}")
            print(f"    Region:              {device.system_config.region}")
            print(f"    Group ID:            {device.system_config.group_id}")
            print(
                f"    Firmware Version:    {device.system_config.firmware_version}")
            print(f"    Ping:                {device.system_config.ping} ms")
            print(
                f"    Acc UDP Prop Rate:   {device.system_config.acc_udp_prop_rate} ms")

        if device.device_info:

            print(f"\n  Device Configuration:")
            print(f"    Module Name:         {device.device_info.module_name}")
            print(f"    Flash Info:          {device.device_info.flash_info}")

        print()

    def process(self, addresses: 'list[str]', commands: 'list[dict]') -> None:

        try:
            controller = WizDeviceController(
                addresses=addresses, listener=WiZListener())

            _commands: 'list[str]' = list()

            for command in commands:

                _commands.append(command[WizDeviceCLI._COMMAND])

                if command[WizDeviceCLI._COMMAND] == "status":

                    controller.getPilot()

                elif command[WizDeviceCLI._COMMAND] == "on":

                    controller.withState(state=True)

                elif command[WizDeviceCLI._COMMAND] == "off":

                    controller.withState(state=False)

                elif command[WizDeviceCLI._COMMAND] == "temp":

                    controller.withTemp(
                        temp=int(command[WizDeviceCLI._PARAMS][0]))

                elif command[WizDeviceCLI._COMMAND] == "dimming":

                    controller.withDimming(dimming=int(
                        command[WizDeviceCLI._PARAMS][0]))

                elif command[WizDeviceCLI._COMMAND] == "color" and command[WizDeviceCLI._PARAMS]:

                    controller.withColor(
                        red=command[WizDeviceCLI._PARAMS][0], green=command[WizDeviceCLI._PARAMS][1], blue=command[WizDeviceCLI._PARAMS][2])

                elif command[WizDeviceCLI._COMMAND] == "scene" and command[WizDeviceCLI._PARAMS]:

                    controller.withScene(
                        scene=command[WizDeviceCLI._PARAMS][0])

                elif command[WizDeviceCLI._COMMAND] == "speed" and command[WizDeviceCLI._PARAMS]:

                    controller.withSpeed(
                        speed=command[WizDeviceCLI._PARAMS][0])

                elif command[WizDeviceCLI._COMMAND] == "dump":

                    controller.getDevInfo()
                    controller.getSystemConfig()
                    controller.getUserConfig()
                    controller.getPilot()

            controller.perform()

            if "print" in _commands or "status" in _commands or "json" in _commands:

                self.print(devices=controller.devices,
                           json_=("json" in _commands))

        except WizDeviceException as ex:
            LOGGER.error(ex.message)

        finally:
            pass

    def transform_commands(self, commands: 'list[dict]'):
        """Validate CLI commands and convert argument strings to typed parameters."""

        errors: 'list[str]' = list()

        for command in commands:

            cmd = command[WizDeviceCLI._COMMAND]
            if cmd not in WizDeviceCLI.COMMANDS:
                errors.append("ERROR: Unknown command <%s>" % cmd)
                continue

            cmd_def = WizDeviceCLI.COMMANDS[cmd]

            regex: str = cmd_def[WizDeviceCLI._REGEX]
            if regex and not re.match(regex, " ".join(command[WizDeviceCLI._ARGS]), re.IGNORECASE):
                errors.append(
                    self._build_help(cmd, False,
                                     "ERROR: Please check parameters of command\n")
                )
                continue

            if cmd_def[WizDeviceCLI._TYPES]:
                params = []
                for i, arg in enumerate(command[WizDeviceCLI._ARGS]):
                    try:
                        params.append(cmd_def[WizDeviceCLI._TYPES][i](arg))
                    except Exception as ex:
                        LOGGER.error(f"Error parsing args: {ex}")
                        exit(1)

                command["params"] = params

        if len(commands) == 0:
            errors.append(
                "No commands given. Use --help in order to get help")

        if len(errors) > 0:
            raise WizDeviceException("\n".join(errors))

        return commands

    def parse_args(self, argv: 'list[str]') -> 'tuple[set[str], list[dict[str, list[str]]]]':
        """Parse CLI arguments into device addresses and command definitions."""

        addresses: 'set[str]' = set()
        commands: 'list[tuple[str, list[str]]]' = list()

        cmd_group = False
        for arg in argv:

            is_cmd = arg.startswith("--")
            cmd_group |= is_cmd
            if not cmd_group:
                _addresses = self.alias.resolve(arg)
                if _addresses:
                    for a in _addresses:
                        addresses.add(a)
                else:
                    addresses.add(arg)

            elif is_cmd:
                commands.append({
                    "command": arg[2:],
                    "args": list()
                })

            else:
                commands[-1]["args"].append(arg)

        self.transform_commands(commands)

        return addresses, commands


if __name__ == '__main__':
    WizDeviceCLI(argv=sys.argv)
