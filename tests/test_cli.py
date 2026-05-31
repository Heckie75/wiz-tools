import unittest
from unittest.mock import MagicMock, patch

from wiz import Alias, Program, Pilot, WizDeviceCLI, WizDeviceController


class TestWizDeviceCLI(unittest.TestCase):

    def test_parse_programm_command(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        addresses, commands = cli.parse_args([
            "wiz.py",
            "192.168.1.100",
            "--program",
            "interval",
            "10",
        ])

        self.assertEqual(addresses, {"wiz.py", "192.168.1.100"})
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "program")
        self.assertEqual(commands[0]["args"], ["interval", "10"])
        self.assertEqual(commands[0]["params"], ["interval", 600])

    def test_parse_programm_command_with_optional_dimming(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        addresses, commands = cli.parse_args([
            "wiz.py",
            "192.168.1.100",
            "--program",
            "interval",
            "10",
            "80",
        ])

        self.assertEqual(addresses, {"wiz.py", "192.168.1.100"})
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "program")
        self.assertEqual(commands[0]["args"], ["interval", "10", "80"])
        self.assertEqual(commands[0]["params"], ["interval", 600, 80])

    def test_run_program_by_name_with_current_pilot(self):
        controller = WizDeviceController(["192.168.1.100"])
        controller.getPilot = MagicMock(return_value=controller)

        device = controller._get_device_for_ip_address("192.168.1.100")
        device.pilot = Pilot.from_json({"state": True, "r": 0, "g": 0, "b": 0, "dimming": 10})

        with patch.object(controller, "perform", return_value=None) as perform_mock, patch("wiz.time.sleep", return_value=None):
            result = controller.runProgramByName(Program.PROGRAM_DOZE, 3, interval=1)

        self.assertIs(result, controller)
        self.assertGreaterEqual(perform_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
