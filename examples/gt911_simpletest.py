# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: Unlicense

import time
import board
import gt911

i2c = board.I2C()
gt = gt911.GT911(i2c)

while True:
    for i, touch in enumerate(gt.touches):
        x, y, a = touch
        print(f"[{i+1}]({x},{y}) size:{a}")
    time.sleep(1)
