% Copyright 2025 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Pygame

```{metadata}
exec:
  python:
    packages: [numpy, pygame-ce]
    files:
      basket.png:
      pineapple.png:
versions:
  pyodide: 0.27.7
```

[`pygame-ce`](https://github.com/pygame-community/pygame-ce) can be used in
[`{exec} python`](../../reference/exec.md#python) blocks by listing it in the
[`exec:python:packages:`](../../reference/exec.md#python) {rst:dir}`metadata`.

```
exec:
  python:
    packages: [pygame-ce]
```

```{important}
Code using Pygame must run in the `main` environment.
```

````{warning}
`pygame-ce` is broken in recent Pyodide versions (0.28.*). Specify an earlier
version (e.g. 0.27.7) via the `versions:pyodide:` {rst:dir}`metadata`.

```
versions:
  pyodide: 0.27.7
```
````

````{tip}
Pygame grabs the keyboard in `pygame.init()`, and releases it in
`pygame.quit()`. If the program exits without calling the latter, the page will
not respond to keyboard input anymore (e.g. typing in an editor won't have any
effect). It is useful to have a code block like the following on the page, to
force releasing the keyboard if this happens.

```{exec} python main
import pygame; pygame.quit()
```
````

```{exec} python
:name: setup
:when: never
:class: hidden
import io
with redirect(stdout=io.StringIO()):
    import tdoc.pygame
setup_canvas()
```

```{defaults} exec
:editor:
:after: setup
:style: max-height: 25rem;
```

## Changes required

Pygame programs require a few minor adjustments to run in the browser.

- The rendering canvas must be created prior to setting the display mode by
  calling {py:func}`~tdoc.core.setup_canvas`.
- Calls to `pygame.time` functions, including `Clock` methods, must be replaced
  with asynchronous calls to subtitutes. This requires the main loop to be made
  asynchronous as well.
- Calls to `pygame.event.wait()` must be replaced with a loop calling
  `pygame.event.poll()` and sleeping asynchronously while no event is available.

| Pygame                     | Replacement                                        |
|----------------------------|----------------------------------------------------|
| `pygame.time.get_ticks()`  | {py:func}`~tdoc.core.animation_time()`             |
| `pygame.time.Clock.tick()` | {py:func}`~tdoc.core.animation_frame()`            |
| `pygame.time.wait()`       | {py:func}`asyncio.sleep()`                         |
| `pygame.event.wait()`      | `pygame.event.poll()` + {py:func}`asyncio.sleep()` |

The program below is a slightly modified version of the `pygame.examples.liquid`
example distributed with Pygame, converted to an asynchronous main loop. Press
{kbd}`Esc` or click the left mouse button to terminate.

```{exec} python main
import pygame
import math
import pathlib

examples = pathlib.Path(pygame.__file__).parent / "examples"

async def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480), pygame.DOUBLEBUF)

    bitmap = pygame.image.load(examples / "data" / "liquid.bmp")
    bitmap = pygame.transform.scale2x(bitmap)
    bitmap = pygame.transform.scale2x(bitmap)

    if screen.get_bitsize() == 8:
        screen.set_palette(bitmap.get_palette())
    else:
        bitmap = bitmap.convert()

    xblocks = range(0, 640, 20)
    yblocks = range(0, 480, 20)
    running = True
    t = animation_time() / 1000
    while running:
        for e in pygame.event.get():
            if (e.type == pygame.MOUSEBUTTONDOWN
                    or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE)):
                running = False

        for x in xblocks:
            xpos = (x + (math.sin(t + x * 0.01) * 15)) + 20
            for y in yblocks:
                ypos = (y + (math.sin(t + y * 0.01) * 15)) + 20
                screen.blit(bitmap, (x, y), (xpos, ypos, 20, 20))

        t = await animation_frame() / 1000
        pygame.display.flip()

try:
    await main()
finally:
    pygame.quit()
```

## Using resource files

The example below demonstrates loading resources from files specified in the
[`exec:python:files:`](../../reference/exec.md#python) {rst:dir}`metadata`.
Press {kbd}`Esc` to terminate the program.

```{exec} python main
import pygame
from random import randint

width, height = 600, 600

async def main():
    pygame.init()
    window = pygame.display.set_mode((width, height))

    class Sprite(pygame.sprite.Sprite):
        def __init__(self, cx, cy):
            super().__init__()
            self.rect = self.image.get_rect()
            self.rect.centerx, self.rect.centery = cx, cy

    class Pineapple(Sprite):
        image = pygame.image.load("pineapple.png").convert_alpha()

    class Basket(Sprite):
        image = pygame.image.load("basket.png").convert_alpha()

    class Text(pygame.sprite.Sprite):
        font = pygame.font.Font(None, 36)

        def __init__(self, cx, cy, *args):
            super().__init__()
            self.image = self.font.render(*args)
            self.rect = self.image.get_rect()
            self.rect.centerx, self.rect.centery = cx, cy

    pineapples = pygame.sprite.LayeredUpdates()
    sprites = pygame.sprite.LayeredUpdates()
    basket = Basket(width / 2, height - Basket.image.get_rect().height / 2)
    sprites.add(basket)

    game_over = False
    score = 0
    running = True
    while running:
        await animation_frame()
        pygame.display.flip()

        window.fill((36, 242, 232))
        pineapples.draw(window)
        sprites.draw(window)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEMOTION:
                basket.rect.centerx = event.pos[0]

        if game_over: continue
        if randint(0, 60) == 0:
            pineapple = Pineapple(randint(0, width - 1),
                                  -Pineapple.image.get_rect().height / 2)
            pineapples.add(pineapple)
        for pineapple in pineapples.sprites():
            pineapple.rect.y += 5
            if pineapple.rect.colliderect(basket):
                score += 1
                pineapple.kill()
            if pineapple.rect.y > height:
                game_over = True
                sprites.add(Text(
                    window.get_rect().centerx, window.get_rect().centery,
                    f"Game over. Score: {score}", True, (10, 10, 10),
                    (255, 90, 20)))

try:
    await main()
finally:
    pygame.quit()
```

## Examples distributed with Pygame

Some of the examples distributed with `pygame-ce` can be run unchanged by
monkey-patching the functionality of Pygame related to time. This only works on
[Chromium-based browsers](#run-sync).

```{note}
The examples cannot be interrupted via the
<button class="tdoc fa-stop"></button> button. If a program doesn't terminate,
reload the page.
```

### Aliens

Move the vehicle left and right with the cursor keys, and fire with
{kbd}`Space`. Terminate the program with {kbd}`Esc`.

```{exec} python main
import pygame
try:
    from pygame.examples.aliens import main
    main()
finally:
    pygame.quit()
```

### Events and inputs

Terminate the program with {kbd}`Esc`.

```{exec} python main
:console-style: max-height: 25rem;
import pygame
try:
    from pygame.examples.eventlist import main
    main()
except SystemExit:
    pass
finally:
    pygame.quit()
```
