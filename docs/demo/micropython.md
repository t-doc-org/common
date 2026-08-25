% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# MicroPython

The [`{exec} micropython`](../reference/exec.md#micropython) directive allows
uploading and executing Python code on an embedded system running
[MicroPython](https://micropython.org).

```{defaults} exec
:editor:
:style: max-height: 20rem
```

## Generic

```{exec} micropython
:name: preamble
:when:
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
from time import sleep

display.on()
for name in dir(Image):
  if not name[0].isupper() or name.startswith('ALL_'): continue
  print(name)
  display.show(getattr(Image, name))
  sleep(0.5)
```

## Raspberry Pi Pico

```{exec} micropython
from machine import Pin, unique_id
from neopixel import NeoPixel
from time import sleep

if unique_id() in [b'\xdeb4\x10\x9fr\x0f0']:  # RP2040-One
  led = NeoPixel(Pin.board.GP16, 1)
  for i in range(2 * 256, 2 ** 3 * 2 * 256):
    v = i & 255
    if (i >> 8) & 1: v = 255 - v
    led[0] = (v * ((i >> 10) & 1), v * ((i >> 9) & 1), v * ((i >> 11) & 1))
    led.write()
    sleep(0.002)
  led[0] = (0, 0, 0)
  led.write()

else:  # Generic
  led = Pin("LED", Pin.OUT)
  for i in range(20):
    led.toggle()
    sleep(0.2)
```
