# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import html
from . import core


def esc(v, quote=True):
    if not isinstance(v, str): v = str(v)
    return html.escape(v, quote)


class _AttributesMeta(type):
    def __call__(cls, *args, **kwargs):
        if len(args) > 1:
            raise TypeError(
                f"{cls.__name__} takes at most 1 positional argument")
        if len(args) == 1:
            obj = args[0]
            if isinstance(obj, cls): return obj
            args = ()
            kwargs[next(iter(cls._attrs))] = obj
        return super().__call__(*args, **kwargs)


class _Attributes(metaclass=_AttributesMeta):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self._attrs:
                raise TypeError(f"Unexpected argument '{k}'")
            setattr(self, k, v)

    def __iter__(self):
        for k, a in self._attrs.items():
            if (v := getattr(self, k, None)) is not None:
                yield f' {a}="{esc(v)}"'


class Stroke(_Attributes):
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
    __slots__ = _attrs.keys()

Stroke.default = Stroke(color='black', width=1, opacity=1)


class Fill(_Attributes):
    _attrs = {
        'color': 'fill',
        'opacity': 'fill-opacity',
        'rule': 'fill-rule',
    }
    __slots__ = _attrs.keys()

Fill.default = Fill(color='black', opacity=1)


class Transform:
    __slots__ = ('renders',)

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
            for v in render(): yield esc(v)
        yield '"'


def matrix(*args, **kwargs): return Transform().matrix(*args, **kwargs)
def translate(*args, **kwargs): return Transform().translate(*args, **kwargs)
def scale(*args, **kwargs): return Transform().scale(*args, **kwargs)
def rotate(*args, **kwargs): return Transform().rotate(*args, **kwargs)
def skew_x(*args, **kwargs): return Transform().skew_x(*args, **kwargs)
def skew_y(*args, **kwargs): return Transform().skew_y(*args, **kwargs)


class _Element:
    _slots = ('_id', 'klass', 'style', 'stroke', 'fill')

    def __init__(self, *, klass=None, style=None, stroke=None, fill=None):
        self._id, self.klass, self.style = None, klass, style
        self.stroke, self.fill = Stroke(stroke), Fill(fill)

    @property
    def id(self):
        if self._id is None: self._id = core.new_id()
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def _attrs(self):
        if (v := self._id) is not None: yield f' id="{esc(v)}"'
        if (v := self.klass) is not None: yield f' class="{esc(v)}"'
        if (v := self.style) is not None: yield f' style="{esc(v)}"'
        yield from self.stroke
        yield from self.fill


class Shape(_Element):
    _slots = _Element._slots + ('transform',)

    def __init__(self, *, transform=None, **kwargs):
        self.transform = transform
        super().__init__(**kwargs)

    def _attrs(self):
        yield from super()._attrs()
        if (v := self.transform) is not None: yield from v


class Circle(Shape):
    __slots__ = Shape._slots + ('x', 'y', 'r')

    def __init__(self, x, y, r, **kwargs):
        self.x, self.y, self.r = x, y, r
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<circle cx="{esc(self.x)}" cy="{esc(self.y)}" r="{esc(self.r)}"'
        yield from self._attrs()
        yield '/>'


class Ellipse(Shape):
    __slots__ = Shape._slots + ('x', 'y', 'rx', 'ry')

    def __init__(self, x, y, rx, ry, **kwargs):
        self.x, self.y, self.rx, self.ry = x, y, rx, ry
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<ellipse cx="{esc(self.x)}" cy="{esc(self.y)}"'
        yield f' rx="{esc(self.rx)}" ry="{esc(self.ry)}"'
        yield from self._attrs()
        yield '/>'


class Line(Shape):
    __slots__ = Shape._slots + ('x1', 'y1', 'x2', 'y2')

    def __init__(self, x1, y1, x2, y2, **kwargs):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<line x1="{esc(self.x1)}" y1="{esc(self.y1)}"'
        yield f' x2="{esc(self.x2)}" y2="{esc(self.y2)}"'
        yield from self._attrs()
        yield '/>'


class Path(Shape):
    __slots__ = Shape._slots + ('path',)

    def __init__(self, *path, **kwargs):
        self.path = path
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<path d="'
        for i, el in enumerate(self.path):
            if i > 0: yield ' '
            if isinstance(el, (tuple, list)):
                yield esc(','.join(str(it) for it in el))
            else:
                yield esc(el)
        yield '"'
        yield from self._attrs()
        yield '/>'


class _Poly(Shape):
    def __init__(self, *points, **kwargs):
        self.points = points
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<{self._tag} points="{esc(' '.join(f'{p[0]},{p[1]}'
                                                   for p in self.points))}"'
        yield from self._attrs()
        yield '/>'


class Polygon(_Poly):
    __slots__ = _Poly._slots + ('points',)
    _tag = 'polygon'


class Polyline(_Poly):
    __slots__ = _Poly._slots + ('points',)
    _tag = 'polyline'


class Rect(Shape):
    __slots__ = Shape._slots + ('x', 'y', 'width', 'height', 'rx', 'ry')

    def __init__(self, x, y, width, height, *, rx=None, ry=None, **kwargs):
        self.x, self.y, self.width, self.height = x, y, width, height
        self.rx, self.ry = rx, ry
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<rect x="{esc(self.x)}" y="{esc(self.y)}"'
        yield f' width="{esc(self.width)}" height="{esc(self.height)}"'
        if (v := self.rx) is not None: yield f' rx="{esc(v)}"'
        if (v := self.ry) is not None: yield f' ry="{esc(v)}"'
        yield from self._attrs()
        yield '/>'


class Text(Shape):
    __slots__ = Shape._slots + ('x', 'y', 'text')

    def __init__(self, x, y, text, **kwargs):
        self.x, self.y, self.text = x, y, text
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<text x="{esc(self.x)}" y="{esc(self.y)}"'
        yield from self._attrs()
        yield f'>{esc(self.text, False)}</text>'


class Use(Shape):
    __slots__ = Shape._slots + ('href', 'x', 'y')

    def __init__(self, href, *, x=0, y=0, **kwargs):
        if not isinstance(href, str): href = f'#{href.id}'
        self.href, self.x, self.y = href, x, y
        super().__init__(**kwargs)

    def __iter__(self):
        yield f'<use href="{esc(self.href)}" '
        yield f' x="{esc(self.x)}" y="{esc(self.y)}"'
        yield from self._attrs()
        yield '/>'


class Container(Shape):
    _slots = Shape._slots + ('children',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = []

    def add(self, child):
        self.children.append(child)
        return child

    def circle(self, *args, **kwargs):
        return self.add(Circle(*args, **kwargs))

    def ellipse(self, *args, **kwargs):
        return self.add(Ellipse(*args, **kwargs))

    def line(self, *args, **kwargs):
        return self.add(Line(*args, **kwargs))

    def path(self, *args, **kwargs):
        return self.add(Path(*args, **kwargs))

    def polygon(self, *args, **kwargs):
        return self.add(Polygon(*args, **kwargs))

    def polyline(self, *args, **kwargs):
        return self.add(Polyline(*args, **kwargs))

    def rect(self, *args, **kwargs):
        return self.add(Rect(*args, **kwargs))

    def text(self, *args, **kwargs):
        return self.add(Text(*args, **kwargs))

    def group(self, *args, **kwargs):
        return self.add(Group(*args, **kwargs))

    def symbol(self, *args, **kwargs):
        return self.add(Symbol(*args, **kwargs))

    def use(self, *args, **kwargs):
        return self.add(Use(*args, **kwargs))

    def __iter__(self):
        yield f'<{self._tag}'
        yield from self._attrs()
        yield '>'
        for child in self.children: yield from child
        yield f'</{self._tag}>'


class Group(Container):
    __slots__ = Container._slots
    _tag = 'g'


class Symbol(Container):
    __slots__ = Container._slots
    _tag = 'symbol'

    def _attrs(self):
        yield from super()._attrs()
        yield ' overflow="visible"'


class Image(Container):
    __slots__ = Container._slots + ('width', 'height', 'stylesheet')

    def __init__(self, width, height, *, stylesheet=None, **kwargs):
        self.width, self.height, self.stylesheet = width, height, stylesheet
        super().__init__(**kwargs)

    def _attrs(self):
        yield ' xmlns="http://www.w3.org/2000/svg"'
        yield ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        yield f' viewBox="0 0 {esc(self.width)} {esc(self.height)}"'
        yield f' width="{esc(self.width)}" height="{esc(self.height)}"'
        yield from super()._attrs()

    def __iter__(self):
        if stylesheet := self.stylesheet: id = self.id  # Force ID allocation
        yield '<svg'
        yield from self._attrs()
        yield '>'
        if stylesheet: yield f'<style>\n#{id} {{{esc(stylesheet)}}}\n</style>'
        for child in self.children: yield from child
        yield '</svg>'
