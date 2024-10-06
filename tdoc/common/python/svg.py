# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

# TODO: Escape content during interpolation
# TODO: Make use of Group
# TODO: Add <style> element
# TODO: Make the output width accessible; maybe return it from render()

class AttributesMeta(type):
    def __call__(cls, *args, **kwargs):
        if len(args) != 1: return super().__call__(*args, **kwargs)
        obj = args[0]
        if isinstance(obj, cls): return obj
        return super().__call__(**{next(iter(cls._attrs)): obj})


class Attributes(metaclass=AttributesMeta):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self._attrs:
                raise TypeError(f"Unexpected argument '{k}'")
            setattr(self, k, v)

    def __iter__(self):
        for k, v in self.__dict__.items():
            yield f' {self._attrs[k]}="{v}"'


class Stroke(Attributes):
    """Stroke attributes."""
    _attrs = {
        'color': 'stroke',
        'width': 'stroke-width',
        'opacity': 'stroke-opacity',
        'dash_array': 'stroke-dasharray',
        'dash_offset': 'stroke-dashoffset',
        'line_cap': 'stroke-linecap',
        'line_join': 'stroke-linejoin',
        'miter_limit': 'stroke-miterlimit',
    }

Stroke.default = Stroke(color='black', width=1, opacity=1)


class Fill(Attributes):
    """Fill attributes."""
    _attrs = {
        'color': 'fill',
        'opacity': 'fill-opacity',
        'rule': 'fill-rule',
    }

Fill.default = Fill(color='black', opacity=1)


class Transform:
    """A transform attribute."""
    def __init__(self):
        self.renders = []

    def matrix(self, a=0, b=0, c=0, d=0, e=0, f=0):
        @self.renders.append
        def render():
            yield f'matrix({a} {b} {c} {d} {e} {f})'
        return self

    def translate(self, x=0, y=0):
        @self.renders.append
        def render():
            yield f'translate({x}'
            if y != 0: yield f' {y}'
            yield ')'
        return self

    def scale(self, x=0, y=None):
        @self.renders.append
        def render():
            yield f'scale({x}'
            if not (y is None or y == x): yield f' {y}'
            yield ')'
        return self

    def rotate(self, angle, x=None, y=None):
        @self.renders.append
        def render():
            yield f'rotate({angle}'
            if x is not None and y is not None: yield f' {x} {y}'
            yield ')'
        return self

    def skew_x(self, angle):
        @self.renders.append
        def render():
            yield f'skewX({angle})'
        return self

    def skew_y(self, angle):
        @self.renders.append
        def render():
            yield f'skewY({angle})'
        return self

    def __iter__(self):
        if not self.renders: return
        yield ' transform="'
        for i, render in enumerate(self.renders):
            if i > 0: yield ' '
            yield from render()
        yield '"'


def matrix(*args, **kwargs): return Transform().matrix(*args, **kwargs)
def translate(*args, **kwargs): return Transform().translate(*args, **kwargs)
def scale(*args, **kwargs): return Transform().scale(*args, **kwargs)
def rotate(*args, **kwargs): return Transform().rotate(*args, **kwargs)
def skew_x(*args, **kwargs): return Transform().skew_x(*args, **kwargs)
def skew_y(*args, **kwargs): return Transform().skew_y(*args, **kwargs)


class Container:
    """An container for shape elements."""
    def __init__(self):
        self.renders = []

    def circle(self, x, y, r, *, stroke=None, fill=None, transform=None,
               style=None):
        @self.renders.append
        def render():
            yield f'<circle cx="{x}" cy="{y}" r="{r}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def ellipse(self, x, y, rx, ry, *, stroke=None, fill=None, transform=None,
               style=None):
        @self.renders.append
        def render():
            yield f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def line(self, x1, y1, x2, y2, *, stroke=None, transform=None,
             style=None):
        @self.renders.append
        def render():
            yield f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
            if stroke is not None: yield from Stroke(stroke)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def path(self, d, *, stroke=None, fill=None, transform=None,
             style=None):
        @self.renders.append
        def render():
            yield f'<path d="{d}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def polygon(self, *points, stroke=None, fill=None, transform=None,
                style=None):
        @self.renders.append
        def render():
            yield f'<polygon points="{' '.join(f'{p[0]},{p[1]}'
                                               for p in points)}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def polyline(self, *points, stroke=None, fill=None, transform=None,
                 style=None):
        @self.renders.append
        def render():
            yield f'<polyline points="{' '.join(f'{p[0]},{p[1]}'
                                                for p in points)}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def rect(self, x, y, width, height, *, rx=None, ry=None, stroke=None,
             fill=None, transform=None, style=None):
        @self.renders.append
        def render():
            yield f'<rect x="{x}" y="{y}" width="{width}" height="{height}"'
            if rx is not None: yield f' rx="{rx}"'
            if ry is not None: yield f' ry="{ry}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield '/>'

    def text(self, x, y, text, *, stroke='transparent', fill=None,
             transform=None, style=None):
        @self.renders.append
        def render():
            yield f'<text x="{x}" y="{y}"'
            if stroke is not None: yield from Stroke(stroke)
            if fill is not None: yield from Fill(fill)
            if transform is not None: yield from transform
            if style is not None: yield f' style="{style}"'
            yield f'>{text}</text>'

    def __iter__(self):
        for render in self.renders:
            yield from render()


class Group(Container):
    """A group."""
    def __init__(self, *, stroke=None, fill=None):
        super().__init__()
        self.stroke, self.fill = stroke, fill

    def __iter__(self):
        yield '<g'
        yield from Stroke(self.stroke)
        yield from Fill(self.fill)
        yield '>'
        yield from super().__iter__()
        yield '</g>'


class Image(Container):
    """An SVG image."""
    def __init__(self, width, height, *, stretch=False, stroke=Stroke.default,
                 fill=Fill.default, style=None):
        super().__init__()
        self.width, self.height, self.stretch = width, height, stretch
        self.stroke, self.fill = stroke, fill
        self.style = style

    def __iter__(self):
        yield ('<svg xmlns="http://www.w3.org/2000/svg"'
               ' xmlns:xlink="http://www.w3.org/1999/xlink"')
        yield f' viewBox="0 0 {self.width} {self.height}"'
        if not self.stretch:
            yield f' width="{self.width}" height="{self.height}"'
        if self.style is not None: yield f' style="{self.style}"'
        if self.stroke is not None: yield from Stroke(self.stroke)
        if self.fill is not None: yield from Fill(self.fill)
        yield '>'
        yield from super().__iter__()
        yield '</svg>'
