import csv
import pandas as pd
from scipy.cluster.vq import vq, kmeans
from sklearn.neighbors.kde import KernelDensity
from .point import Point, PointGroup
from .errors import MaxReachedException

class PointManager():
    def __init__(self, points):
        '''Initialised by passing a list of points or a pandas DataFrame.'''
        if isinstance(points, list):
            if all(isinstance(p, Point) for p in points):
                self.unassigned = PointGroup(points)
            raise TypeError("The list passed were not all Points.")
        
        if isinstance(points, pd.DataFrame):
            if not ('lat' in points.columns and 'lng' in points.columns):
                raise("The dataframe must contain the lat and lng columns.")
            self.unassigned = PointGroup(self.read_from_df(points))
            self.initial_dataframe = points
        
        self.assigned = []
            
    def read_from_df(self, df):
        points = []
        for rec_id, p in df.iterrows():
            p_values = dict(p)
            p_values['id'] = rec_id
            points.append(Point(**p_values))
        
        return points

    def reset(self):
        self.unassigned = PointGroup(self.read_from_df(self.initial_dataframe))
        self.assigned = []

    def assign_to_defined_centers(self, centers, max_distance=None, max_visits=None):
        for center in centers:
            if not self.unassigned: break

            start_point = self.unassigned.get_nearest(center, remove=True)
            new_group = PointGroup(start_point, max_distance=max_distance, max_visits=max_visits)
            for p in self.unassigned.get_points(start_point):
                try:
                    new_group.add_point(p)
                except MaxReachedException:
                    break

            self.assigned.append(new_group)
    
    def cluster(self, method, pre_defined=None, max_distance=None, max_visits=None):
        '''Create clusters from the unassigned point group.
        params:
            method (string): Either "equal_amount" or "highest_concentration". 
                Equal_amount means that the clustering happens outside - in. This prevents having
                several clusters at the edge with almost no points in them. So in fact, the clusters
                will roughly be the same size.
                Highest_concentration means that we don't care about single point clusters. We find
                the clusters where the highest concentration is first.
            pre_defined (list): Points where a cluster needs to be formed. This happens before any 
                other clustering done by the method.
            max_distance (int): The max distance a cluster can be apart in meters. Adding this will 
                significantly slow the algorithm as the center needs to be recalculated after each
                point is added to a cluster.
            max_visits (int): the max amount of visits in for one cluster.
        returns:
            void    
        '''
        if not method in {'equal_amount', 'highest_concentration'}:
            raise TypeError('Method must be either "equal_amount" or "highest_concentration".')
        elif method == 'equal_amount':
            start_point_getter = self.unassigned.get_furthest
        elif method == 'highest_concentration':
            start_point_getter = self.unassigned.get_highest_concentration

        if pre_defined:
            self.assign_to_defined_centers(pre_defined, max_distance, max_visits)

        while self.unassigned:
            start_point = start_point_getter(remove=True)
            if not isinstance(start_point, Point):
                start_point = start_point[0]
            start_point.cluster_id = len(self.assigned)
            new_cluster = PointGroup(start_point, max_distance=max_distance, max_visits=max_visits)
            for p in self.unassigned.get_points(start_point):
                try:
                    p.cluster_id = len(self.assigned)
                    if max_distance:
                        new_cluster.add_point(p, update_center=True)
                    else:
                        new_cluster.add_point(p)
                except MaxReachedException:
                    del p.cluster_id
                    break

            self.assigned.append(new_cluster)
    
    def get_centers(self, min_size=0):
        centers = {
            'id': [],
            'lat': [],
            'lng': [],
            'size': [],
            'max_distance': [],
            'visits': []
        }

        for i, cluster in enumerate(self.assigned):
            if len(cluster._points) >= min_size:
                center = cluster.get_center()
                centers['id'].append(i)
                centers['lat'].append(center.lat)
                centers['lng'].append(center.lng)
                centers['size'].append(len(cluster._points))
                centers['max_distance'].append(cluster.get_max_distance())
                centers['visits'].append(cluster.get_visits())
        
        df = pd.DataFrame(centers)
        return df.set_index('id')
    
    def get_assigned_points(self):
        points = [p for cluster in self.assigned for p in cluster._points]
        
        data = {key:[] for key in points[0].__dict__.keys()}

        for p in points:
            for key in data.keys():
                data[key].append(p.__dict__[key])
        
        df = pd.DataFrame(data)
        return df.set_index('id')