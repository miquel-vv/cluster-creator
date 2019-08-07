import unittest

from ..geo_tools.point import Point, PointGroup

test_data = {
    'point_one': [51.513638, -0.099805, {'id': 'paul', 'other': 5, 'visits': 7.2}],
    'point_two': [51.499488, -0.128839, {'rec_id': 'westminster'}],
    'point_three': [51.506476, -0.089426, {'other': 56, 'visits': 4}]
}


class TestPoint(unittest.TestCase):

    def setUp(self):
        self.point_one = Point(
            test_data['point_one'][0], 
            test_data['point_one'][1], 
            **test_data['point_one'][2]
        )
        self.point_two = Point(
            test_data['point_two'][0], 
            test_data['point_two'][1], 
            **test_data['point_two'][2]
        ) 

    def test_id_requirement(self):
        with self.assertRaises(TypeError):
            point_three = Point(
                test_data['point_three'][0], 
                test_data['point_three'][1], 
                **test_data['point_three'][2]
            )
        
    def test_attribute_instantiated(self):
        self.assertEqual(self.point_one.visits, 7.2)
    
    def test_distance_calculation(self):
        self.assertAlmostEqual(
            self.point_one.dist_to_other(self.point_two), 
            self.point_one.dist_to_other(self.point_two),
            2
        )

        self.assertAlmostEqual(
            self.point_one.dist_to_other(self.point_two), 
            2552.16249,
            2
        )

        self.assertAlmostEqual(
            self.point_two.dist_to_origin(), 
            5726494.60306,
            2
        )


class TestPointGroup(unittest.TestCase):
    def setUp(self):
        self.point_one = Point(
            test_data['point_one'][0], 
            test_data['point_one'][1], 
            **test_data['point_one'][2]
        )
        self.point_two = Point(
            test_data['point_two'][0], 
            test_data['point_two'][1], 
            **test_data['point_two'][2]
        )
        test_data['point_three'][2]['id'] = 'Southwark'
        self.point_three = Point(
            test_data['point_three'][0], 
            test_data['point_three'][1], 
            **test_data['point_three'][2]
        )

        self.group = PointGroup([point_one, point_two, point_three])
    
    def test_instantiation(self):
        with self.assertRaises(TypeError):
            PointGroup('not_a_point') 
        
        with self.assertRaises(TypeError):
            PointGroup([self.point_one, self.point_two, 'not_a_point'])
        
        with self.assertRaises(TypeError):
            PointGroup(self.point_one, self.point_two)
        
    def test_center(self):
        group = PointGroup(self.point_one)
        self.assertEqual(group.get_center(update=False), self.point_one)

        self.assertAlmostEqual(
            self.group.get_center().lat,
            51.51012605,
            5
        )

        self.assertAlmostEqual(
            self.group.get_center().lng,
            -0.099762202,
            5
        )
    
    def test_get_furthest(self):
        away_from_center = self.group.get_furthest()
        self.assertEqual(away_from_center[0], self.point_two)
        self.assertAlmostEqual(
            away_from_center[1],
            2334.39333,
            2
        )

        away_from_two = self.group.get_furthest(self.point_two)
        self.assertEqual(away_from_two[0], self.point_three)
        self.assertAlmostEqual(
            away_from_two[1],
            2836.5123725,
            2
        )
    
    def test_get_nearest(self):
        point_close_to_two = Point(51.501810, -0.140624, **{'id'='Victoria Memorial'})

if __name__=='__main__':
    unittest.main()