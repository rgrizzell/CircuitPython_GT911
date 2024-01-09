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

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""
import struct
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
_GT_POINT_STATUS = const(0x814E)
_GT_POINT_START = const(0x814F)


class GT911:
    """A driver for the GT911 capacitive touch sensor.

    :param i2c: The object representing the I2C interface used to communicate with the touchscreen.
    :type i2c: I2C
    :param rst_pin: The object representing the RESET pin.
    :type rst_pin: DigitalInOut
    :param int_pin: The object representing the INTERRUPT/IRQ pin.
    :type int_pin: DigitalInOut
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        i2c: I2C,
        rst_pin: digitalio.DigitalInOut = None,
        int_pin: digitalio.DigitalInOut = None,
        int_high: bool = False,
    ):
        self.rst_pin = rst_pin
        self.int_pin = int_pin
        self.int_high = int_high
        self._touch_data = [tuple()] * 5

        # Reset and Interrupt pins are optional, but together they can be used to
        # reset the device into a different I2C configuration.
        if self.rst_pin:
            self._reset()
        elif self.int_pin:
            # Listen for interrupts
            self.int_pin.switch_to_input()
        if self.rst_pin and self.int_pin and self.int_high:
            self._i2c_addr = _GT_DEFAULT_I2C_ADDR
        else:
            self._i2c_addr = _GT_SECONDARY_I2C_ADDR

        self.i2c_device = I2CDevice(i2c, self._i2c_addr)
        self._write(_GT_COMMAND, [0])  # Set mode: Read coordinates

    @property
    def touches(self) -> list[tuple]:
        """Get the touches from the device.

        :return: List of touch points containing coordinates and size.
        :rtype: list[tuple]
        """
        num_touch_points = 0
        touch_status = self._read(_GT_POINT_STATUS, 1)[0]
        if touch_status & 0x80:  # if bit7 == 1
            num_touch_points = touch_status & 0x0F  # get bit0
            for i in range(0, num_touch_points):
                # Read the touch point, 8 bytes in total.
                data = self._read(_GT_POINT_START + i * 8, 8)
                # Unpack the touch data.
                self._touch_data[i] = struct.unpack("hhh", data[1:7])
        # Reset the buffer for the next series of touches.
        self._write(_GT_POINT_STATUS, [0])

        return self._touch_data[0:num_touch_points]

    def _reset(self) -> None:
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
        payload = bytes([register >> 8, register & 0xFF])
        result = bytearray(length)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(payload, result)

        return result

    def _write(self, register: int, values: ReadableBuffer) -> None:
        payload = bytearray([register >> 8, register & 0xFF])
        payload[2:] = bytes(
            [(v & 0xFF) for v in values]
        )  # Ensure each value does not exceed 1 byte.
        with self.i2c_device as i2c:
            i2c.write(bytes(payload))
