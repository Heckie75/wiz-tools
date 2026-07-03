import unittest

from wiz import (
    DeviceInfo,
    SystemConfig,
    WizConfig,
    I2CDriver,
    ModelConfig,
    UserConfig,
    Pilot,
)


class TestModels(unittest.TestCase):

    def test_device_info_from_json_and_to_dict(self):
        j = {"devMac": "aabbccddeeff", "moduleName": "wiz_shrgb_01", "flash": [1, 2, 3]}
        info = DeviceInfo.from_json(j)

        self.assertEqual(info.device_mac, "aabbccddeeff")
        self.assertEqual(info.module_name, "wiz_shrgb_01")
        self.assertEqual(info.flash_info, [1, 2, 3])
        self.assertIsNotNone(info.features)
        d = info.to_dict()
        self.assertIn("device_mac", d)
        self.assertIn("features", d)

    def test_system_config_from_json_and_to_dict(self):
        j = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "homeId": "home123",
            "roomId": "room1",
            "rgn": "EU",
            "moduleName": "wiz_shrgbc_01",
            "fwVersion": "1.2.3",
            "groupId": 5,
            "ping": 10,
            "accUdpPropRate": 2,
        }

        cfg = SystemConfig.from_json(j)
        self.assertEqual(cfg.mac, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(cfg.home_id, "home123")
        self.assertEqual(cfg.room_id, "room1")
        self.assertEqual(cfg.region, "EU")
        self.assertEqual(cfg.module_name, "wiz_shrgbc_01")
        self.assertEqual(cfg.firmware_version, "1.2.3")
        self.assertEqual(cfg.group_id, 5)
        self.assertEqual(cfg.ping, 10)
        self.assertEqual(cfg.acc_udp_prop_rate, 2)
        self.assertIsInstance(cfg.to_dict(), dict)

    def test_wiz_config_from_json_and_to_dict(self):
        j = {"mode": [1, 2, 3], "opts": {"optA": True}}
        w = WizConfig.from_json(j)
        self.assertEqual(w.mode, [1, 2, 3])
        self.assertEqual(w.opts, {"optA": True})
        self.assertEqual(w.to_dict()["mode"], [1, 2, 3])

    def test_i2c_driver_from_json_and_to_dict(self):
        j = {"chip": "chip1", "addr": 16, "freq": 400, "curr": [10], "output": [255]}
        d = I2CDriver.from_json(j)
        self.assertEqual(d.chip, "chip1")
        self.assertEqual(d.addr, 16)
        self.assertEqual(d.freq, 400)
        self.assertEqual(d.curr, [10])
        self.assertEqual(d.output, [255])
        self.assertEqual(d.to_dict()["chip"], "chip1")

    def test_model_config_from_json_and_to_dict(self):
        j = {
            "devTotal": 2,
            "headTotal": 1,
            "swHead": 0,
            "ps": 1,
            "hasGradient": 0,
            "nightLightOff": 0,
            "minDimLevel": 10,
            "devices": 4,
            "devType": 7,
            "lightType": 1,
            "pwmFreq": 1000,
            "pwmRes": 8,
            "pwmRange": [0, 255],
            "pwmRanges": [255],
            "wcr": 0,
            "nowc": 0,
            "cctRange": [2200, 6500],
            "renderFactor": [1],
            "wizc1": {"mode": [9], "opts": {"x": 1}},
            "wizc2": {"mode": [], "opts": {}},
            "drvIface": 2,
            "i2cDrv": [{"chip": "chipA", "addr": 32}],
        }

        mc = ModelConfig.from_json(j)
        self.assertEqual(mc.dev_total, 2)
        self.assertIsNotNone(mc.wizc1)
        self.assertIsInstance(mc.i2c_drv, list)
        out = mc.to_dict()
        self.assertEqual(out["devTotal"], 2)
        self.assertIn("wizc1", out)
        self.assertIsInstance(out["i2cDrv"], list)

    def test_user_config_from_json_and_to_dict(self):
        j = {
            "fadeIn": 5,
            "fadeOut": 6,
            "dftDim": 50,
            "opMode": 1,
            "po": True,
            "minDimming": 10,
            "tapSensor": 2,
            "autoUpd": 1,
            "devices": 3,
            "dim2WarmPoints": [100, 200],
            "wizc1": {"mode": [1], "opts": {}},
            "wizc2": {"mode": [], "opts": {}},
            "apStkEn": True,
            "confTs": 123456789,
        }

        uc = UserConfig.from_json(j)
        self.assertEqual(uc.fade_in, 5)
        self.assertEqual(uc.fade_out, 6)
        self.assertEqual(uc.default_dimming, 50)
        self.assertTrue(uc.power_on_state)
        self.assertEqual(uc.dim_to_warm_points, [100, 200])
        od = uc.to_dict()
        self.assertEqual(od["fadeIn"], 5)
        self.assertEqual(od["apStkEn"], True)


class TestPilot(unittest.TestCase):

    def test_pilot_from_json_and_to_dict(self):
        j = {
            "state": True,
            "temp": 3000,
            "r": 255,
            "g": 0,
            "b": 0,
            "dimming": 128,
            "sceneId": 0,
            "speed": 5,
            "rssi": -50,
            "mac": "AA:BB:CC:DD:EE:FF",
        }

        p = Pilot.from_json(j)
        self.assertTrue(p.state)
        self.assertEqual(p.temp, 3000)
        self.assertEqual(p.r, 255)
        self.assertEqual(p.g, 0)
        self.assertEqual(p.b, 0)
        self.assertEqual(p.dimming, 128)
        self.assertEqual(p.sceneId, 0)
        self.assertEqual(p.speed, 5)
        self.assertEqual(p.rssi, -50)
        self.assertEqual(p.mac, "AA:BB:CC:DD:EE:FF")
        d = p.to_dict()
        self.assertEqual(d["state"], True)

    def test_pilot_payload_contains_only_provided_fields(self):
        p = Pilot.from_json({"state": True, "temp": 3000, "rssi": -50, "mac": "AA:BB:CC:DD:EE:FF"})
        payload = p.to_payload()

        self.assertEqual(payload, {"state": True, "temp": 3000})
        self.assertNotIn("rssi", payload)
        self.assertNotIn("mac", payload)

    def test_is_off_and_color_str_behaviour(self):
        p = Pilot()
        # default state is False -> off
        self.assertTrue(p.isOff())
        self.assertEqual(p.color_str(), "off")

        # temperature mode (temp set, RGB zero)
        p.state = True
        p.temp = 3000
        p.r = p.g = p.b = 0
        self.assertEqual(p.color_str(), "temperature (3000K)")

        # RGB color mode: red
        p.temp = 0
        p.r = 255
        p.g = 0
        p.b = 0
        p.dimming = 200
        s = p.color_str()
        self.assertIn("Red", s)
        self.assertIn("rgb(255, 0, 0)", s)

if __name__ == "__main__":
    unittest.main()
