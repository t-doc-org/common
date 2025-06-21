% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# MicroPython

The [`{exec} micropython`](../reference/exec.md#micropython) directive allows
uploading and executing Python code on an embedded system running
[MicroPython](https://micropython.org).

```{defaults} exec
:editor:
:style: max-height: 20rem
:output-style: max-height: 20rem
```

## Generic

```{exec} micropython
:name: preamble
:when: never
print("(This line is printed from the preamble.)")
```

```{exec} micropython
:after: preamble
name = input("What's your name? ")
print("Hello, %s!" % name)
```

## BBC micro:bit V2

```{exec} micropython
from microbit import *
import time

display.on()
for name in dir(Image):
  if not name[0].isupper() or name.startswith('ALL_'): continue
  print(name)
  display.show(getattr(Image, name))
  time.sleep(0.5)
```

## Raspberry Pi Pico

```{exec} micropython
from machine import Pin
import time

led = Pin("LED", Pin.OUT)

for i in range(10):
  led.toggle()
  time.sleep(0.4)
```
