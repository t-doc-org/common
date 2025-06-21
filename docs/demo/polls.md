% Copyright 2024 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Polls

The first {rst:dir}`poll` allows only one answer.

```{poll} aeb57180-a5c8-4532-ad15-94b3dd9f3013
What is the equation of a line in a plane?

- $ax^2 + bx + c = 0$
- $ax + by + cz + d = 0$
- $(x-x_0)^2 + (y-y_0)^2 - r^2 = 0$
- :$ax + by + c = 0$
- $y = at^2 + v_0t + y_0$
- I don't know
```

The next poll allows multiple selections, doesn't number the answers, has no
solutions to show, and auto-closes after 30 seconds.

```{poll} 4a790949-1246-49e8-841e-fb7922b98e45
:mode: multi
:number: none
:close-after: 10s
Which animals do you like?

- Spiders
- Crocodiles
- Dolphins
- Sharks
- Platypuses
- Tasmanian devils
```
