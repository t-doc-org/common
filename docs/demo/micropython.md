% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# MicroPython

```{admonition} Work-in-progress
:class: warning
This functionality is in development and unstable. Please do not use yet.
```

The {rst:dir}`{exec} micropython <exec>` directive allows uploading and
executing Python code on an embedded system running MicroPython.

```{exec} micropython
:editor:
:output-style: max-height: 20rem
from machine import Pin
import time

led = Pin("LED", Pin.OUT)

while True:
    led.toggle()
    time.sleep(0.4)
```

## Multiple editors

```{exec} micropython
:editor:
:output-style: max-height: 20rem
from machine import Pin
import time

led = Pin("LED", Pin.OUT)

while True:
    led.toggle()
    time.sleep(0.2)
```
