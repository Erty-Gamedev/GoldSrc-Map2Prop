from typing import List, Tuple, Union, Generator
from vector3d import Vector3D, EPSILON
from itertools import chain


class InvalidSolidException(Exception):
    def __init__(self, message: str, vertices: List[Vector3D]):
        self.message = message
        self.vertices = [(p[0], p[1], p[2]) for p in vertices]
        super().__init__(f"{self.message}\nVertices:\n{self.vertices}")


def looped_pairs(
        polygon: List[Vector3D]) -> Generator[Tuple[Vector3D, Vector3D], None, None]:
    iterable = iter(polygon)
    first = last = next(iterable)
    for x in iterable:
        yield last, x
        last = x
    yield (last, first)


def looped_slice(
        polygon: List[Vector3D],
        start: int,
        count: int) -> Generator[Vector3D, None, None]:
    length = len(polygon)
    for i in range(start, start + count):
        yield polygon[i % length]


def looped_slice_inv(
        polygon: List[Vector3D],
        start: int,
        count: int) -> Union[List[Vector3D]]:
    if start + count > len(polygon):
        return polygon[start + count - len(polygon): start]
    else:
        return list(chain(polygon[:start], polygon[start + count:]))


def point_in_triangle(
        point: Vector3D,
        triangle: Tuple[Vector3D, Vector3D, Vector3D]) -> bool:
    a, b, c = triangle

    # Offset triangle by point, that way everything's relative to origin
    a -= point
    b -= point
    c -= point

    # Normal vectors of each vector between the point
    # and the triangle's vertices
    u, v, w = b.cross(c), c.cross(a), a.cross(b)

    # If the vectors aren't facing the same direction,
    # the point must be outside the triangle
    if u.dot(v) < 0.0 or u.dot(w) < 0.0:
        return False

    return True


def points_in_triangle(
        triangle: Tuple[Vector3D, Vector3D, Vector3D],
        points: List[Vector3D]) -> bool:
    for point in points:
        if point_in_triangle(point, triangle):
            return True
    return False


def polygon_normal(polygon: List[Vector3D]) -> Vector3D:
    normal = Vector3D(0, 0, 0)
    for a, b in looped_pairs(polygon):
        m = b - a
        p = b + a
        normal[0] += m[1] * p[2]
        normal[1] += m[2] * p[0]
        normal[2] += m[0] * p[1]
    return normal


def triangulate(polygon: List[Vector3D], normal: Vector3D
                )-> Generator[Tuple[Vector3D, Vector3D, Vector3D], None, None]:
    """
    Converts a polygon to a set of triangles that cover the same area.

    Based on polytri by David Björkevik.
    (https://github.com/bjorkegeek/polytri)

    Modified to remove Numpy dependency.

    Returns:
        a generator of triangles (tuple of three Vector3D)
    """

    polygon = polygon.copy()

    i: int = 0
    while len(polygon) > 2:
        if i >= len(polygon):
            raise InvalidSolidException('Triangulation failed', polygon)
        (a, b, c) = looped_slice(polygon, i, 3)
        triangle = (a, b, c)
        if (a == b or b == c):
            # Duplicate vertex, remove and skip
            del polygon[(i + 1) % len(polygon)]
            continue

        cross = (c - b).cross(b - a)
        dot = -normal.dot(cross)
        yielded = False
        if dot > EPSILON:
            # triangle = (a, b, c)
            if not points_in_triangle(
                    triangle, looped_slice_inv(polygon, i, 3)):
                del polygon[(i + 1) % len(polygon)]
                yield triangle
                i = 0
                yielded = True
        if not yielded:
            i += 1
