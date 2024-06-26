# -*- coding: utf-8 -*-
"""
@author: Erty
"""

from typing import Union, TypeAlias, Final
from math import sqrt

EPSILON: Final[float] = 1/(2**10)
Number: TypeAlias = Union[int, float]


class Vector3D(list):
    def __init__(self, x: Number, y: Number, z: Number):
        super().__init__((x, y, z))

    @classmethod
    def zero(cls): return cls(0, 0, 0)

    @property
    def x(self): return self[0]
    @x.setter
    def x(self, value: Number): self[0] = value

    @property
    def y(self): return self[1]
    @y.setter
    def y(self, value: Number): self[1] = value

    @property
    def z(self): return self[2]
    @z.setter
    def z(self, value: Number): self[2] = value

    @property
    def mag(self) -> float:
        return sqrt((self.x ** 2) + (self.y ** 2) + (self.z ** 2))

    @property
    def normalized(self):
        return Vector3D(
            self.x / self.mag, self.y / self.mag, self.z / self.mag)

    def dot(self, b) -> float:
        return self.x * b[0] + self.y * b[1] + self.z * b[2]

    def cross(self, b):
        return Vector3D(
            self.y * b[2] - self.z * b[1],
            self.z * b[0] - self.x * b[2],
            self.x * b[1] - self.y * b[0]
        )

    def eq(self, b) -> bool:
        return (
            abs(self.x - b[0]) < EPSILON and
            abs(self.y - b[1]) < EPSILON and
            abs(self.z - b[2]) < EPSILON
        )

    def __neg__(self):
        return Vector3D(-self.x, -self.y, -self.z)

    def __add__(self, b):
        if isinstance(b, (int, float)):
            return Vector3D(self[0] + b, self[1] + b, self[2] + b)
        elif isinstance(b, (Vector3D, list)):
            return Vector3D(self[0] + b[0], self[1] + b[1], self[2] + b[2])

    def __iadd__(self, b): return self.__add__(b)

    def __sub__(self, b):
        if isinstance(b, (int, float)):
            return Vector3D(self[0] - b, self[1] - b, self[2] - b)
        elif isinstance(b, (Vector3D, list)):
            return Vector3D(self[0] - b[0], self[1] - b[1], self[2] - b[2])

    def __isub__(self, b): return self.__sub__(b)

    def __mul__(self, b):
        if isinstance(b, (int, float)):
            return Vector3D(self[0] * b, self[1] * b, self[2] * b)
        elif isinstance(b, (Vector3D, list)):
            return Vector3D(self[0] * b[0], self[1] * b[1], self[2] * b[2])

    def __rmul__(self, b): return self.__mul__(b)

    def __truediv__(self, b):
        if isinstance(b, (int, float)):
            return Vector3D(self[0] / b, self[1] / b, self[2] / b)
        elif isinstance(b, (Vector3D, list)):
            return Vector3D(self[0] / b[0], self[1] / b[1], self[2] / b[2])

    def __rtruediv__(self, b): return self.__truediv__(b)

    def __str__(self):
        return f"[{self.x:f}, {self.y:f}, {self.z:f}]"

    def __repr__(self):
        return f"Vector3D({self.x:f}, {self.y:f}, {self.z:f})"

    def __hash__(self): return hash(tuple(self))

    def __format__(self, format_spec: str):
        if format_spec.startswith('p'):
            if ':' in format_spec:
                fspec = format_spec[1:]
                pre = f"({{{fspec}}}, {{{fspec}}}, {{{fspec}}})"
                return pre.format(self.x, self.y, self.z)
        return f"({self.x:f}, {self.y:f}, {self.z:f})"
