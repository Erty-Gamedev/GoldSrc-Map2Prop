# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 16:44:40 2023

@author: Erty
"""


from vector3d import Vector3D
from itertools import chain


def looped_pairs(polygon: list) -> tuple:
    iterable = iter(polygon)
    first = last = next(iterable)
    for x in iterable:
        yield last, x
        last = x
    yield (last, first)


def looped_slice(polygon: list, start: int, count: int) -> list:
    length = len(polygon)
    for i in range(start, start + count):
        yield polygon[i % length]


def looped_slice_inv(polygon, start, count) -> list:
    if start + count > len(polygon):
        return polygon[start + count - len(polygon): start]
    else:
        return chain(polygon[:start], polygon[start + count:])


def point_in_triangle(point, triangle) -> bool:
    a, b, c = triangle

    # Offset triangle by point, that way everything's relative to origin
    a -= point
    b -= point
    c -= point

    # Normal vectors of each vector between the point
    # and the triangle's vertices
    u, v, w = b.cross(c), c.cross(a), a.cross(b)

    # If the vectors aren't face the same direction,
    # the point must be outside the triangle
    if u.dot(v) < 0.0 or u.dot(w) < 0.0:
        return False

    return True


def points_in_triangle(triangle, points) -> bool:
    for point in points:
        if point_in_triangle(point, triangle):
            return True
    return False


def polygon_normal(polygon: list) -> Vector3D:
    normal = Vector3D(0, 0, 0)
    for a, b in looped_pairs(polygon):
        m = b - a
        p = b + a
        normal[0] += m[1] * p[2]
        normal[1] += m[2] * p[0]
        normal[2] += m[0] * p[1]
    return normal


def triangulate(polygon: list):
    """
    Converts a polygon to a set of triangles that cover the same area.

    Based on polytri by David Björkevik.
    (https://github.com/bjorkegeek/polytri)

    Modified to remove Numpy dependency.

    Returns:
        a generator of triangles, each specified in the same format as the
        input polygon
    """

    polygon = [Vector3D(*v) for v in polygon]

    normal = polygon_normal(polygon)
    i = 0
    while len(polygon) > 2:
        if i >= len(polygon):
            raise Exception('Triangulation failed')
        (a, b, c) = looped_slice(polygon, i, 3)
        triangle = (a, b, c)
        if (a == b or b == c):
            # Duplicate vertex, remove and skip
            del polygon[(i + 1) % len(polygon)]
            continue

        cross = (c - b).cross(b - a)
        dot = normal.dot(cross)
        yielded = False
        if dot > 1E-6:
            triangle = (a, b, c)
            if not points_in_triangle(
                    triangle, looped_slice_inv(polygon, i, 3)):
                del polygon[(i + 1) % len(polygon)]
                yield triangle
                i = 0
                yielded = True
        if not yielded:
            i += 1
