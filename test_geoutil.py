# -*- coding: utf-8 -*-
"""
@author: Erty
"""

import unittest
import geoutil

# Simple test box of size 2x2x2
box = {
    'A': geoutil.Vector3D(1, -1, 0),
    'B': geoutil.Vector3D(1, -1, 2),
    'C': geoutil.Vector3D(1, 1, 0),
    'D': geoutil.Vector3D(1, 1, 2),
    'E': geoutil.Vector3D(-1, -1, 0),
    'F': geoutil.Vector3D(-1, -1, 2),
    'G': geoutil.Vector3D(-1, 1, 0),
    'H': geoutil.Vector3D(-1, 1, 2),
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

    def test_segment_cross(self):
        expected = geoutil.Vector3D(12, 12, 12)

        result = geoutil.segments_cross(
            geoutil.Vector3D(0, 3, 0),
            geoutil.Vector3D(-.5, -.5, 4),
            geoutil.Vector3D(3, 0, 0)
        )
        self.assertEqual(expected, result)

    def test_segment_dot(self):
        expected = -19.5

        result = geoutil.segments_dot(
            geoutil.Vector3D(0, 3, 0),
            geoutil.Vector3D(-.5, -.5, 4),
            geoutil.Vector3D(3, 0, 0)
        )
        self.assertEqual(expected, result)

    def test_deg2rad(self):
        self.assertEqual(geoutil.PI / 2, geoutil.deg2rad(90))
        self.assertEqual(0, geoutil.deg2rad(360))
        self.assertEqual(0, geoutil.deg2rad(720))

    def test_points_to_plane(self):
        expected = {
            'x': (geoutil.Vector3D(1, 0, 0), 1),
            'y': (geoutil.Vector3D(0, 1, 0), 1),
            'z': (geoutil.Vector3D(0, 0, 1), 2),
            '-x': (geoutil.Vector3D(-1, 0, 0), 1),
            '-y': (geoutil.Vector3D(0, -1, 0), 1),
            '-z': (geoutil.Vector3D(0, 0, -1), 0),
        }

        for side, face in boxfaces.items():
            result = geoutil.points_to_plane(*face[:3])
            self.assertEqual(expected[side], result)

    def test_triangulate_face(self):
        expected = [
            [box['A'], box['C'], box['D']], [box['A'], box['D'], box['B']]
        ]
        result = geoutil.triangulate_face(boxfaces['x'])

        self.assertEqual(expected, result)

    def test_geometric_center(self):
        expected = geoutil.Vector3D(0, 0, 1)
        result = geoutil.geometric_center(box.values())

        self.assertEqual(expected, result)

    def test_sort_vertices(self):
        expected = [box['C'], box['D'], box['B'], box['A']]
        vertices = [box['A'], box['B'], box['C'], box['D']]

        result = geoutil.sort_vertices(vertices, geoutil.Vector3D(1, 0, 0))
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
