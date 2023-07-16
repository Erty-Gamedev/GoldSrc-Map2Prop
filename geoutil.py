# -*- coding: utf-8 -*-
"""
Created on Thu May 18 10:38:39 2023

@author: Erty
"""


import numpy as np
from collections import namedtuple
from polytri.polytri import triangulate


Point = namedtuple('Point', ['x', 'y', 'z'])
Uv = namedtuple('Uv', ['u', 'v', 'w'])


class PolyPoint:
    def __init__(self, v: Point, t: Point, n: Point):
        self.v, self.t, self.n = v, t, n


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


def vectors_angle(a: Point, b: Point):
    return np.arccos(np.clip(
            np.dot(a, b) / np.linalg.norm(a) * np.linalg.norm(b), -1, 1))


def segments_angle(a: Point, b: Point, c: Point):
    vector_ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    vector_bc = [c.x - b.x, c.y - b.y, c.z - b.z]
    return vectors_angle(vector_ab, vector_bc)


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


def rotate_2d(vector: tuple, degrees: float) -> tuple:
    x, y = vector
    th = np.deg2rad(degrees)
    return x * np.cos(th) - y * np.sin(th), x * np.sin(th) + y * np.cos(th)


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


def plane_normal(plane_points: tuple):
    cross = segments_cross(*plane_points)
    return cross / np.linalg.norm(cross)


def polygon_to_plane(polygon: list):
    first_points = polygon[:3]
    first_point = first_points[0]
    normal = plane_normal(first_points)
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


def triangulate_face(polygon: list) -> list:
    tris = []
    for tri in triangulate(polygon):
        tris.append([Point(*p) for p in tri])
    return tris


def average_normals(normals: list) -> Point:
    avg = np.sum(normals, axis=0) / len(normals)
    return Point(*(avg/np.linalg.norm(avg)))


def average_near_normals(normals: list, threshold: float) -> dict:
    new_normals = {}

    i, c = 0, 0
    while i < len(normals):
        c += 1
        if c > 1000:
            raise Exception('Possible infinite loop encountered')

        a = normals[i]

        near = [a]
        for b in normals:
            if b is a:
                continue
            if vectors_angle(a, b) <= threshold:
                near.append(b)
        if len(near) == 1:
            new_normals[a] = a
            i += 1
            continue

        new_normals[a] = average_normals(near)
        for n in near:
            new_normals[n] = new_normals[a]
            normals.remove(n)

        i = 0

    return new_normals


class PolyFace:
    def __init__(self, polypoints: list, texture: str):
        self.polypoints = polypoints
        self.vertices = [p.v for p in self.polypoints]
        self.texture = texture
