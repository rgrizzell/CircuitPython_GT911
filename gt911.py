# SPDX-FileCopyrightText: 2017 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: MIT

"""
`gt911`
====================================================

CircuitPython Driver for Goodix GT911-based touch screens

* Author(s): ladyada, retiredwizard, Robert Grizzell

Implementation Notes
--------------------

**Hardware:**

* `Product Page <https://www.goodix.com/en/product/touch/touch_screen_controller>`_
* `GT911 Datasheet
 <https://www.lcd-module.de/fileadmin/eng/pdf/zubehoer/GT911%20Programming%20Guide_20140804_Rev00.pdf>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""
import time
import digitalio
from micropython import const
from adafruit_bus_device.i2c_device import I2CDevice

try:
    from busio import I2C
    from circuitpython_typing import ReadableBuffer
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/rgrizzell/CircuitPython_GT911.git"

_GT_DEFAULT_I2C_ADDR = 0x5D
_GT_SECONDARY_I2C_ADDR = 0x14

_GT_COMMAND = const(0x8040)
_GT_COMMAND_CHECK = const(0x8046)

_GT_REG_STATUS = const(0x814E)
_GT_POINT1_COORD = const(0x814F)
_GT_POINT2_COORD = const(0x8157)
_GT_POINT3_COORD = const(0x815F)
_GT_POINT4_COORD = const(0x8167)
_GT_POINT5_COORD = const(0x816F)
_GT_REG_PRODID_1 = const(0x8140)
_GT_REG_PRODID_2 = const(0x8141)
_GT_REG_PRODID_3 = const(0x8142)
_GT_REG_PRODID_4 = const(0x8143)
_GT_REG_FIRMVERSH = const(0x8145)
_GT_REG_FIRMVERSL = const(0x8144)
_GT_REG_VENDID = const(0x814A)

_GT_PANEL_BITFREQH = const(0x8068)
_GT_PANEL_BITFREQL = const(0x8067)
_GT_SCREEN_TOUCH_LVL = const(0x8053)

_GT_TOUCH_NO = const(0x804C)
_GT_X_THRESHOLD = const(0x8057)
_GT_Y_THRESHOLD = const(0x8058)


class GT911:
    """A driver for the GT911 capacitive touch sensor.

    :param i2c: The object representing the I2C interface used to communicate with the touchscreen.
    :type i2c: I2C
    :param rst_pin: The object representing the RESET pin.
    :type rst_pin: DigitalInOut
    :param int_pin: The object representing the INTERRUPT/IRQ pin.
    :type int_pin: DigitalInOut
    :param debug: Enables debug output.
    :type debug: bool
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        i2c: I2C,
        rst_pin: digitalio.DigitalInOut = None,
        int_pin: digitalio.DigitalInOut = None,
        int_high: bool = False,
        rotation: int = 0,
        debug: bool = False,
    ):
        self.rst_pin = rst_pin
        self.int_pin = int_pin
        self.int_high = int_high
        self._rotation = rotation
        self._debug = debug

        # Reset and Interrupt pins are optional, but together they can be used to
        # reset the device into a different I2C configuration.
        if self.rst_pin:
            self._reset_device()
        elif self.int_pin:
            # Listen for interrupts
            self.int_pin.switch_to_input()

        if self.rst_pin and self.int_pin and self.int_high:
            self._i2c_addr = _GT_DEFAULT_I2C_ADDR
        else:
            self._i2c_addr = _GT_SECONDARY_I2C_ADDR

        self.i2c_device = I2CDevice(i2c, self._i2c_addr)
        # Device initialized
        if self._debug:
            print("address:", self._i2c_addr)
            for key, value in self._device_info().items():
                print(f"{key}: {value}")

        self._last_touch = self._read_last_touch()
        self._write(_GT_COMMAND, [0])  # Read coordinates status

    @property
    def touched(self) -> bool:
        """Check to see if a new touch occurred.

        :return: True if new touch is registered, False if not.
        :rtype: bool
        """
        curr_touch = self._read_last_touch()
        if self._last_touch != curr_touch:
            self._last_touch = curr_touch
            """
            If this extra call to _read_last_touch()
            isn't made then the next touch is missed ?????
            I have no idea why
            """
            self._read_last_touch()
            return True
        return False

    @property
    def touches(self) -> list[dict]:
        """Get the touches from the device.

        :return: List of touch points containing an ID and coordinates.
        :rtype: list[dict]
        """
        touch_points = []
        data = self._last_touch
        touch_count = 1
        if self._debug:
            print(f"touches: {touch_count}")

        for _ in range(touch_count):
            touch_id = data[0]

            x = data[2] * 256 + data[1]
            y = data[4] * 256 + data[3]

            point = {"id": touch_id, "x": x, "y": y}
            if self._debug:
                print(f"id={touch_id} x={x} y={y}")
            touch_points.append(point)
        return touch_points

    def _read_last_touch(self) -> list[int]:
        self._write(_GT_REG_STATUS, [0])
        test = self._read(_GT_REG_STATUS, 1)[0]
        timeout = 250
        while not (test & 0x80) and (timeout := timeout - 1) > 0:
            if test == 0:
                break
            time.sleep(0.001)
            self._write(_GT_REG_STATUS, [0])
            test = self._read(_GT_REG_STATUS, 1)[0]
        self._write(_GT_REG_STATUS, [0])

        return list(self._read(_GT_POINT1_COORD, 7))

    def _reset_device(self) -> None:
        """If the reset pin is defined, the device can be reset. If the interrupt pin is also
        defined, device can be reset into a specific I2C address configuration.
        """
        if not self.rst_pin:
            raise RuntimeError("RESET pin must be configured to reset device.")

        self.rst_pin.switch_to_output(True)  # Switch pin to output, high
        if self.int_pin:
            self.rst_pin.switch_to_output(False)  # Switch pin to output, low
            time.sleep(0.005)  # Wait >5ms

        self.rst_pin.value = False  # Stop the device
        time.sleep(0.01)  # Wait >10ms

        # Interrupt pin modifies I2C addressing (High: 0x14 | Low: 0x5D)
        if self.int_pin:
            # Set interrupt pin value in Open Drain mode.
            self.int_pin.switch_to_output(
                self.int_high, drive_mode=digitalio.DriveMode.OPEN_DRAIN
            )
            time.sleep(0.0001)  # Wait >10μs

        self.rst_pin.value = True  # Start the device
        if self.int_pin:
            time.sleep(0.005)  # Wait >5ms
            self.int_pin.switch_to_input()  # Listen for interrupts

    def _read(self, register: int, length: int) -> bytearray:
        payload = bytes([((register & 0xFF00) >> 8), (register & 0xFF)])
        result = bytearray(length)

        if self.int_pin:
            while self.int_pin.value:
                pass

        with self.i2c_device as i2c:
            i2c.write_then_readinto(payload, result)

        if self._debug:
            print("\t$%02X => %s" % (register, [hex(i) for i in result]))
        return result

    def _write(self, register: int, values: ReadableBuffer) -> None:
        values = [((register & 0xFF00) >> 8), (register & 0xFF)] + [
            (v & 0xFF) for v in values
        ]

        with self.i2c_device as i2c:
            i2c.write(bytes(values))

        if self._debug:
            print("\t$%02X <= %s" % (values[0], [hex(i) for i in values[1:]]))

    def _device_info(self):
        chip_id = chr(self._read(_GT_REG_PRODID_1, 1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_2, 1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_3, 1)[0])
        chip_id += chr(self._read(_GT_REG_PRODID_4, 1)[0])
        firm_id = self._read(_GT_REG_FIRMVERSH, 1)[0]
        firm_id = (firm_id << 8) | self._read(_GT_REG_FIRMVERSL, 1)[0]
        vend_id = self._read(_GT_REG_VENDID, 1)[0]
        num_touch = self._read(_GT_TOUCH_NO, 1)[0] * 0x0F
        x_thresh = self._read(_GT_X_THRESHOLD, 1)[0]
        y_thresh = self._read(_GT_Y_THRESHOLD, 1)[0]
        thresh_lvl = self._read(_GT_SCREEN_TOUCH_LVL, 1)[0]
        frequency = (self._read(_GT_PANEL_BITFREQH, 1)[0] << 8) | self._read(
            _GT_PANEL_BITFREQL, 1
        )[0]

        return {
            "chip_id": f"{chip_id:4}",
            "firm_id": f"{firm_id:02X}",
            "vend_id": f"{vend_id:02X}",
            "touch_points": num_touch,
            "thresholds": (x_thresh, y_thresh),
            "threshold_level": thresh_lvl,
            "frequency_hz": frequency,
        }
