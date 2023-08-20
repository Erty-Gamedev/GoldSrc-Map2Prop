# -*- coding: utf-8 -*-
"""
Created on Thu May 18 10:38:39 2023

@author: Erty
"""


from vector3d import Vector3D
from math import sqrt, cos, sin, acos
from triangulate.triangulate import triangulate


PI = 3.141592653589793116
DEG2RAD = PI / 180


class PolyPoint:
    def __init__(self, v: Vector3D, t: Vector3D, n: Vector3D):
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
    return 0 if angle < PI else 1


def segments_dot(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    vector_ab = Vector3D(b.x - a.x, b.y - a.y, b.z - a.z)
    vector_bc = Vector3D(c.x - b.x, c.y - b.y, c.z - b.z)
    return vector_ab.dot(vector_bc)


def segments_cross(a: Vector3D, b: Vector3D, c: Vector3D) -> Vector3D:
    ab = Vector3D(b.x - a.x, b.y - a.y, b.z - a.z)
    bc = Vector3D(c.x - b.x, c.y - b.y, c.z - b.z)
    return ab.cross(bc)


def clip(value, minimum, maximum):
    return min(maximum, max(minimum, value))


def vectors_angle(a: Vector3D, b: Vector3D):
    return acos(clip(a.dot(b) / a.mag * b.mag, -1, 1))


def segments_angle(a: Vector3D, b: Vector3D, c: Vector3D):
    vector_ab = [b.x - a.x, b.y - a.y, b.z - a.z]
    vector_bc = [c.x - b.x, c.y - b.y, c.z - b.z]
    return vectors_angle(vector_ab, vector_bc)


def plane_rotation(normal, d):
    a, b, c = normal

    squaresum = sum(a ** 2, b ** 2, c ** 2)
    rootsquaresum = sqrt(squaresum)
    costh = c / rootsquaresum
    sinth = sqrt(
        (a ** 2 + b ** 2) / squaresum
    )
    k = 1 - costh
    u1 = b / rootsquaresum
    u2 = a / rootsquaresum
    u1u2k = u1 * u2 * k

    return [
        [costh + u1 ** 2 * k, u1u2k, u2 * sinth],
        [u1u2k, costh + u2 ** 2 * k, -u1 * sinth],
        [-u2 * sinth, u1 * sinth, costh]
    ]


def deg2rad(degrees) -> float:
    return degrees * DEG2RAD


def rotate_2d(vector: tuple, degrees: float) -> tuple:
    x, y = vector
    th = deg2rad(degrees)
    return x * cos(th) - y * sin(th), x * sin(th) + y * cos(th)


def polygon_transpose(polygon, vector):
    new_poly = []
    for point in polygon:
        new_poly.append(Vector3D(
            point.x + vector[0],
            point.y + vector[1],
            point.z + vector[2]
        ))
    return new_poly


def flatten_plane(polygon: list):
    normal, k = polygon_to_plane(polygon)
    transposed = polygon_transpose(polygon, normal * k)

    new_poly = []
    rotation = plane_rotation(normal, k)
    for point in transposed:
        new_point = Vector3D(
            point.dot(rotation[0]),
            point.dot(rotation[1]),
            point.dot(rotation[2]),
        )
        new_poly.append(new_point)
    return new_poly


def is_point_on_plane(point: Vector3D, normal, k) -> bool:
    a, b, c = normal
    return abs(
        a * point.x + b * point.y + c * point.z + k) < 0.0078125


def plane_normal(plane_points: tuple):
    return segments_cross(*plane_points).normal


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
    try:
        for tri in triangulate(polygon):
            tris.append([Vector3D(*p) for p in tri])
    except Exception as e:
        raise InvalidSolidException(e, polygon)
    return tris


def sum_vectors(vectors: list) -> Vector3D:
    return Vector3D(*[sum(v) for v in zip(*vectors)])


def average_normals(normals: list) -> Vector3D:
    return (sum_vectors(normals) / len(normals)).normal


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


def line_intersection(a: list, b: list):
    pass


def plane_intersection(a: list, b: list):
    pass


def find_geometric_center(vertices: list) -> Vector3D:
    p_min, p_max = Vector3D(*vertices[0]), Vector3D(*vertices[0])

    for vertex in vertices[1:]:
        for i in range(3):
            if vertex[i] < p_min[i]:
                p_min[i] = vertex[i]
            if vertex[i] > p_max[i]:
                p_max[i] = vertex[i]

    return Vector3D(
        *(p_min[i] + (p_max[i] - p_min[i]) / 2 for i in range(3)))


class PolyFace:
    def __init__(self, polypoints: list, texture: str):
        self.polypoints = polypoints
        self.vertices = [p.v for p in self.polypoints]
        self.texture = texture
