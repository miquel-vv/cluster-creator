import unittest
import os
import pandas as pd
from geo_tools.manager import PointManager

class TestPointManager(unittest.TestCase):
    def setUp(self):
        self.df = pd.read_csv(os.path.join('tests', 'test_data.csv'))
        self.manager = PointManager(self.df)
    
    def test_init(self):
        self.assertEqual(len(self.df), len(self.manager.unassigned._points))

    def test_cluster_equal_amount(self):
        self.assertNotEqual(len(self.manager.unassigned._points), 0)
        amount_of_points = len(self.manager.unassigned._points)
        self.manager.cluster('equal_amount', max_visits=360)
        self.assertEqual(len(self.manager.unassigned._points), 0)
        self.assertEqual(len(self.manager.assigned), 6)
        points_assigned = len([p for cluster in self.manager.assigned for p in cluster._points])
        self.assertEqual(amount_of_points, points_assigned)
        
        clusters = self.manager.get_centers()
        self.assertGreaterEqual(360, max(clusters['visits']))

    def test_cluster_high_concentration(self):
        self.assertNotEqual(len(self.manager.unassigned._points), 0)
        amount_of_points = len(self.manager.unassigned._points)
        self.manager.cluster('highest_concentration', max_distance=100000)
        self.assertEqual(len(self.manager.unassigned._points), 0)
        self.assertEqual(len(self.manager.assigned), 12)
        points_assigned = len([p for cluster in self.manager.assigned for p in cluster._points])
        self.assertEqual(amount_of_points, points_assigned)
        
        clusters = self.manager.get_centers()
        self.assertGreaterEqual(100000, max(clusters['max_distance']))
    
    def test_get_centers(self):
        test_df = pd.read_csv(os.path.join('tests', 'clusters.csv'))
        self.manager.cluster('equal_amount', max_visits=360)
        clusters = self.manager.get_centers()
        self.assertTrue(len(clusters), len(test_df))

    def test_get_assigned_points(self):
        self.manager.cluster('equal_amount', max_visits=360)
        assigned = self.manager.get_assigned_points()
        self.assertEqual(len(self.df), len(assigned))