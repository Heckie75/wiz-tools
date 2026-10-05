import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from wiz import Alias, Pilot, Program, WizDevice, WizDeviceCLI, WizDeviceController, WizDeviceException


class TestWizDeviceCLI(unittest.TestCase):

    def test_status_print_includes_cold_and_warm_white_levels(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = None
        device = WizDevice("192.168.178.47").withPilot(Pilot.from_json({
            "state": True, "c": 0, "w": 255, "dimming": 100, "rssi": -60,
        }))
        output = io.StringIO()

        with redirect_stdout(output):
            cli.printDevice(device)

        self.assertIn("Cold white (c):      0/255", output.getvalue())
        self.assertIn("Warm white (w):      255/255", output.getvalue())

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

    def test_parse_programm_command_with_optional_phase_shift(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        addresses, commands = cli.parse_args([
            "wiz.py",
            "192.168.1.100",
            "--program",
            "infinite",
            "10",
            "80",
            "30",
        ])

        self.assertEqual(addresses, {"wiz.py", "192.168.1.100"})
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "program")
        self.assertEqual(commands[0]["args"], ["infinite", "10", "80", "30"])
        self.assertEqual(commands[0]["params"], ["infinite", 600, 80, 30])

    def test_parse_program_command_with_automatic_phase_shift(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        addresses, commands = cli.parse_args([
            "wiz.py",
            "192.168.1.100",
            "192.168.1.101",
            "--program",
            "infinite",
            "10",
            "80",
            "auto",
        ])

        self.assertEqual(addresses, {"wiz.py", "192.168.1.100", "192.168.1.101"})
        self.assertEqual(commands[0]["params"], ["infinite", 600, 80, "auto"])
        self.assertEqual(commands[0]["params"], ["infinite", 600, 80, "auto"])
    def test_parse_and_combine_color_and_white_commands(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()
        controller = WizDeviceController(["192.168.1.100"])

        addresses, commands = cli.parse_args([
            "192.168.1.100",
            "--color",
            "255",
            "0",
            "59",
            "--white",
            "255",
            "0",
        ])

        for command in commands:
            WizDeviceCLI.COMMANDS[command["command"]]["action"](
                controller, command["params"])

        self.assertEqual(addresses, {"192.168.1.100"})
        self.assertEqual(controller.commands["setPilot"], {
            "r": 255, "g": 0, "b": 59, "w": 0, "c": 255,
        })

    def test_color_command_rejects_a_fourth_channel(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        with self.assertRaises(WizDeviceException):
            cli.parse_args([
                "192.168.1.100", "--color", "255", "0", "59", "1",
            ])

    def test_color_command_sets_only_rgb_channels(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()
        controller = WizDeviceController(["192.168.1.100"])

        _, commands = cli.parse_args([
            "192.168.1.100", "--color", "255", "0", "59",
        ])
        WizDeviceCLI.COMMANDS[commands[0]["command"]]["action"](
            controller, commands[0]["params"])

        self.assertEqual(controller.commands["setPilot"], {
            "r": 255, "g": 0, "b": 59,
        })

    def test_parse_white_command_accepts_channel_boundaries(self):
        cli = WizDeviceCLI.__new__(WizDeviceCLI)
        cli.alias = Alias()

        _, commands = cli.parse_args([
            "192.168.1.100", "--white", "0", "255",
        ])

        self.assertEqual(commands[0]["params"], [0, 255])

        with self.assertRaises(WizDeviceException):
            cli.parse_args(["192.168.1.100", "--white", "256", "0"])

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
