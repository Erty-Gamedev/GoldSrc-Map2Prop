# -*- coding: utf-8 -*-
"""
Created on Thu May 18 10:38:39 2023

@author: Erty
"""


import numpy as np
from collections import namedtuple
from is_convex_polygon import is_convex_polygon
from polytri.polytri import triangulate


Point = namedtuple('Point', ['x', 'y', 'z'])
Uv = namedtuple('Uv', ['u', 'v', 'w'])
ObjItem = namedtuple('ObjItem', ['i', 'v'])
PolyPoint = namedtuple('PolyPoint', ['v', 't', 'n'])


class InvalidSolidException(Exception):
    def __init__(self, message, vertices):
        self.message = message
        self.vertices = [(p.x, p.y, p.z) for p in vertices]
        super().__init__(f"{self.message}\nVertices:\n{self.vertices}")


def get_triples(vertices: list, last_two_and_first: bool = True):
    triples = [vertices[i:i + 3] for i in range(len(vertices) - 2)]
    if last_two_and_first:
        triples.append([vertices[-2], vertices[-1], vertices[0]])
    return triples


def direction(angle: float) -> int:
    return 0 if angle < np.pi else 1


def segments_dot(a: Point, b: Point, c: Point):
    vector_ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    vector_bc = [c.x - b.x, c.y - b.y, c.z - b.z]
    return np.dot(vector_ab, vector_bc)


def segments_cross(a: Point, b: Point, c: Point):
    ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    bc = [c.x - b.x, c.y - b.y, c.z - b.z]
    return np.cross(ab, bc)


def segments_angle(a: Point, b: Point, c: Point):
    vector_ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    vector_bc = [c.x - b.x, c.y - b.y, c.z - b.z]

    dot = np.dot(vector_ab, vector_bc)
    magprod = np.linalg.norm(vector_ab) * np.linalg.norm(vector_bc)

    return np.arccos(dot / magprod)


def plane_rotation(normal, d):
    a, b, c = normal

    squaresum = np.sum(np.power(normal, 2))
    rootsquaresum = np.sqrt(squaresum)
    costh = c / rootsquaresum
    sinth = np.sqrt(
        (np.power(a, 2) + np.power(b, 2)) / squaresum
    )
    k = 1 - costh
    u1 = b / rootsquaresum
    u2 = a / rootsquaresum
    u1u2k = u1 * u2 * k

    return np.array([
        [costh + np.power(u1, 2) * k, u1u2k, u2 * sinth],
        [u1u2k, costh + np.power(u2, 2) * k, -u1 * sinth],
        [-u2 * sinth, u1 * sinth, costh]
    ])


def polygon_transpose(polygon, vector):
    new_poly = []
    for point in polygon:
        new_poly.append(Point(
            point.x + vector[0],
            point.y + vector[1],
            point.z + vector[2]
        ))
    return new_poly


def flatten_plane(polygon: list):
    normal, k = polygon_to_plane(polygon)
    transposed = polygon_transpose(polygon, np.array(normal) * k)

    new_poly = []
    rotation = plane_rotation(normal, k)
    for point in transposed:
        point = np.array(point).dot(rotation)
        new_poly.append(Point(*point))
    return new_poly


def is_point_on_plane(point: Point, normal, k) -> bool:
    a, b, c = normal
    return np.absolute(
        a*point.x + b*point.y + c*point.z + k) < 0.0078125


def polygon_to_plane(polygon: list):
    first_points = polygon[:3]
    first_point = first_points[0]
    cross = segments_cross(*first_points)
    normal = cross / np.linalg.norm(cross)
    k = -(
        normal[0]*first_point.x
        + normal[1]*first_point.y
        + normal[2]*first_point.z
    )

    return normal, k


def check_planar(polygon: list) -> bool:
    if len(polygon) < 3:
        return False
    if len(polygon) == 3:
        return True

    normal, k = polygon_to_plane(polygon)

    for point in polygon[3:]:
        if not is_point_on_plane(point, normal, k):
            return False
    return True


def check_convex(polygon: list) -> bool:
    if len(polygon) < 3:
        return False
    if len(polygon) == 3:
        return True

    polygon2D = [(p.x, p.y) for p in flatten_plane(polygon)]
    return is_convex_polygon(polygon2D)


def triangulate_face(polygon: list) -> list:
    tris = []
    for tri in triangulate(polygon):
        tris.append([Point(*p) for p in tri])
    return tris


class PolyFace:
    def __init__(self, polypoints: list, texture: str):
        self.polypoints = polypoints
        self.vertices = [p.v.v for p in self.polypoints]
        self.texture = texture

        if not check_planar(self.vertices):
            raise InvalidSolidException(
                'Vertices are not planar', self.vertices)
        if not check_convex(self.vertices):
            raise InvalidSolidException(
                'Face is not convex', self.vertices)
