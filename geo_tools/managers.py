import csv
import pandas as pd
from scipy.cluster.vq import vq, kmeans
from sklearn.neighbors.kde import KernelDensity    
from .cluster import Cluster
from .point import Point, PointGroup
from .errors import MaxReachedException

class NewPointManager():
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
        
        self.assigned = []
            
    def read_from_df(self, df):
        points = []
        for rec_id, p in df.iterrows():
            p_values = dict(p)
            p_values['id'] = rec_id
            points.append(Point(**p_values))
        
        return points

    def assign_to_defined_centers(self, centers, max_distance=None, max_visits=None):
        for center in centers:
            if not self.unassigned: break

            start_point = self.unassigned.find_nearest(center, remove=True)
            new_group = PointGroup(start_point, max_distance=max_distance, max_visits=max_visits)
            for p in self.get_points(start_point):
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
            max_distance (int): The max distance a cluster can be apart in meters.
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
            new_cluster = PointGroup(start_point, max_distance=max_distance, max_visits=max_visits)
            for p in self.unassigned.get_nearest(start_point):
                try:
                    if method == 'highest_concentration':
                        new_cluster.add_point(p, update_center=True)
                    else:
                        new_cluster.add_point(p)
                except MaxReachedException:
                    break

            self.assigned.append(new_cluster)
    
    def get_centers(self, method, min_size=0):
        centers = {
            'id': [],
            'lat': [],
            'lng': [],
            'size': [],
            'max_distance': [],
            'max_visits': []
        }

        for i, cluster in enumerate(self.assigned):
            if len(cluster._points) >= min_size:
                center = cluster.get_center()
                centers['id'].append(i)
                centers['lat'].append(center.lat)
                centers['lng'].append(center.lng)
                centers['size'].append(len(cluster._points))
                centers['max_distance'].append(clusters.get_max_distance())
                centers['max_visits'].append(clusters.get_visits())
        
        return pd.DataFrame(centers, index_col=['id'])


class PointManager():
    
    def __init__(self, points):
        self.unassigned = points
        self.clusters = []
        self.pre_defined = []

    def find_fixed_only(self, max_distance, including_fixed=True, double_counting=True):
        '''Clusters the points to the fixed points only and leaves the rest unassigned
        args: 
            max_distance: the area around the points that can be clustered.
            including_fixed: Boolean to assess wether the fixed points should be included in the cluster or not.
            double_counting: Boolean to determine if the points should be double counted or not. (i.e. If there are 
                            overlapping areas, points will be added to both clusters.)
        output:
            fills the self.clusters list.'''

        for p in self.pre_defined:
            if self.unassigned:
                if not including_fixed:
                    nearest = self.get_nearest(point=p, remove=True)
                    point = nearest[2]
                else:
                    point = p
                queue = self.get_nearest(point, queue=True)
                self.create_cluster_fill(point, queue, max_distance=max_distance, double_counting=double_counting)
    
    def find_clusters_fill(self, max_visits):
        '''Starts by filling the fixed points and then fills the furthest maximally.'''

        for p in self.pre_defined:
            if self.unassigned:
                nearest = self.get_nearest(point=p, remove=True)
                nearest_point = nearest[2]

                queue = self.get_nearest(nearest_point, queue=True)
                self.create_cluster_fill(nearest_point, queue, max_visits)
        
        if self.unassigned:
            self.find_clusters_top_right(max_visits, max_type='visits', pre_defined=False)

    def find_clusters_inside_out(self, max_distance, granularity):
        '''After the fixed points, starts by picking approximately evenly spread out points and fills 
        those first then fills in the furthest point.'''
        
        for p in self.pre_defined:
            nearest = self.get_nearest(p, remove=True)
            nearest_point = nearest[2]
            #logging.debug('Nearest_point of {} is {}'.format(p.rec_id, nearest.rec_id))
            queue = self.get_nearest(nearest_point, queue=True)
            self.create_cluster_queue(nearest_point, queue, max_distance)
        
        while self.unassigned:
            nearest = self.get_highest_concentration(remove=True)
            #logging.debug('Nearest_point of {} is {}'.format(c.rec_id, nearest.rec_id))
            queue = self.get_nearest(nearest, queue=True)
            self.create_cluster_queue(nearest, queue, max_distance)

    
    def find_clusters_top_right(self, maximum, max_type='distance',pre_defined=True):
        '''Analyses the unassigned list of points and puts them into clusters
        if the distance to cluster centre doesn't increase to above the max value.
        
        args:
            max_distance: The distance in km's
            pre_defined: If passed true, will first look at the pre_defined points to create clusters
        output:
            A list containing all the clusters.
        '''
        if pre_defined:
            for p in self.pre_defined:
                self.create_cluster(p, maximum, moving=False)
        
        max_iters = len(self.unassigned)
        while self.unassigned and max_iters>0:
            max_iters -= 1
            top_right = self.get_furthest(remove=True)
            if max_type == 'visits':
                queue = self.get_nearest(top_right, queue=True)
                self.create_cluster_fill(top_right, queue, max_visits=maximum)
            else:
                self.create_cluster(top_right, maximum, moving=False)
    
    def create_cluster(self, point, max_distance, moving=True):
        '''Looks through unassigned list and adds as much as possible to cluster.
        looks for points, nearest to the centre of the new cluster. 
        the static approach adds points nearest to the start point.
        args:
            point: The starting point of the cluster. instance of Point.
            max_distance: an integer/float value representing the max amount of km 
                         the centre of a cluster can be away from the furthest point.
            moving: refers to the approach in finding the next point to add. If it is moving
                    it will look for the point closest to the centre. If not, it will add
                    the point closest to the starting point.
        output:
            No output. Adds the created cluster to the cluster list of this class instance.
        '''
        
        new_cluster = Cluster([point])
        
        max_distance_exceeded = False
        new_centre = point
        while self.unassigned and not max_distance_exceeded:
            min_el = self.get_nearest(point=new_centre, remove=True)
            minimum = min_el[2]
            
            new_dist = new_cluster.stage_point(minimum)
            if new_dist > (max_distance*1000):
                max_distance_exceeded = True
                new_cluster.remove_staged_point()
                self.unassigned.append(minimum)
            else:
                if moving:
                    new_centre = new_cluster.add_staged_point()
                else:
                    new_cluster.add_staged_point()
        
        self.clusters.append(new_cluster)
    
    def create_cluster_queue(self, point, queue, max_distance):
        '''creates clusters based on the starting point and a passed list of points nearest to
        the starting point. This method is more efficient as the create cluster as it doesnt
        recalculate the minimum each time.
        args:
            point: the starting point, instance of Point
            queue: the list of points in descending order. (i.e. last element is nearest)
            max_distance: The maximum distance a point can be from the starting point. in km
        output:
            none. Adds the cluster to the self.clusters list.'''
        
        new_cluster = Cluster([point])
        to_pop = []
        max_distance_exceeded = False
        
        while not max_distance_exceeded and queue:
            nearest = queue.pop(-1)
            if not nearest[1] > (max_distance*1000):
                to_pop.append(nearest[0])
                new_cluster.stage_point(nearest[2])
                new_cluster.add_staged_point()
            else:
                max_distance_exceeded = True
        
        to_pop.sort(reverse = True)  #Sort the indexes descending, otherwise indexes won't be alligned
        for i in to_pop:
            self.unassigned.pop(i)
        
        self.clusters.append(new_cluster)
        
    def create_cluster_fill(self, point, queue, max_visits=0, max_distance=200, double_counting=False):
        '''This method creates a cluster by adding points until the max_visits is reached.
        To find points it adds point from the queue.
        args:
            point: the starting point of the cluster
            queue: The queue with points sorted by the proximity to the starting point.
        output:
            none. Adds the cluster to the point managers' cluster list.
        '''
        
        visits = point.visits
        new_cluster = Cluster([point])
        max_reached = False
        to_pop = []
        
        while not max_reached and queue:
            nearest = queue.pop(-1)
            visits += nearest[2].visits
            
            if (visits > max_visits and max_visits) or nearest[1]>(max_distance*1000):
                max_reached = True
            else:
                new_cluster.stage_point(nearest[2])
                new_cluster.add_staged_point()
                to_pop.append(nearest[0])
        
        if not double_counting:
            to_pop.sort(reverse=True)
            for i in to_pop:
                self.unassigned.pop(i)
        
        self.clusters.append(new_cluster)
        
    def assign_clusters(self, df):
        '''Takes a pandas.dataframe containing the points and adds a column
        indicating the cluster.
        args:
            df: pandas DataFrame with the points. 
                The index must be the same as rec_id
        output:
            the df with an additional column containing the cluster number.
        
        '''
        point_dict = {p: i for i, cluster in enumerate(self.clusters) for p in cluster.points_index()}

        cluster_id = []
        for rec_id in df.index:
            cluster_id.append(point_dict[rec_id])
            
        return df.assign(cluster_id=cluster_id)
    
    def create_centres_csv(self, filename, min_size=0):
        with open(filename,
                  'w',
                  newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['id', 'lat', 'lng'])

            for i, cluster in enumerate(self.clusters):
                if len(cluster.points) >= min_size:
                    centre = cluster.find_centre()
                    writer.writerow([i, centre.lat, centre.lng])