import colorsys
import os
import sys
import time
from collections import defaultdict
from queue import deque


THERMAL_PATH = '/sys/devices/virtual/thermal'
FAN_PWM_TARGET_PATH = '/sys/devices/pwm-fan/target_pwm'

# Min / max temperatures for the color scale
MIN_TEMP = 10
MAX_TEMP = 85

# Minimum temperature to start the fan
MIN_FAN_TEMP = int(os.environ.get('FAN_CONTROL_MIN_TEMP', 50))

# Temperature at which fan runs at full speed
MAX_FAN_TEMP = int(os.environ.get('FAN_CONTROL_MAX_TEMP', 70))

# Zone 4 seems to be stuck to 100
EXCLUDE_ZONES = set(os.environ.get(
    'FAN_CONTROL_EXCLUDE_ZONES',
    'thermal_zone4').split())

HISTORY_SIZE = int(os.environ.get('FAN_CONTROL_HISTORY_SIZE', 60))

VERBOSE = sys.stdout.isatty()


class ColorScale:

    def __init__(self, min_value, max_value):

        self.min_hue = 2 / 3  # Blue
        self.max_hue = 0  # Red
        self._hue_range = self.max_hue - self.min_hue

        self.min_value = min_value
        self.max_value = max_value
        self._value_range = self.max_value - self.min_value

    def get_hue(self, value):
        value = max(self.min_value, min(value, self.max_value))
        value_ratio = (value - self.min_value) / self._value_range
        return self.min_hue + (self._hue_range * value_ratio)

    def get_term_color(self, value, lum=.5, sat=1):
        hue = self.get_hue(value)
        r, g, b = colorsys.hls_to_rgb(hue, lum, sat)
        return ('8;2;{};{};{}'
                .format(int(r * 255), int(g * 255), int(b * 255)))


def get_temperatures():
    data = {}
    for name in os.listdir(THERMAL_PATH):
        if name.startswith('thermal_zone'):
            data[name] = get_temperature(name)
    return data


def get_temperature(zone_name, max_retries=3):
    for x in range(max_retries):
        try:
            with open(os.path.join(THERMAL_PATH, zone_name, 'temp')) as fp:
                raw_value = fp.read().strip()
                return int(raw_value) / 1000
        except TimeoutError:
            if x >= (max_retries - 1):
                # This was last attempt
                raise


def get_max_temp(temps, exclude=[]):
    return max(
        value for key, value in temps.items()
        if key not in exclude)


def get_fan_speed(temp, fan_min_temp=MIN_FAN_TEMP, fan_full_temp=MAX_FAN_TEMP):
    if temp < fan_min_temp:
        return 0
    if temp >= fan_full_temp:
        return 255
    _temp_range = fan_full_temp - fan_min_temp
    return int(255 * (temp - fan_min_temp) / _temp_range)


def set_fan_speed(new_speed):
    """
    Args:
        speed: integer from 0 to 255
    """
    with open(FAN_PWM_TARGET_PATH, 'w') as fp:
        fp.write(str(new_speed))


def main():
    colors = ColorScale(MIN_TEMP, MAX_TEMP)
    history = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))

    def reset_screen():
        print('\x1b[2J\x1b[H', end='')  # Clear screen, move to 0,0

    def print_header():
        print(' Jetson Nano temperature monitor '.center(80, '='))
        print()

    def print_zone_status():
        for zone_name, temp in sorted(temps.items()):
            print('{zone} \x1b[3{color}m{temp:>5}\x1b[0m '
                  .format(zone=zone_name,
                          color=colors.get_term_color(temp),
                          temp=temp),
                  end='')
            for item in history[zone_name]:
                color = colors.get_term_color(item)
                print('\x1b[4{}m \x1b[0m'.format(color), end='')
            print()
        print()

    while True:

        temps = get_temperatures()

        if VERBOSE:
            # We only need to keep history if running in verbose mode
            for key, val in temps.items():
                history[key].append(val)

        if VERBOSE:
            reset_screen()
            print_header()
            print_zone_status()

        max_temp = get_max_temp(temps, exclude=EXCLUDE_ZONES)
        fan_speed = get_fan_speed(max_temp)

        if VERBOSE:
            print('>>> Max temp: \x1b[3{temp_color}m{max_temp}\x1b[0m °C\n'
                  '>>> Fan speed: {fan_percent:.0f}% ({fan_speed})\n'
                  .format(max_temp=max_temp,
                          temp_color=colors.get_term_color(max_temp),
                          fan_percent=fan_speed * 100 / 255,
                          fan_speed=fan_speed))
        else:
            # Summary, can be sent to a log file
            print('temperature={} fan_speed={}'
                  .format(max_temp, fan_speed),
                  flush=True)

        set_fan_speed(fan_speed)

        time.sleep(1)


if __name__ == '__main__':
    main()
