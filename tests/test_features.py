import unittest

from wiz import Features, WizDeviceException


class TestFeatures(unittest.TestCase):

    def test_from_module_name_full_color(self):
        features = Features.fromModuleName("wiz_shrgbc_01")

        self.assertEqual(features.device_type, Features.DEVICE_BULB)
        self.assertTrue(features.color)
        self.assertTrue(features.white)
        self.assertTrue(features.temp)
        self.assertTrue(features.dimming)
        self.assertFalse(features.power_meter)
        self.assertEqual(features.type_key, "SHRGBC")
        self.assertEqual(
            features.getFeaturesDescription(),
            "Full Color Light (RGB + Cold & Warm White) (SHRGBC)"
        )

    def test_from_module_name_color_fixed_white(self):
        features = Features.fromModuleName("wiz_shrgbw_v2")

        self.assertEqual(features.device_type, Features.DEVICE_BULB)
        self.assertTrue(features.color)
        self.assertFalse(features.white)
        self.assertTrue(features.temp)
        self.assertTrue(features.dimming)
        self.assertFalse(features.power_meter)
        self.assertEqual(features.type_key, "SHRGBW")
        self.assertEqual(
            features.getFeaturesDescription(),
            "Color Light (RGB + Dedicated White LED, fixed color temperature) (SHRGBW)"
        )

    def test_from_module_name_strip(self):
        features = Features.fromModuleName("wiz_strip_123")

        self.assertEqual(features.device_type, Features.DEVICE_STRIP)
        self.assertFalse(features.color)
        self.assertFalse(features.white)
        self.assertFalse(features.temp)
        self.assertFalse(features.dimming)
        self.assertFalse(features.power_meter)
        self.assertEqual(features.type_key, "STRIP")
        self.assertEqual(
            features.getFeaturesDescription(),
            "LED Strip Controller (STRIP)"
        )

    def test_from_module_name_invalid_format(self):
        with self.assertRaises(WizDeviceException):
            Features.fromModuleName("shrgbc")

    def test_get_features_description_unknown(self):
        features = Features()
        features.module_name = "wiz_unknown_device"

        self.assertEqual(features.getFeaturesDescription(), "unknown")


if __name__ == "__main__":
    unittest.main()
