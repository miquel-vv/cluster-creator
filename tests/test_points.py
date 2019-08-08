import unittest

from geo_tools.point import Point, PointGroup
from geo_tools.errors import MaxReachedException

test_data = {
    'point_one': [51.513638, -0.099805, {'id': 'paul', 'other': 5, 'visits': 7.2}],
    'point_two': [51.499488, -0.128839, {'id': 'westminster'}],
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

        self.group = PointGroup([self.point_one, self.point_two, self.point_three])
    
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

        group = PointGroup(self.point_one)
        group.add_point(self.point_three)

        self.assertEqual(group.get_center(update=False), self.point_one)
        self.assertNotEqual(group.get_center(), self.point_one)
    
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
        
        self.group.get_furthest(remove=True)
        self.assertCountEqual(self.group._points, {self.point_one, self.point_three})
    
    def test_get_nearest(self):
        point_close_to_two = Point(51.501810, -0.140624, **{'id':'Victoria Memorial'})
        nearest = self.group.get_nearest(point_close_to_two)

        self.assertEqual(nearest[0], self.point_two)

        nearest_test = [self.point_two, self.point_one, self.point_three]
        nearest_queue = [p[0] for p in self.group.get_nearest(point_close_to_two, queue=True)]

        self.assertEqual(nearest_test, nearest_queue)

        self.group.get_nearest(point_close_to_two, remove=True)
        self.assertCountEqual(self.group._points, {self.point_one, self.point_three})
    
    def test_highest_concentration(self):
        between_one_and_three = Point(51.508813, -0.094113, id='southwark bridge')
        self.group.add_point(between_one_and_three)
        self.assertEqual(self.group.get_highest_concentration(), between_one_and_three)
        self.group.get_highest_concentration(remove=True)
        self.assertCountEqual(self.group._points, {self.point_one, self.point_two, self.point_three})
    
    def test_add_point(self):
        extra_point = Point(51.509751, -0.082530, id='st. dunstan')
        current_center = self.group.get_center()
        self.group.add_point(extra_point, update_center=True)
        self.assertNotEqual(current_center, self.group._center)

        group = PointGroup(self.point_one, max_distance=1500)
        group.add_point(self.point_three, update_center=True)

        self.assertNotEqual(group._center, self.point_one)
        self.assertNotEqual(group._center, self.point_three)
        self.assertCountEqual(group._points, {self.point_one, self.point_three})

        with self.assertRaises(MaxReachedException):
            group.add_point(self.point_two)
        
        self.point_two.visits = 2
        group = PointGroup(self.point_one, max_visits=10)
        group.add_point(self.point_two)

        with self.assertRaises(MaxReachedException):
            group.add_point(self.point_three)
    
    def test_get_points(self):
        new_list = [p for p in self.group.get_points(self.point_one)]
        self.assertCountEqual(new_list, [self.point_one, self.point_three, self.point_two])

        self.assertEqual(len(self.group._points), 0)

        group = PointGroup(new_list)

        i = 0
        for p in group.get_points(self.point_one):
            if i == 1:
                break
            i += 1
        
        self.assertCountEqual(group._points, [self.point_two, self.point_three])

    def test_bool(self):
        self.assertEqual(self.group.__bool__(), True)

        for p in self.group.get_points(self.point_one):
            pass

        self.assertEqual(self.group.__bool__(), False)

if __name__=='__main__':
    unittest.main()