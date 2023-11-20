# SPDX-FileCopyrightText: 2023 Robert Grizzell
#
# SPDX-License-Identifier: MIT

import time
import board
import gt911

i2c = board.I2C()
gt = gt911.GT911(i2c)

while True:
    print(gt.last_touch)
    time.sleep(1)
