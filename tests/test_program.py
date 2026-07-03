import unittest
from unittest.mock import patch

from wiz import Program, Pilot, WizDeviceController

class FakeController(WizDeviceController):

    def __init__(self, ip_addresses):
        super().__init__(ip_addresses)
        self.sent_pilots = []

    def perform(self, timeout: float = 1) -> None:
        if self.commands.get("setPilot") is not None:
            self.sent_pilots.append(self.commands["setPilot"].copy())
        self.resetCommands()

class TestProgram(unittest.TestCase):

    def test_get_current(self):

        program = Program(FakeController(ip_addresses=[]), Program.PROGRAM_INTERVAL, duration=100)
        current, next = program._get_step(0)
        self.assertEqual(current, Program._BEGIN)
        self.assertEqual(next, Program._END)

        current, next = program._get_step(50)
        self.assertEqual(current, Program._BEGIN)
        self.assertEqual(next, Program._END)

        current, next = program._get_step(100)
        self.assertEqual(current, Program._END)
        self.assertEqual(next, None)

    def test_get_pilot_program_on_off(self):

        program = Program(FakeController(ip_addresses=[]), Program.PROGRAM_INTERVAL, duration=100)
        p = program.get_pilot(0)
        self.assertEqual(p.state, True)

        p = program.get_pilot(50)
        self.assertEqual(p.state, True)

        p = program.get_pilot(100)
        self.assertEqual(p.state, False)

    def test_get_pilot_wakeup(self):

        program = Program(FakeController(ip_addresses=[]), Program.PROGRAM_WAKEUP, 60)
        p = program.get_pilot(0)
        self.assertEqual(p.state, False)

        p = program.get_pilot(8)
        self.assertEqual(p.b, 10)

        p = program.get_pilot(16)
        self.assertEqual(p.b, 20)

        p = program.get_pilot(20)
        self.assertEqual(p.g, 30)
        self.assertEqual(p.b, 137)
        self.assertEqual(p.dimming, 40)

        p = program.get_pilot(24)
        self.assertEqual(p.g, 60)
        self.assertEqual(p.b, 255)
        self.assertEqual(p.dimming, 60)

        p = program.get_pilot(40)
        self.assertEqual(p.r, 116)
        self.assertEqual(p.g, 149)
        self.assertEqual(p.b, 255)
        self.assertEqual(p.dimming, 80)

        p = program.get_pilot(59)
        self.assertEqual(p.r, 255)
        self.assertEqual(p.g, 255)
        self.assertEqual(p.b, 255)
        self.assertEqual(p.dimming, 100)

    def test_get_pilot_infinite_applies_phase_shift_per_device(self):

        controller = FakeController(ip_addresses=["192.168.1.100", "192.168.1.101"])
        program = Program(controller, Program.PROGRAM_INFINITE, 360, phase_shift=60)

        first = program.get_pilot(0, device_index=0)
        second = program.get_pilot(0, device_index=1)
        reference = program.get_pilot(60, device_index=0)

        self.assertEqual(first.b, 255)
        self.assertEqual(second.to_dict(), reference.to_dict())

    def test_run_program_sends_new_pilot_only_when_changed(self):

        class FakeController(WizDeviceController):

            def __init__(self, ip_addresses):
                super().__init__(ip_addresses)
                self.sent_pilots = []

            def perform(self, timeout: float = 1) -> None:
                if self.commands.get("setPilot") is not None:
                    self.sent_pilots.append(self.commands["setPilot"].copy())
                self.resetCommands()

        current_pilot = Pilot.from_json({"state": True, "r": 0, "g": 0, "b": 0, "dimming": 10})
        controller = FakeController(["192.168.1.100"])
        program = Program(controller, Program.PROGRAM_DOZE, 3, currentPilot=current_pilot)

        with patch("wiz.time.sleep", return_value=None):
            controller.runProgram(program, interval=1)

        self.assertGreaterEqual(len(controller.sent_pilots), 2)
        self.assertEqual(controller.sent_pilots[0]["state"], True)
        self.assertEqual(controller.sent_pilots[-1]["state"], False)

    def test_run_program_sends_final_step_on_keyboard_interrupt(self):

        controller = FakeController(["192.168.1.100"])
        program = Program(controller, Program.PROGRAM_INTERVAL, 60)

        with patch("wiz.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                controller.runProgram(program, interval=1)

        self.assertGreaterEqual(len(controller.sent_pilots), 2)
        self.assertEqual(controller.sent_pilots[-1], {"state": False})


if __name__ == "__main__":
    unittest.main()
