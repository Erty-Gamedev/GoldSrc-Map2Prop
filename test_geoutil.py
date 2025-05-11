"""
Tests for geometric functions
"""

import unittest
from vector3d import Vector3D
from triangulate.triangulate import triangulate

# Simple test box of size 2x2x2
box = {
    'A': Vector3D(1, -1, 0),
    'B': Vector3D(1, -1, 2),
    'C': Vector3D(1, 1, 0),
    'D': Vector3D(1, 1, 2),
    'E': Vector3D(-1, -1, 0),
    'F': Vector3D(-1, -1, 2),
    'G': Vector3D(-1, 1, 0),
    'H': Vector3D(-1, 1, 2),
}
boxfaces = {
    'x': [box['A'], box['C'], box['D'], box['B']],
    'y': [box['C'], box['G'], box['H'], box['D']],
    'z': [box['B'], box['D'], box['H'], box['F']],
    '-x': [box['E'], box['F'], box['H'], box['G']],
    '-y': [box['A'], box['B'], box['F'], box['E']],
    '-z': [box['A'], box['E'], box['G'], box['C']],
}


class TestGeoutil(unittest.TestCase):

    def test_triples(self):
        expected = [[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 1]]
        result = geoutil.get_triples([1, 2, 3, 4, 5], True)
        self.assertEqual(expected, result)

    def test_vectors_angle(self):
        a = Vector3D(0.8, 0.9, 1.0)
        b = Vector3D(1.0, 0.0, 0.0)
        result = geoutil.vectors_angle(a, b)
        self.assertAlmostEqual(1.0343, result, 4)

    def test_segments_angle(self):
        a = Vector3D(1.0483718182005188, 0.03884376154959568, 0.31663345635354817)
        b = Vector3D(1.6243808521814356, 0.7427492126576541, 0.4847987784743218)
        c = Vector3D(1.0639173529825854, 2.0197854083931044, 1.2592803409293363)
        result = geoutil.segments_angle(a, b, c)
        self.assertAlmostEqual(2.06996, result, 4)

    def test_segment_cross(self):
        expected = Vector3D(12, 12, 12)

        result = geoutil.segments_cross(
            Vector3D(0, 3, 0),
            Vector3D(-.5, -.5, 4),
            Vector3D(3, 0, 0)
        )
        self.assertEqual(expected, result)

    def test_segment_dot(self):
        expected = -19.5

        result = geoutil.segments_dot(
            Vector3D(0, 3, 0),
            Vector3D(-.5, -.5, 4),
            Vector3D(3, 0, 0)
        )
        self.assertEqual(expected, result)

    def test_deg2rad(self):
        self.assertEqual(geoutil.PI / 2, geoutil.deg2rad(90))
        self.assertEqual(0, geoutil.deg2rad(360))
        self.assertEqual(0, geoutil.deg2rad(720))

    def test_points_to_plane(self):
        expected = {
            'x': (Vector3D(1, 0, 0), 1),
            'y': (Vector3D(0, 1, 0), 1),
            'z': (Vector3D(0, 0, 1), 2),
            '-x': (Vector3D(-1, 0, 0), 1),
            '-y': (Vector3D(0, -1, 0), 1),
            '-z': (Vector3D(0, 0, -1), 0),
        }

        for side, face in boxfaces.items():
            result = geoutil.points_to_plane(*face[:3])
            self.assertEqual(expected[side], result)

    def test_ear_clip(self):
        expected = [
            (box['B'], box['A'], box['C']), (box['C'], box['D'], box['B'])
        ]
        result = ear_clip.ear_clip(boxfaces['x'], Vector3D(1, 0, 0))

        self.assertEqual(expected, result)
        # We expect n - 2 triangles for n vertices
        self.assertEqual(len(boxfaces['x']) - 2, len(result))

    def test_geometric_center(self):
        expected = Vector3D(0, 0, 1)
        result = geoutil.geometric_center(list(box.values()))

        self.assertEqual(expected, result)

    def test_bounds_from_points(self):
        expected = (Vector3D(-1, -1, 0), Vector3D(1, 1, 2))
        result = geoutil.bounds_from_points(list(box.values()))

        self.assertEqual(expected, result)

    def test_plane_normal(self):
        result = geoutil.plane_normal(boxfaces['x'][:3])
        self.assertEqual(Vector3D(1, 0, 0), result)

    def test_plane_normal2(self):
        A = Vector3D(0, -.25, 1)
        B = Vector3D(-.66172, .60355, .50136)
        C = Vector3D(-.94679, -.27159, .28654)

        result = geoutil.plane_normal((A, B, C))
        self.assertEqual(Vector3D(-.6018, 0, .7986), result)

    def test_sort_vertices(self):
        vertices = [box['A'], box['B'], box['C'], box['D']]
        expected = [box['A'], box['C'], box['D'], box['B']]

        result = geoutil.sort_vertices(vertices, Vector3D(1, 0, 0))
        self.assertEqual(expected, result)

    def test_sort_vertices2(self):
        A = Vector3D(0, -.25, 1)
        B = Vector3D(0, .25, 1)
        C = Vector3D(-.28236, -.60355, .78723)
        D = Vector3D(-.65862, -.60355, .50369)
        E = Vector3D(-.94679, -.27159, .28654)
        F = Vector3D(-.94725, .24074, .2862)
        G = Vector3D(-.66172, .60355, .50136)
        H = Vector3D(-.27808, .59819, .79045)

        vertices = [A, D, C, G, F, H, E, B]
        expected = [A, B, H, G, F, E, D, C]

        result = geoutil.sort_vertices(vertices, geoutil.plane_normal((A, G, E)))
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
