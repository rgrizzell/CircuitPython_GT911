# SPDX-FileCopyrightText: 2023 Robert Grizzell
#
# SPDX-License-Identifier: MIT
"""
`gt911`
================================================================================

CircuitPython Driver for Goodix GT911-based touch screens


* Author(s): Robert Grizzell


"""

from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_struct import ROUnaryStruct

try:
    from busio import I2C
    from digitalio import DigitalInOut
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

    TODO: Device initialization into Normal Mode.
    TODO: Context Manager functionality.
    TODO: Initialize the Reset and Interrupt pins.
    TODO: Translate X,Y based on rotation.
    TODO: Can a COMMAND write be combined with a COMMAND_CHECK write?
    """

    _device_id = ROUnaryStruct(_PRODUCT_ID, "B")

    _reset = RWBit(_COMMAND, 0x02)

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        i2c: I2C,
        device_address: int = None,
        rst_pin: DigitalInOut = None,
        int_pin: DigitalInOut = None,
        rotation: int = 0,
    ):
        if device_address:
            self.i2c_device = i2c_device.I2CDevice(i2c, device_address)
        else:
            try:
                self.i2c_device = i2c_device.I2CDevice(i2c, _SLAVE_ADDRESS2)
            except ValueError:
                self.i2c_device = i2c_device.I2CDevice(i2c, _SLAVE_ADDRESS1)

        if self._device_id != 0x00:
            raise RuntimeError("Failed to find GT911")

        self.rst_pin = rst_pin
        self.int_pin = int_pin
        self._rotation = rotation

        self._last_touch = (None, None)

        self._reset = True

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
