#!/usr/bin/python3

import argparse
import logging as log
from select import select

from evdev import InputDevice, UInput, UInputError


# configuration for Saitek Cyborg 3D Gold
MOVED_EVENT = 3
MAP_EVENT_CODE_TO_AXIS_IDX = {
    0: 0,   # left-right
    1: 1,   # back-front
    5: 2,   # rotate left-right
    6: 3,   # throttle back-front
    16: 4,  # small-thumb-thing left-right
    17: 5   # small-thumb-thing back-front
}


class Calibration(object):
    def __init__(self, a, b, c, d):
        # example: my joystick goes from 32 (max left) to 150 (max right). Deadzone center is 90-91.
        # a is deadzone center left
        # b is deadzone center right
        # c is multiplier for left side
        # d is multiplier for right side
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def apply(self, real_pos):
        # y = sign*multiplier(deadzone-real_pos)
        x = real_pos
        y = 0
        if x < self.a:
            y = -self.c * (self.a - x) / 16384
        elif x > self.b:
            y = self.d * (x - self.b) / 16384

        # Not sure where this comes from... but it makes sdl2-jstest and in-game
        # movement sane.
        y /= 256
        y += 128
        return round(y)

    def __str__(self):
        return "a: {}, b: {}, c: {}, d: {}". format(self.a, self.b, self.c, self.d)


def parse_params():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--input_dev', type=str, default='/dev/input/event28',
                        help='input event device')
    parser.add_argument('--calib_file', type=str, default='cal.txt',
                        help='jcal calibration file')
    parser.add_argument('--verbose', action='store_true',
                        help='print verbose debugging output')
    parser.add_argument('--filter_evcode', type=int, default=-1,
                        help='prints events only for speficic evcode')
    parser.add_argument('--dry_run', action='store_true',
                        help='do not apply calibration, just pass through')
    args = parser.parse_args()
    return args


def setup_logging(is_verbose):
    if is_verbose:
        log.basicConfig(level=log.DEBUG)
    else:
        log.basicConfig(level=log.INFO)


def load_calibrations(calib_path):
    calibrations = {}
    with open(calib_path, "r") as f:
        line = f.readline()
        # e.g.
        # jscal -s 6,1,1,90,90,9418500,8947575,1,1,90,91,-8947575,-8521500,1,0,83,84,9099229,7669350,1,0,90,90,-7254791,-7456313,1,0,0,0,-2147483648,-2147483648,1,0,0,0,-536854528,-536854528 /dev/input/js0
        _, _, lotsa_numbers, _ = line.split(" ")
        calibs = lotsa_numbers.split(",")

        num_axis = int(calibs[0])

        current_axis = 0
        for i in range(1, len(calibs), 6):
            _, _, a, b, c, d = map(int, calibs[i:i+6])
            calibrations[current_axis] = Calibration(a, b, c, d)
            current_axis += 1

        assert(len(calibrations) == num_axis)

        log.info("Loaded calibration for axis:")
        for i in range(num_axis):
            log.info("- axis {}: {}".format(i, calibrations[i]))
    return calibrations


def setup_devices(original_path):
    raw = InputDevice(original_path)
    target_dev = '/dev/uinput'
    try:
        fixed = UInput.from_device(raw, devnode=target_dev, name="Calibrated {}".format(raw.name))
    except UInputError as e:
        raise PermissionError("You should run this command as root") from e
    log.info("Redirecting fixed stream to {}".format(target_dev))
    return raw, fixed


def write_event(device, event):
    device.write_event(event)
    device.syn()


def redirect(from_dev, to_dev, calib, dry_run, filter_evcode):
    while True:
        r, _, _ = select([from_dev], [], [])
        for event in from_dev.read():
            if event.type != MOVED_EVENT:
                write_event(to_dev, event)
                continue

            axis = MAP_EVENT_CODE_TO_AXIS_IDX[event.code]
            old_val = event.value
            new_val = calib[axis].apply(old_val) if not dry_run else old_val

            if filter_evcode == -1 or event.code == filter_evcode:
                log.debug('{}\t-> Adjusted value: {}'.format(event, new_val))

            event.value = new_val
            write_event(to_dev, event)


def main():
    args = parse_params()
    setup_logging(args.verbose)
    calib = load_calibrations(args.calib_file)
    from_dev, to_dev = setup_devices(args.input_dev)
    redirect(from_dev, to_dev, calib, args.dry_run, args.filter_evcode)


if __name__ == "__main__":
    main()
