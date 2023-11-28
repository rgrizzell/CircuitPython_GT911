# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: MIT
"""
`gt911`
================================================================================

CircuitPython Driver for Goodix GT911-based touch screens


* Author(s): Robert Grizzell

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
from adafruit_bus_device import i2c_device

try:
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/rgrizzell/CircuitPython_GT911.git"

_SLAVE_ADDRESS1 = const(0x5D)
_SLAVE_ADDRESS2 = const(0x14)

_COMMAND = const(0x8040)
_COMMAND_CHECK = const(0x8046)
_PRODUCT_ID = const(0x8140)
_POINT_INFO = const(0x814E)
_POINT_1 = const(0x814F)
_POINT_2 = const(0x8157)
_POINT_3 = const(0x815F)
_POINT_4 = const(0x8167)
_POINT_5 = const(0x816F)
_points = (_POINT_1, _POINT_2, _POINT_3, _POINT_4, _POINT_5)


class GT911:
    """GT911 chip go brrr

    TODO: Context Manager functionality.
    TODO: Translate X,Y based on rotation.
    TODO: Can a COMMAND write be combined with a COMMAND_CHECK write?
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        i2c: I2C,
        rst_pin: digitalio.DigitalInOut = None,
        int_pin: digitalio.DigitalInOut = None,
        int_high: bool = False,
        rotation: int = 0,
    ):
        self.rst_pin = rst_pin
        self.int_pin = int_pin
        self.int_high = int_high
        self._rotation = rotation
        self._last_touch = (None, None)

        # Reset and Interrupt pins are optional, but can be used to
        # reset the device into a different I2C configuration.
        if self.rst_pin:
            self._reset_device()
        elif self.int_pin:
            # Listen for interrupts
            self.int_pin.switch_to_input()

        if self.rst_pin and self.int_pin and self.int_high:
            self._i2c_addr = _SLAVE_ADDRESS2
        else:
            self._i2c_addr = _SLAVE_ADDRESS1

        self.i2c_device = i2c_device.I2CDevice(i2c, self._i2c_addr)
        if self._read_register(_PRODUCT_ID, 3) != "911":
            raise RuntimeError("Failed to find GT911")
        # Device initialized

    # pylint: enable=too-many-arguments

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deinit()

    def deinit(self):
        """De-initializes the driver and releases the hardware."""

    @property
    def last_touch(self):
        """Get the coordinates of the last touch.
        TODO: Check if touch buffer ready, else return last touch.
        """
        self._last_touch = (0, 0)

        # i2c: read 0x814E
        # bit 0-3: touch points
        # bit 4: have touch key (1 = pressed, 0 = released)?
        # bit 5: proximity valid?
        # bit 6: large detect?
        # bit 7: buffer status (1 = data, 0 = empty)

        # i2c: write 0x814E
        # bit 7: set to 0
        return self._last_touch

    def _reset_device(self):
        """If the reset pin is defined, the device can be reset. If the interrupt pin is also
         defined, the device can be reset into a specific I2C address configuration.

        This code is untested. Test hardware did not wire RESET to GPIO.
        """
        if not self.rst_pin:
            raise RuntimeError("RESET pin must be configured to reset device.")

        self.rst_pin.switch_to_output(True)  # Switch pin to output
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

    def _read_register(self, register: int, register_width: int = 1):
        reg = bytearray(2)
        reg[0] = register >> 8
        reg[1] = register & 0xFF
        data = bytearray(register_width)
        with self.i2c_device as i:
            i.write_then_readinto(reg, data)
        return data
