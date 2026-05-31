#!/usr/bin/python3
import hashlib
import json
import logging
import os
import random
import re
import platform
import signal
import socket
import subprocess
import sys
import time
import uuid


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


class Features():

    DEVICE_SOCKET = "SOCKET"
    DEVICE_BULB = "BULB"
    DEVICE_STRIP = "STRIP"
    DEVICE_MOTION_SENSOR = "MOTION_SENSOR"

    FEATURES = {
        "SHRGBW": "Color Light (RGB + Dedicated White LED, fixed color temperature)",
        "SHRGBC": "Full Color Light (RGB + Cold & Warm White)",
        "SHRGB":  "Color Light (RGB)",
        "SHDW":   "Tunable White (Cold & Warm White)",
        "SHDIM":  "Dimmable (Fixed Color Temperature)",
        "SOCKET": "Smart Outlet (Switching only, no power monitoring)",
        "SHPL":   "Smart Plug (Switching)",
        "POW":    "Power Monitoring Outlet (Energy tracking enabled)",
        "STRIP":  "LED Strip Controller",
        "PIR":    "Motion Sensor (Passive Infrared)"
    }

    def __init__(self):

        self.module_name: str = ""
        self.device_type: str = ""
        self.type_key: str = ""

        self.color: bool = False
        self.white: bool = False
        self.temp: bool = False
        self.dimming: bool = False
        self.power_meter: bool = False

    def getFeaturesDescription(self) -> str:

        module_name_upper = self.module_name.upper()
        for feature in Features.FEATURES:
            if f"_{feature}_" in module_name_upper:
                return f"{Features.FEATURES[feature]} ({feature})"

        return "unknown"

    @staticmethod
    def fromModuleName(module_name: str) -> 'Features':

        module_name_upper = module_name.upper()
        parts = module_name_upper.split('_')

        features: Features = Features()
        features.module_name = module_name

        if len(parts) < 2:
            raise WizDeviceException("invalid format")

        features.type_key = parts[1]

        # SHRGBC = Color + Tunable White (Full control)
        if "RGBC" in features.type_key:
            features.device_type = Features.DEVICE_BULB
            features.color = True
            features.white = True
            features.temp = True
            features.dimming = True

        # SHRGBW = Color + Fixed White (No color temperature control)
        elif "RGBW" in features.type_key:
            features.device_type = Features.DEVICE_BULB
            features.color = True
            features.white = False
            features.temp = True
            features.dimming = True

        # SHRGB = Color
        elif "RGB" in features.type_key:
            features.device_type = Features.DEVICE_BULB
            features.color = True
            features.white = False
            features.temp = False
            features.dimming = True

        # SHDW / SHTW = Only Tunable White
        elif any(x in features.type_key for x in ["DW", "TW"]):
            features.device_type = Features.DEVICE_BULB
            features.temp = True
            features.dimming = True

        # SHDIM = Just dimming, fixed temp
        elif "DIM" in features.type_key:
            features.device_type = Features.DEVICE_BULB
            features.dimming = True

        # SOCKETS / PLUGS
        elif Features.DEVICE_SOCKET in features.type_key or "PL" in features.type_key:
            features.device_type = Features.DEVICE_SOCKET
            if "POW" in features.type_key or "PL" in features.type_key:
                features.power_meter = True

        if Features.DEVICE_STRIP in module_name_upper:
            features.device_type = Features.DEVICE_STRIP

        return features

    def to_json(self) -> dict[str, bool | str]:

        return {
            "module_name": self.module_name,
            "device_type": self.device_type,
            "color": self.color,
            "temp": self.temp,
            "dimming": self.dimming,
            "power_meter": self.power_meter,
            "description": self.getFeaturesDescription()
        }

    def __str__(self) -> str:
        return f"Features(module_name={self.module_name}, device_type={self.device_type}, color={self.color}, white={self.white}, temp={self.temp}, dimming={self.dimming}, power_meter={self.power_meter})"


class DeviceInfo():

    def __init__(self) -> None:
        self.device_mac: str = None
        self.module_name: str = None
        self.flash_info: list = []
        self.features: Features = None

    @staticmethod
    def from_json(json_data: dict[str, str | int | list]) -> 'DeviceInfo':
        """Factory method to create a DeviceInfo instance from a JSON response dictionary."""

        info = DeviceInfo()
        info.device_mac = json_data.get("devMac")
        info.module_name = json_data.get("moduleName")
        info.flash_info = json_data.get("flash", [])
        info.features = Features.fromModuleName(info.module_name)
        return info

    def to_dict(self) -> dict[str, str | int | list]:

        return {
            "device_mac": self.device_mac,
            "module_name": self.module_name,
            "flash_info": self.flash_info,
            "features": self.features.to_json()
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

    def __str__(self):
        return f"SystemConfig(mac={self.mac}, home_id={self.home_id}, room_id={self.room_id}, region={self.region}, module_name={self.module_name}, firmware_version={self.firmware_version}, group_id={self.group_id}, ping={self.ping}, acc_udp_prop_rate={self.acc_udp_prop_rate})"


class WizConfig():

    def __init__(self) -> None:
        self.mode: list[int] = []
        self.opts: dict[str, str | int | bool] = {}

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool | list | dict]) -> 'WizConfig':
        config = WizConfig()
        config.mode = json_data.get("mode", [])
        config.opts = json_data.get("opts", {})
        return config

    def to_dict(self) -> dict[str, str | int | bool | list | dict]:
        return {
            "mode": self.mode,
            "opts": self.opts
        }

    def __str__(self):
        return f"WizConfig(mode={self.mode}, opts={self.opts})"


class I2CDriver():

    def __init__(self) -> None:
        self.chip: str = ""
        self.addr: int = 0
        self.freq: int = 0
        self.curr: list[int] = []
        self.output: list[int] = []

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool | list | dict]) -> 'I2CDriver':
        driver = I2CDriver()
        driver.chip = json_data.get("chip", "")
        driver.addr = json_data.get("addr", 0)
        driver.freq = json_data.get("freq", 0)
        driver.curr = json_data.get("curr", [])
        driver.output = json_data.get("output", [])
        return driver

    def to_dict(self) -> dict[str, str | int | bool | list | dict]:
        return {
            "chip": self.chip,
            "addr": self.addr,
            "freq": self.freq,
            "curr": self.curr,
            "output": self.output
        }

    def __str__(self):
        return f"I2CDriver(chip={self.chip}, addr={self.addr}, freq={self.freq}, curr={self.curr}, output={self.output})"


class ModelConfig():

    def __init__(self) -> None:

        self.dev_total: int = 0
        self.head_total: int = 0
        self.sw_head: int = 0
        self.ps: int = 0
        self.has_gradient: int = 0
        self.night_light_off: int = 0
        self.min_dim_level: int = 0
        self.devices: int = 0
        self.dev_type: int = 0
        self.light_type: int = 0
        self.pwm_freq: int = 0
        self.pwm_res: int = 0
        self.pwm_range: list[int] = []
        self.pwm_ranges: list[int] = []
        self.wcr: int = 0
        self.nowc: int = 0
        self.cct_range: list[int] = []
        self.render_factor: list[int] = []
        self.wizc1: WizConfig | None = None
        self.wizc2: WizConfig | None = None
        self.drv_iface: int = 0
        self.i2c_drv: list[I2CDriver] = []

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool | list | dict]) -> 'ModelConfig':

        config = ModelConfig()
        config.dev_total = json_data.get("devTotal", 0)
        config.head_total = json_data.get("headTotal", 0)
        config.sw_head = json_data.get("swHead", 0)
        config.ps = json_data.get("ps", 0)
        config.has_gradient = json_data.get("hasGradient", 0)
        config.night_light_off = json_data.get("nightLightOff", 0)
        config.min_dim_level = json_data.get("minDimLevel", 0)
        config.devices = json_data.get("devices", 0)
        config.dev_type = json_data.get("devType", 0)
        config.light_type = json_data.get("lightType", 0)
        config.pwm_freq = json_data.get("pwmFreq", 0)
        config.pwm_res = json_data.get("pwmRes", 0)
        config.pwm_range = json_data.get("pwmRange", [])
        config.pwm_ranges = json_data.get("pwmRanges", [])
        config.wcr = json_data.get("wcr", 0)
        config.nowc = json_data.get("nowc", 0)
        config.cct_range = json_data.get("cctRange", [])
        config.render_factor = json_data.get("renderFactor", [])
        config.wizc1 = WizConfig.from_json(json_data.get("wizc1", {}))
        config.wizc2 = WizConfig.from_json(json_data.get("wizc2", {}))
        config.drv_iface = json_data.get("drvIface", 0)
        config.i2c_drv = [I2CDriver.from_json(
            driver) for driver in json_data.get("i2cDrv", [])]
        return config

    def to_dict(self) -> dict[str, str | int | bool | list | dict]:
        return {
            "devTotal": self.dev_total,
            "headTotal": self.head_total,
            "swHead": self.sw_head,
            "ps": self.ps,
            "hasGradient": self.has_gradient,
            "nightLightOff": self.night_light_off,
            "minDimLevel": self.min_dim_level,
            "devices": self.devices,
            "devType": self.dev_type,
            "lightType": self.light_type,
            "pwmFreq": self.pwm_freq,
            "pwmRes": self.pwm_res,
            "pwmRange": self.pwm_range,
            "pwmRanges": self.pwm_ranges,
            "wcr": self.wcr,
            "nowc": self.nowc,
            "cctRange": self.cct_range,
            "renderFactor": self.render_factor,
            "wizc1": self.wizc1.to_dict() if self.wizc1 else {},
            "wizc2": self.wizc2.to_dict() if self.wizc2 else {},
            "drvIface": self.drv_iface,
            "i2cDrv": [driver.to_dict() for driver in self.i2c_drv]
        }

    def __str__(self):
        return f"MethodConfig(dev_total={self.dev_total}, head_total={self.head_total}, sw_head={self.sw_head}, ps={self.ps}, has_gradient={self.has_gradient}, night_light_off={self.night_light_off}, min_dim_level={self.min_dim_level}, devices={self.devices}, dev_type={self.dev_type}, light_type={self.light_type}, pwm_freq={self.pwm_freq}, pwm_res={self.pwm_res}, pwm_range={self.pwm_range}, pwm_ranges={self.pwm_ranges}, wcr={self.wcr}, nowc={self.nowc}, cct_range={self.cct_range}, render_factor={self.render_factor}, wizc1={self.wizc1}, wizc2={self.wizc2}, drv_iface={self.drv_iface}, i2c_drv={self.i2c_drv})"


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
        self.wizard_config1: WizConfig | None = None
        self.wizard_config2: WizConfig | None = None
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
        config.wizard_config1 = WizConfig.from_json(
            json_data.get("wizc1", {}))
        config.wizard_config2 = WizConfig.from_json(
            json_data.get("wizc2", {}))
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
            "wizc1": self.wizard_config1.to_dict() if self.wizard_config1 else {},
            "wizc2": self.wizard_config2.to_dict() if self.wizard_config2 else {},
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

    SCENES = {
        11: {"name": "warm white", "dimming": True, "speed": False, "rgb": False, "temp": True},
        17: {"name": "true colors", "dimming": True, "speed": False, "rgb": False, "temp": False},
        12: {"name": "daylight", "dimming": True, "speed": False, "rgb": False, "temp": True},
        13: {"name": "cool white", "dimming": True, "speed": False, "rgb": False, "temp": True},
        30: {"name": "golden white", "dimming": True, "speed": True, "rgb": False, "temp": False},
        15: {"name": "focus", "dimming": True, "speed": False, "rgb": False, "temp": False},
        16: {"name": "relax", "dimming": True, "speed": False, "rgb": False, "temp": False},
        2: {"name": "romance", "dimming": True, "speed": True, "rgb": False, "temp": False},
        6: {"name": "cozy", "dimming": True, "speed": False, "rgb": False, "temp": False},
        26: {"name": "club", "dimming": True, "speed": True, "rgb": False, "temp": False},
        29: {"name": "candlelight", "dimming": False, "speed": False, "rgb": False, "temp": False},
        5: {"name": "fireplace", "dimming": True, "speed": True, "rgb": False, "temp": False},
        18: {"name": "tv time", "dimming": True, "speed": False, "rgb": False, "temp": False},
        10: {"name": "bedtime", "dimming": True, "speed": False, "rgb": False, "temp": False},
        14: {"name": "night light", "dimming": False, "speed": False, "rgb": False, "temp": False},
        3: {"name": "sunset", "dimming": True, "speed": True, "rgb": False, "temp": False},
        9: {"name": "wakeup", "dimming": True, "speed": False, "rgb": False, "temp": False},
        20: {"name": "spring", "dimming": True, "speed": True, "rgb": False, "temp": False},
        21: {"name": "summer", "dimming": True, "speed": True, "rgb": False, "temp": False},
        22: {"name": "fall", "dimming": True, "speed": True, "rgb": False, "temp": False},
        36: {"name": "snowy sky", "dimming": True, "speed": True, "rgb": False, "temp": False},
        23: {"name": "deep dive", "dimming": True, "speed": True, "rgb": False, "temp": False},
        1: {"name": "ocean", "dimming": True, "speed": True, "rgb": False, "temp": False},
        7: {"name": "forest", "dimming": False, "speed": False, "rgb": False, "temp": False},
        24: {"name": "jungle", "dimming": True, "speed": True, "rgb": False, "temp": False},
        25: {"name": "mojito", "dimming": True, "speed": True, "rgb": False, "temp": False},
        19: {"name": "plant growth", "dimming": True, "speed": False, "rgb": False, "temp": False},
        28: {"name": "halloween", "dimming": True, "speed": True, "rgb": False, "temp": False},
        27: {"name": "christmas", "dimming": True, "speed": True, "rgb": False, "temp": False},
        4: {"name": "party", "dimming": True, "speed": True, "rgb": False, "temp": False},
        8: {"name": "pastel Colors", "dimming": True, "speed": True, "rgb": False, "temp": False},
        32: {"name": "steampunk", "dimming": True, "speed": True, "rgb": False, "temp": False},
        33: {"name": "diwali", "dimming": True, "speed": True, "rgb": False, "temp": False},
        35: {"name": "light alarm", "dimming": False, "speed": False, "rgb": False, "temp": False},
        31: {"name": "pulse", "dimming": True, "speed": True, "rgb": False, "temp": False},
        0: {"name": "colors", "dimming": False, "speed": False, "rgb": True, "temp": True},
        40: {"name": "dim to warm", "dimming": False, "speed": False, "rgb": False, "temp": True},
        34: {"name": "(unknown)", "dimming": False, "speed": False, "rgb": False, "temp": False},
        249: {"name": "pulse", "dimming": False, "speed": False, "rgb": False, "temp": False},
        1000: {"name": "rhythm", "dimming": False, "speed": False, "rgb": False, "temp": False}
    }

    def __init__(self) -> None:

        self.state: bool = False
        self.temp: int = 0
        self.r: int = 0
        self.g: int = 0
        self.b: int = 0
        self.w: int = 0
        self.dimming: int = 0

        self.sceneId: int = 0
        self.speed: int = 0

        self.rssi: int = 0
        self.mac: str = None

        self._provided_fields: set[str] = set()

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool], pilot: 'Pilot' = None) -> 'Pilot':
        """Factory method to create a Pilot instance from a JSON response dictionary."""

        pilot = pilot or Pilot()
        if "state" in json_data:
            pilot.state = json_data["state"]
            pilot._provided_fields.add("state")

        if "temp" in json_data:
            pilot.temp = json_data["temp"]
            pilot._provided_fields.add("temp")

        if "r" in json_data:
            pilot.r = json_data["r"]
            pilot._provided_fields.add("r")

        if "g" in json_data:
            pilot.g = json_data["g"]
            pilot._provided_fields.add("g")

        if "b" in json_data:
            pilot.b = json_data["b"]
            pilot._provided_fields.add("b")

        if "w" in json_data:
            pilot.w = json_data["w"]
            pilot._provided_fields.add("w")

        if "dimming" in json_data:
            pilot.dimming = json_data["dimming"]
            pilot._provided_fields.add("dimming")

        if "sceneId" in json_data:
            pilot.sceneId = json_data["sceneId"]
            pilot._provided_fields.add("sceneId")

        if "speed" in json_data:
            pilot.speed = json_data["speed"]
            pilot._provided_fields.add("speed")

        if "rssi" in json_data:
            pilot.rssi = json_data["rssi"]
            pilot._provided_fields.add("rssi")

        if "mac" in json_data:
            pilot.mac = json_data["mac"]
            pilot._provided_fields.add("mac")

        return pilot

    def isOff(self) -> bool | None:

        return not self.state if self.state is not None else None

    def color_str(self) -> str:

        if self.isOff():
            return "off"

        # If temp is set, show temperature and ignore RGB values (since they are not relevant in white mode)
        if self.temp and not (self.r or self.g or self.b):
            return f"temperature ({self.temp}K)"

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
        return [Pilot.SCENES.get(sceneId).get("name") for sceneId in Pilot.SCENES]

    def scene_str(self) -> str:
        """Get the human-readable name of a scene based on its integer identifier. Handles special cases for certain scene values and falls back to a predefined list of scene names."""

        try:
            return f"{Pilot.SCENES.get(self.sceneId).get("name")} ({self.sceneId}, speed: {self.speed})"

        except IndexError:
            return "Unknown Scene"

    def to_dict(self) -> dict[str, str | int | bool]:

        return {
            "state": self.state,
            "temp": self.temp,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "w": self.w,
            "dimming": self.dimming,
            "sceneId": self.sceneId,
            "speed": self.speed,
            "rssi": self.rssi,
            "mac": self.mac
        }

    def to_payload(self) -> dict[str, str | int | bool]:
        """Return only the fields that were explicitly provided, suitable for setPilot payloads."""

        payload = {}
        for key in ["state", "temp", "r", "g", "b", "w", "dimming", "sceneId", "speed"]:
            if key in self._provided_fields:
                payload[key] = getattr(self, key)

        return payload

    def equals(self, second: 'Pilot') -> bool:

        if self is second:
            return True

        if second is None:
            return False

        return self.to_dict() == second.to_dict()

    def __str__(self):
        return f"Pilot(state={self.state}, temp={self.temp}, r={self.r}, g={self.g}, b={self.b}, w={self.w}, dimming={self.dimming}, sceneId={self.sceneId}, speed={self.speed}, rssi={self.rssi}, mac={self.mac})"


class Power():

    def __init__(self):

        self.power: int = None

    @staticmethod
    def from_json(json_data: dict[str, str | int | bool | list | dict]) -> 'Power':
        """Factory method to create a Power instance from a JSON response dictionary."""

        config = Power()
        config.power = json_data["power"]
        return config

    def to_dict(self) -> dict[str, str | int | bool | list | dict]:

        return {
            "power": self.power
        }

    def __str__(self):
        return f"Power(power={self.power})"


class WizDevice():
    """Represents a single Wiz device with its properties and state."""

    def __init__(self, ip_address: str = None) -> None:

        self.ip_address: str = ip_address

        self.device_info: DeviceInfo = None
        self.model_config: ModelConfig = None
        self.system_config: SystemConfig = None
        self.user_config: UserConfig = None
        self.pilot: Pilot = None
        self.power: Power = None

    def withDeviceInfo(self, device_info: DeviceInfo) -> 'WizDevice':
        self.device_info = device_info
        return self

    def withSystemConfig(self, system_config: SystemConfig) -> 'WizDevice':
        self.system_config = system_config
        return self

    def withModelConfig(self, model_config: ModelConfig) -> 'WizDevice':
        self.model_config = model_config
        return self

    def withUserConfig(self, user_config: UserConfig) -> 'WizDevice':
        self.user_config = user_config
        return self

    def withPilot(self, pilot: Pilot) -> 'WizDevice':
        self.pilot = pilot
        return self

    def withPower(self, power: Power) -> 'WizDevice':
        self.power = power
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
            "model_config": self.model_config.to_dict() if self.model_config else None,
            "user_config": self.user_config.to_dict() if self.user_config else None,
            "pilot": self.pilot.to_dict() if self.pilot else None,
            "power": self.power.to_dict() if self.power else None
        }

    def __str__(self):
        return f"WizDevice(ip_address={self.ip_address}, device_info={self.device_info}, system_config={self.system_config}, model_config={self.model_config}, user_config={self.user_config}, pilot={self.pilot}, power={self.power})"


class WiZListener():

    def onStart(self, ip_addresses: list[str], commands: dict[str, dict]):

        LOGGER.debug("start processing")

    def onMessageSend(self, ip_address: str, message: str):

        LOGGER.debug(f">>> message send to {ip_address}: {message}")

    def onMessageReceived(self, ip_address: str, message: str):

        LOGGER.debug(f"<<< message received from {ip_address}: {message}")

    def onError(self, ip_address: str, exception: Exception):

        LOGGER.debug(
            f"Error while comminicating weith {ip_address}: {exception}")

    def onFinished(self, devices: list[WizDevice]):

        output = "\n".join([str(d) for d in devices])

        LOGGER.debug(f"Devices handled: \n{output}")


class Alias():

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

        if re.match(Alias.IP_PATTERN, label):
            return {label} if label else None

        if re.match(Alias.MAC_PATTERN, label):
            devices = WizDeviceController.discover_wiz_devices(
                broadcast_address="255.255.255.255")
            ip_addresses = {
                d.ip_address for d in devices if d.mac and d.formatted_mac() == label.upper()}
            return ip_addresses or None

        ip_addresses = {
            alias for alias, value in self.aliases.items() if label in value
        }
        if ip_addresses:
            LOGGER.debug("Found IP addresses for aliases: %s",
                         ", ".join(ip_addresses))
        else:
            LOGGER.debug("No aliases found")
        return ip_addresses or None

    def __str__(self) -> str:

        return "\n".join([f"{a}\t{self.aliases[a]}" for a in self.aliases])


class WizDeviceController():
    """Controller class for managing multiple Wiz devices, handling discovery, connection, and command execution."""

    UDP_PORT = 38899

    _RESULT_HANDLERS = {
        "getDevInfo": lambda device, result: device.withDeviceInfo(DeviceInfo.from_json(result)),
        "getSystemConfig": lambda device, result: device.withSystemConfig(SystemConfig.from_json(result)),
        "getModelConfig": lambda device, result: device.withModelConfig(ModelConfig.from_json(result)),
        "getUserConfig": lambda device, result: device.withUserConfig(UserConfig.from_json(result)),
        "getPilot": lambda device, result: device.withPilot(Pilot.from_json(result)),
        "getPower": lambda device, result: device.withPower(Power.from_json(result)),
        "pulse": lambda device, result: device,
    }

    def __init__(self, ip_addresses: 'list[str]', listener: WiZListener = None) -> None:

        self.ip_addresses: 'list[str]' = ip_addresses
        self.devices: 'list[WizDevice]' = list()

        self.listener = listener

        self.commands: dict[str, dict] = None
        self.resetCommands()

        self.requestId: int = 0

    def startListener(self, listener: WiZListener, duration: int = 60) -> None:
        """Listen for incoming Wiz UDP messages and forward events to the configured listener."""

        if not listener:
            LOGGER.warning("No listener configured for UDP listen mode")
            return

        if duration <= 0:
            LOGGER.warning("Duration must be greater than 0 seconds")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind(("", WizDeviceController.UDP_PORT))
            sock.settimeout(1.0)

            LOGGER.info(
                f"Listening for Wiz UDP messages on port {WizDeviceController.UDP_PORT} for {duration} seconds")

            stop_time = time.monotonic() + duration
            while time.monotonic() < stop_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    payload = data.decode("utf-8")
                    LOGGER.debug(
                        f"<<< Received packet from {addr[0]}:{addr[1]}: {payload}")
                    try:
                        message = json.loads(payload)
                    except json.JSONDecodeError:
                        LOGGER.debug(
                            f"Received non-JSON UDP packet from {addr[0]}:{addr[1]}")
                        continue

                    listener.onMessageReceived(
                        ip_address=addr[0], message=message)

                except socket.timeout:
                    continue

                except Exception as ex:
                    LOGGER.error(f"UDP listener error: {ex}")
                    break

        except Exception as ex:
            LOGGER.error(
                f"Unable to start UDP listener on port {WizDeviceController.UDP_PORT}: {ex}")
        finally:
            sock.close()

    def get_source_ip(self) -> str:

        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.setblocking(False)  # must be non-blocking for async
        try:
            test_sock.connect(('8.8.8.8', 1))
            source_ip = test_sock.getsockname()[0]
            return source_ip
        except Exception:
            LOGGER.debug(
                "The system could not auto detect the source ip for 8.8.8.8 on your operating system")
            return None
        finally:
            test_sock.close()

    @staticmethod
    def generate_mac():
        """
            Erzeugt eine stabile, hardwaregebundene ID im 12-stelligen Hex-Format,
            die keine echte MAC-Adresse ist, aber auf demselben Gerät konsistent bleibt.
        """
        system_id = ""

        try:
            if platform.system() == "Windows":
                cmd = 'wmic csproduct get uuid'
                system_id = subprocess.check_output(
                    cmd, shell=True).decode().split('\n')[1].strip()
            elif platform.system() == "Linux":
                # Nutzt die eindeutige Machine-ID unter Linux
                with open("/etc/machine-id", "r") as f:
                    system_id = f.read().strip()
        except Exception:
            system_id = str(uuid.getnode())

        hash_object = hashlib.sha256(system_id.encode())
        hex_hash = hash_object.hexdigest()

        wiz_id = hex_hash[:12].lower()

        return wiz_id

    def resetCommands(self):

        self.commands: dict[str, dict] = {
            "registration": None,
            "getDevInfo": None,
            "getModelConfig": None,
            "getSystemConfig": None,
            "getUserConfig": None,
            "getPower": None,
            "getPilot": None,
            "setPilot": None,
            "pulse": None
        }

    def getDevInfo(self) -> 'WizDeviceController':

        self.commands["getDevInfo"] = {}
        return self

    def getModelConfig(self) -> 'WizDeviceController':

        self.commands["getModelConfig"] = {}
        return self

    def getSystemConfig(self) -> 'WizDeviceController':

        self.commands["getSystemConfig"] = {}
        return self

    def getPower(self) -> 'WizDeviceController':

        self.commands["getPower"] = {}
        return self

    def getUserConfig(self) -> 'WizDeviceController':

        self.commands["getUserConfig"] = {}
        return self

    def getPilot(self) -> 'WizDeviceController':

        self.commands["getPilot"] = {}
        return self

    def setPilot(self, properties: dict[str, str | int]) -> 'WizDeviceController':

        if self.commands["setPilot"] is None:
            self.commands["setPilot"] = {}

        for p in properties:
            if p not in ["state", "temp", "r", "g", "b", "dimming", "sceneId", "speed"]:
                continue
            if p in ["temp", "speed", "dimming", "sceneId"] and properties[p] == 0:
                continue
            self.commands["setPilot"][p] = properties[p]

        return self

    def withState(self, state: bool) -> 'WizDeviceController':

        self.setPilot(properties={"state": state})
        return self

    def withTemp(self, temp: int) -> 'WizDeviceController':

        self.setPilot(properties={"temp": temp})
        return self

    def withDimming(self, dimming: int) -> 'WizDeviceController':

        self.setPilot(properties={"dimming": dimming})
        return self

    def withColor(self, red: int = 0, green: int = 0, blue: int = 0, white: int = 0) -> 'WizDeviceController':

        self.setPilot(properties={"r": red, "g": green, "b": blue, "w": white})
        return self

    def withScene(self, scene: str) -> 'WizDeviceController':

        if scene.isdigit():
            sceneId = int(scene)
        else:
            _sceneIds = [sceneId for sceneId in Pilot.SCENES if Pilot.SCENES.get(sceneId, None).get("name") == scene]
            if not _sceneIds:
                raise WizDeviceException(f"Unknown scene '{scene}'")
            sceneId = _sceneIds[0]

        self.setPilot(properties={"sceneId": sceneId})
        return self

    def withSpeed(self, speed: int) -> 'WizDeviceController':

        self.setPilot(properties={"speed": speed})
        return self

    def withHome(self, homeId: int) -> 'WizDeviceController':

        self.setPilot(properties={"homeId": homeId})
        return self

    def withRoom(self, roomId: int) -> 'WizDeviceController':

        self.setPilot(properties={"roomId": roomId})
        return self

    def withGroup(self, groupId: int) -> 'WizDeviceController':

        self.setPilot(properties={"groupId": groupId})
        return self

    def register(self, value: bool = True) -> 'WizDeviceController':

        self.commands["registration"] = {
            "register": value,
            "phoneMac": WizDeviceController.generate_mac(),
            "phoneIp": self.get_source_ip()
        }
        return self

    def unregister(self) -> 'WizDeviceController':

        self.register(False)
        return self

    def pulse(self, delta: int = 15, duration: int = 300) -> 'WizDeviceController':

        self.commands["pulse"] = {
            "delta": delta,
            "duration": duration
        }
        return self

    def reboot(self) -> 'WizDeviceController':

        self.commands["reboot"] = {}
        return self

    def reset(self) -> 'WizDeviceController':

        self.commands["reset"] = {}
        return self

    def _get_device_for_ip_address(self, ip_address: str) -> 'WizDevice':

        for device in self.devices:
            if device.ip_address == ip_address:
                return device

        new_device = WizDevice(ip_address=ip_address)
        self.devices.append(new_device)
        return new_device

    def perform(self, timeout: float = 1) -> None:

        def handle_responses(command: str, responses: dict[str, dict]):

            if not responses:
                return

            for remote_ip in responses:

                device = self._get_device_for_ip_address(remote_ip)
                for response in responses[remote_ip]:
                    json_response = json.loads(response)
                    if "result" in json_response:
                        if command == "setPilot" and json_response["result"].get("success"):
                            device = device.withPilot(
                                Pilot.from_json(params, pilot=device.pilot))
                        else:
                            handler = WizDeviceController._RESULT_HANDLERS.get(
                                command)
                            if handler:
                                device = handler(
                                    device, json_response["result"])

        def request(ip_address: str, payload: str, timeout: float) -> dict[str, list[str]]:

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.bind(('', WizDeviceController.UDP_PORT))

            LOGGER.debug(
                f">>> Sending message {payload} to {ip_address}:{WizDeviceController.UDP_PORT}")

            if self.listener:
                self.listener.onMessageSend(
                    ip_address=ip_address, message=payload)

            responses: dict[str, list[str]] = dict()
            try:
                sock.sendto(payload.encode(
                    "utf-8"), (ip_address, WizDeviceController.UDP_PORT))

                while True:
                    data, addr = sock.recvfrom(1024)
                    decoded_data = data.decode("utf-8")

                    LOGGER.debug(
                        f"<<< Received response from {addr[0]}: {decoded_data}")

                    if self.listener:
                        self.listener.onMessageReceived(
                            ip_address=addr[0], message=decoded_data)

                    if addr[0] in responses:
                        responses[addr[0]].append(decoded_data)
                    else:
                        responses[addr[0]] = [decoded_data]

                    # if not a broadcast there won't be other messages
                    if not ip_address.endswith(".255"):
                        break

            except Exception as e:

                if self.listener:
                    self.listener.onError(
                        ip_address=ip_address, exception=e)

            finally:
                sock.close()

            return responses

        if self.listener:
            self.listener.onStart(
                ip_addresses=self.ip_addresses, commands=self.commands)

        for ip_address in self.ip_addresses:

            for command, params in self.commands.items():
                if params is None:
                    continue

                self.requestId += 1
                payload = {
                    "version": 1,
                    "method": command,
                    "id": self.requestId,
                    "params": params
                }

                responses = request(
                    ip_address=ip_address, payload=json.dumps(payload), timeout=timeout)
                handle_responses(command=command, responses=responses)

        if self.listener:
            self.listener.onFinished(devices=self.devices)

        self.resetCommands()

    def __str__(self):
        return f"WizDeviceController(ip_addresses={self.ip_addresses}, commands={self.commands}, devices={self.devices})"


class Program():

    _BEGIN = 0
    _END = -1

    PROGRAM_INTERVAL = "interval"
    PROGRAM_FADE = "fade"
    PROGRAM_WAKEUP = "wakeup"
    PROGRAM_DOZE = "doze"
    PROGRAM_AMBIENT = "ambient"
    PROGRAM_RGB = "rgb"
    PROGRAM_GBR = "gbr"
    PROGRAM_BRG = "brg"
    PROGRAM_BGR = "bgr"
    PROGRAM_RBG = "rbg"
    PROGRAM_GRB = "grb"
    PROGRAM_RANDOM = "random"
    PROGRAM_INFINITE = "infinite"
    PROGRAM_WARM_TO_COLD = "warm-to-cold"
    PROGRAM_COLD_TO_WARM = "cold-to-warm"
    PROGRAM_SUNRISE = "sunrise"
    PROGRAM_SUNSET = "sunset"
    PROGRAM_SUNRISE_SUNSET = "sunrise-sunset"

    PROGRAMS_STARTING_FROM_CURRENT = [
        PROGRAM_FADE, PROGRAM_DOZE, PROGRAM_AMBIENT]

    PROGRAMS = {
        PROGRAM_INTERVAL: {
            _BEGIN: {"state": True},
            _END: {"state": False}
        },
        PROGRAM_FADE: {
            _BEGIN: {"state": True, "dimming": 0},
            _END: {"state": False, "dimming": 10}
        },
        PROGRAM_WAKEUP: {
            _BEGIN: {"r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            16: {"r": 0, "g": 0, "b": 20, "w": 0, "dimming": 20},
            24: {"r": 0, "g": 60, "b": 255, "w": 0, "dimming": 60},
            59: {"r": 255, "g": 255, "b": 255, "w": 50, "dimming": 100},
            60: {"r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            _END: {"state": False, "r": 0, "g": 0,
                   "b": 0, "w": 0, "dimming": 10}
        },
        PROGRAM_DOZE: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0, "w": 0, "dimming": 0},
            1: {"r": 255, "g": 47, "b": 0, "dimming": 40},
            58: {"r": 255, "g": 47, "b": 0, "dimming": 10},
            59: {"r": 0, "g": 0, "b": 0, "dimming": 10},
            _END: {"state": False, "r": 0, "g": 0, "b": 0, "dimming": 10}
        },
        PROGRAM_AMBIENT: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0, "w": 0, "dimming": 0},
            1: {"r": 255, "g": 47, "b": 0, "dimming": 40},
            59: {"r": 255, "g": 47, "b": 0, "dimming": 40},
            _END: {"state": False, "r": 0, "g": 0, "b": 0, "dimming": 10}
        },
        PROGRAM_RGB: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 255, "g": 0, "b": 0},
            120: {"r": 255, "g": 255, "b": 0},
            180: {"r": 0, "g": 255, "b": 0},
            240: {"r": 0, "g": 255, "b": 255},
            300: {"r": 0, "g": 0, "b": 255},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_GBR: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 0, "g": 255, "b": 0},
            120: {"r": 0, "g": 255, "b": 255},
            180: {"r": 0, "g": 0, "b": 255},
            240: {"r": 255, "g": 0, "b": 255},
            300: {"r": 255, "g": 0, "b": 0},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_BRG: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 0, "g": 0, "b": 255},
            120: {"r": 255, "g": 0, "b": 255},
            180: {"r": 255, "g": 0, "b": 0},
            240: {"r": 255, "g": 255, "b": 0},
            300: {"r": 0, "g": 255, "b": 0},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_BGR: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 0, "g": 0, "b": 255},
            120: {"r": 0, "g": 255, "b": 255},
            180: {"r": 0, "g": 255, "b": 0},
            240: {"r": 255, "g": 255, "b": 0},
            300: {"r": 255, "g": 0, "b": 0},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_RBG: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 255, "g": 0, "b": 0},
            120: {"r": 255, "g": 0, "b": 255},
            180: {"r": 0, "g": 0, "b": 255},
            240: {"r": 0, "g": 255, "b": 255},
            300: {"r": 0, "g": 255, "b": 0},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_GRB: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0},
            60: {"r": 0, "g": 255, "b": 0},
            120: {"r": 255, "g": 255, "b": 0},
            180: {"r": 255, "g": 0, "b": 0},
            240: {"r": 255, "g": 0, "b": 255},
            300: {"r": 0, "g": 0, "b": 255},
            360: {"r": 0, "g": 0, "b": 0},
            _END: {"state": False}
        },
        PROGRAM_RANDOM: {
        },
        PROGRAM_INFINITE: {
            _BEGIN: {"r": 0, "g": 0, "b": 255},
            60: {"r": 0, "g": 255, "b": 255},
            120: {"r": 0, "g": 255, "b": 0},
            180: {"r": 255, "g": 255, "b": 0},
            240: {"r": 255, "g": 0, "b": 0},
            300: {"r": 255, "g": 0, "b": 255},
            360: {"r": 0, "g": 0, "b": 255},
            _END: {"state": False}
        },
        PROGRAM_WARM_TO_COLD: {
            _BEGIN: {"state": True, "temp": 2200},
            _END: {"state": False, "temp": 6500}
        },
        PROGRAM_COLD_TO_WARM: {
            _BEGIN: {"state": True, "temp": 6500},
            _END: {"state": False, "temp": 2200}
        },
        PROGRAM_SUNRISE: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            16: {"r": 0, "g": 0, "b": 20, "w": 0, "dimming": 20},
            24: {"r": 0, "g": 60, "b": 255, "w": 0, "dimming": 60},
            59: {"r": 255, "g": 255, "b": 255, "w": 50, "dimming": 100},
            _END: {"state": False, "r": 0, "g": 0,
                   "b": 0, "w": 0, "dimming": 10}
        },
        PROGRAM_SUNSET: {
            _BEGIN: {"state": True, "r": 255, "g": 255, "b": 255, "w": 50, "dimming": 100},
            16: {"r": 0, "g": 60, "b": 255, "w": 0, "dimming": 60},
            24: {"r": 0, "g": 0, "b": 20, "w": 0, "dimming": 20},
            59: {"r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            _END: {"state": False, "r": 0, "g": 0,
                   "b": 0, "w": 0, "dimming": 10}
        },
        PROGRAM_SUNRISE_SUNSET: {
            _BEGIN: {"state": True, "r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            16: {"r": 0, "g": 0, "b": 20, "w": 0, "dimming": 20},
            24: {"r": 0, "g": 60, "b": 255, "w": 0, "dimming": 60},
            59: {"r": 255, "g": 255, "b": 255, "w": 50, "dimming": 100},
            75: {"r": 0, "g": 60, "b": 255, "w": 0, "dimming": 60},
            90: {"r": 0, "g": 0, "b": 20, "w": 0, "dimming": 20},
            119: {"r": 0, "g": 0, "b": 0, "w": 0, "dimming": 10},
            _END: {"state": False, "r": 0, "g": 0,
                   "b": 0, "w": 0, "dimming": 10}
        }
    }

    def __init__(self, wizController: WizDeviceController, programID: str, duration: int, dimming: int | None = None) -> None:

        if programID not in Program.PROGRAMS:
            raise ValueError(f"Invalid program ID: {programID}")

        elif programID == Program.PROGRAM_RANDOM:
            programID = random.choice([
                Program.PROGRAM_RGB,
                Program.PROGRAM_GBR,
                Program.PROGRAM_BRG,
                Program.PROGRAM_RBG,
                Program.PROGRAM_GRB,
                Program.PROGRAM_BGR
            ])

        if duration <= 0:
            raise WizDeviceException(
                "Program duration must be greater than 0 seconds")

        self.programID: int = programID
        self.dimming: int | None = dimming
        self.start_time: float = 0
        self.duration: int = duration

        self._current_program: dict = Program.PROGRAMS.get(
            programID, {}).copy()
        max_time: int = max(max(self._current_program.keys()), 1)
        self._time_factor: float = max_time / duration

        self.wizController: WizDeviceController = wizController
        self._last_pilot: Pilot = None

    def reset(self) -> None:

        self._time = Program._BEGINelapsed

    def get_pilot(self, time_: int) -> Pilot:

        current_step, next_step = self._get_step(time_)
        if time_ <= 0 or time_ >= self.duration:
            return Pilot.from_json(self._current_program[current_step]) if current_step is not None else None

        pilot = self.interpolate(time_, current_step, next_step)

        return pilot

    def interpolate(self, time_: int, current_step: int, next_step: int) -> Pilot:

        duration_of_step = max(next_step, current_step + 1) - current_step
        progress_in_step = time_ - current_step / self._time_factor

        interpolable_keys = ["r", "g", "b", "w", "dimming", "temp"]
        interpolated_values = {}

        for key in interpolable_keys:
            if key not in self._current_program[current_step] or key not in self._current_program[next_step]:
                continue
            elif key in self._current_program[current_step] and key not in self._current_program[next_step]:
                interpolated_values[key] = self._current_program[current_step][key]
                continue

            start_value = self._current_program[current_step].get(key, 0)
            end_value = self._current_program[next_step].get(
                key, 0) if next_step is not None else start_value
            interpolated_value = int(start_value + (end_value - start_value) * (
                progress_in_step / duration_of_step) * self._time_factor)

            if key == "dimming":
                interpolated_value = int((interpolated_value + 5) // 10 * 10)
            elif key == "temp":
                interpolated_value = int(
                    (interpolated_value + 50) // 100 * 100)

            interpolated_values[key] = interpolated_value

        for key in self._current_program[current_step]:
            if key not in interpolable_keys:
                interpolated_values[key] = self._current_program[current_step][key]

        for key in ["state", "sceneId", "speed"]:
            if key not in interpolated_values:
                steps = [s for s in self._current_program.keys(
                ) if s != Program._END and s <= current_step]
                for step in reversed(steps):
                    if key in self._current_program[step]:
                        interpolated_values[key] = self._current_program[step][key]
                        break

        if self.dimming is not None and "dimming" not in interpolated_values:
            interpolated_values["dimming"] = self.dimming

        return Pilot.from_json(interpolated_values)

    def _get_step(self, time_: int) -> tuple[int, int]:

        steps = list(self._current_program.keys())
        if time_ >= self.duration:
            return steps[-1], None

        factorized_time = self._time_factor * time_
        if steps[-1] == Program._END:
            steps = steps[:-1]

        current_index = None
        current_step = None

        for i, step_time in enumerate(steps):
            if factorized_time >= step_time:
                current_index = i
                current_step = step_time
            else:
                break

        next_step = steps[current_index + 1] if current_index + \
            1 < len(steps) else Program._END
        return current_step, next_step

    def performPilot(self, elapsed: int) -> None:

        pilot = self.get_pilot(elapsed)
        if pilot is not None and not pilot.equals(self._last_pilot):
            LOGGER.debug(
                f"Sending pilot for program duration {self.duration} sec at elapsed {elapsed} sec")
            self.wizController.resetCommands()
            self.wizController.setPilot(pilot.to_payload()).perform()

        self._last_pilot = pilot

    def initialize(self, offset: int = 0) -> 'Program':

        if self.programID in Program.PROGRAMS_STARTING_FROM_CURRENT:
            self.wizController.resetCommands()
            self.wizController.getPilot().perform()

            if not self.wizController.devices or not self.wizController.devices[0].pilot:
                raise WizDeviceException(
                    f"Unable to get current pilot for program '{self.programID}'"
                )

            current_pilot = self.wizController.devices[0].pilot.to_dict()
            for k in ["r", "g", "b", "w", "c", "dimming"]:
                if k in current_pilot and k in self._current_program[Program._BEGIN]:
                    self._current_program[Program._BEGIN][k] = current_pilot[k]

        self._last_pilot: Pilot | None = None
        self.start_time = int(time.time()) - offset

        return self

    def start(self, interval: int = 1) -> None:
        """Run a program by polling its pilot at the configured interval and sending new pilots when they change."""

        def _format_time(secs: int) -> str:

            return f"{(secs // 3600):02}:{(secs // 60 % 60):02}:{(secs % 60):02}"

        if interval <= 0:
            raise WizDeviceException(
                "Program update interval must be greater than 0 seconds")

        elapsed = 0
        interrupted = False
        interrupted_exception: BaseException | None = None

        def _signal_handler(signum, frame):
            nonlocal interrupted
            interrupted = True

        original_sigint = None
        original_sigterm = None
        try:
            original_sigint = signal.getsignal(signal.SIGINT)
            original_sigterm = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except Exception:
            original_sigint = None
            original_sigterm = None

        try:
            while True:

                elapsed = int(time.time() - self.start_time)
                if self.programID == Program.PROGRAM_INFINITE:
                    elapsed = elapsed % self.duration
                    LOGGER.info(
                        f"Elapsed: {_format_time(elapsed)}, ETA: {_format_time(self.duration - elapsed)}, {int(elapsed / self.duration * 360)}°")
                else:
                    LOGGER.info(
                        f"Elapsed: {_format_time(elapsed)}, ETA: {_format_time(self.duration - elapsed)}, {int(100 * elapsed / self.duration)}%")

                before_perform = time.time()
                self.performPilot(elapsed)

                if elapsed >= self.duration:
                    break

                try:
                    time.sleep(
                        max(interval - (time.time() - before_perform), 0))

                except BaseException as ex:
                    if interrupted or isinstance(ex, KeyboardInterrupt):
                        interrupted = True
                        interrupted_exception = ex
                        break
                    raise

                if interrupted:
                    break

        finally:
            if interrupted:
                LOGGER.info(
                    f"Program interrupted after {elapsed} seconds; sending final program step")
                self.performPilot(self.duration)

            try:
                if original_sigint is not None:
                    signal.signal(signal.SIGINT, original_sigint)
                if original_sigterm is not None:
                    signal.signal(signal.SIGTERM, original_sigterm)
            except Exception:
                pass

        if interrupted and interrupted_exception is not None:
            raise interrupted_exception

    @staticmethod
    def from_json(json_: dict) -> 'Program':

        program = Program(wizController=WizDeviceController(ip_addresses=json_.get("ip_addresses", [])),
                          programID=json_.get("programID", None),
                          dimming=json_.get("dimming", 100),
                          duration=json_.get("duration", 0))

        program.start_time = json_.get("start_time", 0)

        return program

    def to_dict(self) -> dict:

        return {
            "programID": self.programID,
            "dimming": self.dimming,
            "start_time": self.start_time,
            "duration": self.duration,
            "ip_addresses": self.wizController.ip_addresses
        }

    def __str__(self):
        return f"Program(controller={self.wizController}, programId={self.programID}, duration={self.duration}, dimming={self.dimming}, start_time={self.start_time})"


class WizDeviceCLI():
    """Command-line interface for interacting with Wiz devices. Parses command-line arguments, executes commands, and provides help information."""

    _USAGE = "usage"
    _DESCR = "descr"
    _REGEX = "regex"
    _TYPES = "types"
    _ACTION = "action"

    _COMMAND = "command"
    _ARGS = "args"
    _PARAMS = "params"

    @staticmethod
    def parse_program_duration(arg: str) -> int:
        """Parse program duration as minutes, accepting integer minutes or HH:MM like 24:00."""

        minutes = None
        if re.fullmatch(r"[1-9][0-9]{0,3}", arg):
            minutes = int(arg)
        else:
            time_match = re.fullmatch(
                r"(?:([01]?\d|2[0-3]):([0-5]\d)|24:00)", arg)
            if time_match:
                if arg == "24:00":
                    minutes = 1440
                else:
                    hours = int(time_match.group(1))
                    mins = int(time_match.group(2))
                    minutes = hours * 60 + mins

        if minutes is None or minutes < 1 or minutes > 1440:
            raise ValueError(
                "Program duration must be between 1 and 1440 minutes, or in HH:MM format up to 24:00"
            )

        return minutes * 60

    COMMANDS: dict[str, dict[str, object]] = {
        "aliases": {
            _USAGE: "--aliases",
            _DESCR: "print known aliases from .known_wizs file",
            _REGEX: None,
            _TYPES: None,
            _ACTION: None,
        },
        "scan": {
            _USAGE: "--scan",
            _DESCR: "scan for Wiz devices",
            _REGEX: None,
            _TYPES: None,
            _ACTION: None,
        },
        "status": {
            _USAGE: "--status",
            _DESCR: "just read and print the basic information of wiz device",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.getPilot(),
        },
        "power": {
            _USAGE: "--power",
            _DESCR: "read power measurements from wiz device",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.getPower(),
        },
        "on": {
            _USAGE: "--on",
            _DESCR: "turn device on",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.withState(state=True),
        },
        "off": {
            _USAGE: "--off",
            _DESCR: "turn device off",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.withState(state=False),
        },
        "temp": {
            _USAGE: "--temp <temp>",
            _DESCR: "set temperature for white\n- <temp> value 2200 - 6500",
            _REGEX: r"^%s$" % (_REG_TEMP),
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withTemp(temp=params[0]),
        },
        "dimming": {
            _USAGE: "--dimming <dimming>",
            _DESCR: "set dimming for light\n- <dimming> value 10 - 100",
            _REGEX: r"^%s$" % (_REG_DIMMING),
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withDimming(dimming=params[0]),
        },
        "color": {
            _USAGE: "--color <red> <green> <blue> [<shite>]",
            _DESCR: "set color, each value 0 - 255",
            _REGEX: r"^%s %s %s( %s)?$" % (_REG_255, _REG_255, _REG_255, _REG_255),
            _TYPES: [int, int, int, int],
            _ACTION: lambda controller, params: controller.withColor(
                red=params[0], green=params[1], blue=params[2], white=params[3] if len(
                    params) == 4 else 0
            ),
        },
        "scene": {
            _USAGE: "--scene <id/name>",
            _DESCR: "set scene by name or id\n- %s" % "\n- ".join(Pilot.scene_list()),
            _REGEX: r"^(%s)$" % ("|".join([Pilot.SCENES.get(sceneId).get("name") for i, sceneId in enumerate(Pilot.SCENES) if i < len(Pilot.SCENES) - 2])),
            _TYPES: [str],
            _ACTION: lambda controller, params: controller.withScene(scene=params[0]),
        },
        "pulse": {
            _USAGE: "--pulse <delta> <duration>",
            _DESCR: "fade-in and out bulb acc. delta +/- and duration in ms",
            _REGEX: r"^(-?(?:\d{1,2}|100)) (\d{1,7})$",
            _TYPES: [int, int],
            _ACTION: lambda controller, params: controller.pulse(delta=params[0], duration=params[1]),
        },
        "speed": {
            _USAGE: "--speed <speed>",
            _DESCR: "set speed for scene, speed 10 - 200",
            _REGEX: r"^([1-9][0-9]|1[0-9][0-9]|200)$",
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withSpeed(speed=params[0]),
        },
        "program": {
            _USAGE: "--program <name> <duration> [<dimming>]",
            _DESCR: "run a built-in program for a duration in minutes or HH:MM (24:00 supported)\n- supported names: %s" % ", ".join(sorted(Program.PROGRAMS.keys())),
            _REGEX: r"^(%s) ((?:[1-9][0-9]{0,3})|(?:[01]?\d:[0-5]\d)|(?:2[0-3]:[0-5]\d)|24:00)(?: ((?:[1-9][0-9]|100)))?$" % "|".join([re.escape(name) for name in Program.PROGRAMS]),
            _TYPES: [str, parse_program_duration, int],
            _ACTION: lambda controller, params: Program(controller, params[0], duration=params[1], dimming=params[2] if len(params) > 2 else None).initialize().start(),
        },
        "register": {
            _USAGE: "--register",
            _DESCR: "register this client",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.register(),
        },
        "unregister": {
            _USAGE: "--unregister",
            _DESCR: "unregister this client",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.unregister(),
        },
        "listen": {
            _USAGE: "--listen <seconds>",
            _DESCR: "Listen to broadvcast messages and print them",
            _REGEX: r"^(\d+)$",
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.startListener(listener=WiZListener(), duration=params[0]) if params else None,
        },
        "reset": {
            _USAGE: "--reset",
            _DESCR: "set device to factory settings",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.reset(),
        },
        "reboot": {
            _USAGE: "--reboot",
            _DESCR: "reboot the device",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: controller.reboot(),
        },
        "home": {
            _USAGE: "--home <homeId>",
            _DESCR: "set home in case that you send a broadcast",
            _REGEX: r"^(\d+)$",
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withHome(homeId=params[0]),
        },
        "room": {
            _USAGE: "--room <roomId>",
            _DESCR: "set room in case that you send a broadcast",
            _REGEX: r"^(\d+)$",
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withRoom(roomId=params[0]),
        },
        "group": {
            _USAGE: "--group <groupId>",
            _DESCR: "set group in case that you send a broadcast",
            _REGEX: r"^(\d+)$",
            _TYPES: [int],
            _ACTION: lambda controller, params: controller.withGroup(groupId=params[0]),
        },
        "help": {
            _USAGE: "--help [<command>]",
            _DESCR: "prints help optionally for given command",
            _REGEX: r"^([a-z-]+)?$",
            _TYPES: None,
            _ACTION: None,
        },
        "dump": {
            _USAGE: "--dump",
            _DESCR: "request full state of bulb",
            _REGEX: None,
            _TYPES: None,
            _ACTION: lambda controller, params: [
                controller.getDevInfo(),
                controller.getSystemConfig(),
                controller.getModelConfig(),
                controller.getUserConfig(),
                controller.getPilot(),
                controller.getPower(),
            ],
        },
        "print": {
            _USAGE: "--print",
            _DESCR: "prints collected data of bulb",
            _REGEX: None,
            _TYPES: None,
            _ACTION: None,
        },
        "json": {
            _USAGE: "--json",
            _DESCR: "prints information in json format",
            _REGEX: None,
            _TYPES: None,
            _ACTION: None,
        },
        "log": {
            _USAGE: "--log <DEBUG|INFO|WARNING|ERROR>",
            _DESCR: "set loglevel",
            _REGEX: r"^(DEBUG|INFO|WARNING|ERROR)$",
            _TYPES: [str],
            _ACTION: None,
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
                ip_addresses, cliCommands = self.parse_args(sys.argv)
                if ip_addresses and cliCommands:
                    self.process(ip_addresses=ip_addresses,
                                 cliCommands=cliCommands)
                elif not ip_addresses:
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

            def onStart(self, ip_addresses: list[str], commands: dict[str, dict]):
                print("MAC\t\tIP Address\tModule\tHome\tRoom\tGroup\tAlias", flush=True)

            def onFinished(self, devices: list[WizDevice]):

                for device in devices:
                    if not device.system_config:
                        continue

                    alias = self.alias.aliases[device.ip_address] if self.alias and device.ip_address in self.alias.aliases else ""
                    print(f"{WizDevice.formatted_mac(device.system_config.mac)}\t{device.ip_address}\t{device.system_config.module_name}\t{device.system_config.home_id}\t{device.system_config.room_id}\t{device.system_config.group_id}\t{alias}", flush=True)

        controller = WizDeviceController(
            ip_addresses=["255.255.255.255"], listener=ScanListener(alias=self.alias))
        controller.getSystemConfig().perform()

    def print_help(self):

        help = self._build_help(header=True)

        help += "\n\nBasic commands:"
        help += self._build_help(command="status")
        help += self._build_help(command="power")
        help += self._build_help(command="on")
        help += self._build_help(command="off")

        help += "\n\nSet light:"
        help += self._build_help(command="temp")
        help += self._build_help(command="dimming")
        help += self._build_help(command="color")

        help += "\n\nSet scene:"
        help += self._build_help(command="scene")
        help += self._build_help(command="speed")

        help += "\n\nSet program:"
        help += self._build_help(command="program")

        help += "\n\nOther commands:"
        help += self._build_help(command="pulse")
        help += self._build_help(command="register")
        help += self._build_help(command="unregister")
        help += self._build_help(command="listen")
        help += self._build_help(command="reboot")
        help += self._build_help(command="reset")
        help += self._build_help(command="home")
        help += self._build_help(command="room")
        help += self._build_help(command="group")
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

        if device.power:
            print(f"\n  Power:")
            print(f"    Power:               {device.power.power} W")

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
            print(f"    Wizard Config 1:")
            if device.user_config.wizard_config1:
                print(
                    f"      mode:              {device.user_config.wizard_config1.mode}")
                print(
                    f"      opts:              {device.user_config.wizard_config1.opts}")
            else:
                print(f"      <none>")
            print(f"    Wizard Config 2:")
            if device.user_config.wizard_config2:
                print(
                    f"      mode:              {device.user_config.wizard_config2.mode}")
                print(
                    f"      opts:              {device.user_config.wizard_config2.opts}")
            else:
                print(f"      <none>")
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

        if device.model_config:
            print(f"\n  Model Configuration:")
            print(f"    devTotal:            {device.model_config.dev_total}")
            print(f"    headTotal:           {device.model_config.head_total}")
            print(f"    swHead:              {device.model_config.sw_head}")
            print(f"    ps:                  {device.model_config.ps}")
            print(
                f"    hasGradient:         {device.model_config.has_gradient}")
            print(
                f"    nightLightOff:       {device.model_config.night_light_off}")
            print(
                f"    minDimLevel:         {device.model_config.min_dim_level}")
            print(f"    devices:             {device.model_config.devices}")
            print(f"    devType:             {device.model_config.dev_type}")
            print(f"    lightType:           {device.model_config.light_type}")
            print(f"    pwmFreq:             {device.model_config.pwm_freq}")
            print(f"    pwmRes:              {device.model_config.pwm_res}")
            print(f"    pwmRange:            {device.model_config.pwm_range}")
            print(f"    pwmRanges:           {device.model_config.pwm_ranges}")
            print(f"    wcr:                 {device.model_config.wcr}")
            print(f"    nowc:                {device.model_config.nowc}")
            print(f"    cctRange:            {device.model_config.cct_range}")
            print(
                f"    renderFactor:        {device.model_config.render_factor}")
            print(f"    wizc1:")
            if device.model_config.wizc1:
                print(
                    f"      mode:              {device.model_config.wizc1.mode}")
                print(
                    f"      opts:              {device.model_config.wizc1.opts}")
            else:
                print(f"      <none>")

            print(f"    wizc2:")
            if device.model_config.wizc2:
                print(
                    f"      mode:              {device.model_config.wizc2.mode}")
                print(
                    f"      opts:              {device.model_config.wizc2.opts}")
            else:
                print(f"      <none>")

            print(f"    drvIface:            {device.model_config.drv_iface}")
            print(f"    i2cDrv:")
            if device.model_config.i2c_drv:
                for idx, driver in enumerate(device.model_config.i2c_drv, start=1):
                    print(
                        f"      [{idx}] chip={driver.chip} addr={driver.addr} freq={driver.freq} curr={driver.curr} output={driver.output}")
            else:
                print(f"      []")

        if device.device_info:

            print(f"\n  Device Configuration:")
            print(f"    Module Name:         {device.device_info.module_name}")
            print(f"    Flash Info:          {device.device_info.flash_info}")
            print(
                f"    device type:         {device.device_info.features.device_type.capitalize()}")
            print(
                f"    has RGB LED:         {device.device_info.features.color}")
            print(
                f"    has white LED:       {device.device_info.features.white}")
            print(
                f"    has temperature:     {device.device_info.features.temp}")
            print(
                f"    has dimming:         {device.device_info.features.dimming}")
            print(
                f"    has power meter:     {device.device_info.features.power_meter}")
            print(
                f"    Description:         {device.device_info.features.getFeaturesDescription()}")

        print()

    def process(self, ip_addresses: 'list[str]', cliCommands: 'list[dict]') -> None:

        def buildRequsts(controller: WizDeviceController, cliCommands: 'list[dict]') -> list[str]:

            commands: list[str] = list()
            for command in cliCommands:
                cmd = command[WizDeviceCLI._COMMAND]
                commands.append(cmd)

                cmd_def = WizDeviceCLI.COMMANDS.get(cmd, {})
                action = cmd_def.get(WizDeviceCLI._ACTION)
                if action:
                    action(controller, command.get(WizDeviceCLI._PARAMS, []))

            return commands

        try:
            controller = WizDeviceController(
                ip_addresses=ip_addresses, listener=WiZListener())

            commands = buildRequsts(controller, cliCommands)

            controller.perform()

            if "print" in commands or "status" in commands or "json" in commands:

                self.print(devices=controller.devices,
                           json_=("json" in commands))

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
