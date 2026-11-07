# Changelog

## Unreleased

- Added `Program` methods to check, add, and remove device IP addresses.
- Adding a new device to an infinite program recalculates its phase shift and reinitializes the program; duplicate addresses are ignored.
- Infinite programs now calculate each device's pilot without sharing step-tracking state between devices.