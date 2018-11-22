import evdev
from evdev import InputDevice, categorize, ecodes
print("Start")
print(evdev.list_devices())

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(device.path, device.name, device.phys)
    print(device.leds(verbose=True))