import csv
import pandas as pd
from scipy.cluster.vq import vq, kmeans    
from .cluster import Cluster
from .point import Point

class PointManager():
    
    def __init__(self, points):
        self.unassigned = points
        self.clusters = []
        self.pre_defined = []
    
    def find_top_right(self):
        '''returns the point in the top right using lat and lng as x and y axis.
        Caution: this method removes the point from the unassigned list!'''
        
        max_value = 0
        max_location = 0
        for i, p in enumerate(self.unassigned):
            dist_to_origin = p.dist_to_origin()
            if dist_to_origin > max_value:
                max_value = dist_to_origin
                max_location = i
        return self.unassigned.pop(max_location)
    
    def find_nearest_point(self, point, queue=False):
        '''Looks through the unassigned points and returns the nearest one.
        args:
            point: the point from which you want to find the nearest to.
            queue: Boolean to identify if only the nearest point needs to be returned or
                a list of points sorted based on distance in descending order.
        output:
            if queue is False: a tuple (index, distance, point) returning the index of the point in the
            unassigned list, the distance to that point and the point itself.
            If queue is True: a list of tuples as above sorted in descending order. Descending
            because that makes the pop more efficient.
        '''
        distances = [(i, point.dist_to_other(p), p) for i,p in enumerate(self.unassigned)]
        distances.sort(key=lambda x:x[1], reverse=True)
        
        if not queue: 
            return distances.pop(-1)
        else:
            return distances

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
                    nearest_index = self.find_nearest_point(p)
                    point = self.unassigned.pop(nearest_index[0])
                else:
                    point = p
                #logging.debug('Nearest_point of {} is {}'.format(p.rec_id, nearest.rec_id))
                queue = self.find_nearest_point(point, queue=True)
                self.create_cluster_fill(point, queue, max_distance=max_distance, double_counting=double_counting)
    
    def find_clusters_fill(self, max_visits):
        '''Starts by filling the fixed points and then fills the furthest maximally.'''

        for p in self.pre_defined:
            if self.unassigned:
                nearest_index = self.find_nearest_point(p)
                nearest = self.unassigned.pop(nearest_index[0])
                #logging.debug('Nearest_point of {} is {}'.format(p.rec_id, nearest.rec_id))
                queue = self.find_nearest_point(nearest, queue=True)
                self.create_cluster_fill(nearest, queue, max_visits)
        
        if self.unassigned:
            self.find_clusters_top_right(max_visits, max_type='visits', pre_defined=False)

    def find_clusters_inside_out(self, max_distance, granularity):
        '''After the fixed points, starts by picking approximately evenly spread out points and fills 
        those first then fills in the furthest point.'''
        
        for p in self.pre_defined:
            nearest_index = self.find_nearest_point(p)
            nearest = self.unassigned.pop(nearest_index[0])
            #logging.debug('Nearest_point of {} is {}'.format(p.rec_id, nearest.rec_id))
            queue = self.find_nearest_point(nearest, queue=True)
            self.create_cluster_queue(nearest, queue, max_distance)
        
        centres = self.find_potential_centres(granularity)
        for c in centres:
            if self.unassigned:
                nearest_index = self.find_nearest_point(c)
                nearest = self.unassigned.pop(nearest_index[0])
                #logging.debug('Nearest_point of {} is {}'.format(c.rec_id, nearest.rec_id))
                queue = self.find_nearest_point(nearest, queue=True)
                self.create_cluster_queue(nearest, queue, max_distance)
        
        if self.unassigned:
            self.find_clusters_top_right(max_distance, pre_defined=False)    
    
    def find_potential_centres(self, granularity):
        '''Applies the K-mean algortithm on the unassigned points and returns the centres.'''
        
        index = []
        lat = []
        lng = []
        
        for i, p in enumerate(self.unassigned):
            index.append(i)
            lat.append(p.lat)
            lng.append(p.lng)
            
        lat_lng = {'lat': lat,
                   'lng': lng}

        lat_lng = pd.DataFrame(lat_lng, index=index)
        guess = max([len(lat_lng)//granularity, 2]) #The initial guess can't be zero.
        centres,_ = kmeans(lat_lng, guess)

        return [Point('start', p[0], p[1]) for p in centres]
    
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
            top_right = self.find_top_right()
            #logging.debug('creating around top_right {}'.format(top_right.rec_id))
            if max_type == 'visits':
                queue = self.find_nearest_point(top_right, queue=True)
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
        
        #logging.info('Creating cluster for {}'.format(point.rec_id))
        new_cluster = Cluster([point])
        
        max_distance_exceeded = False
        new_centre = point
        while self.unassigned and not max_distance_exceeded:
            min_el = self.find_nearest_point(new_centre)
            minimum = self.unassigned.pop(min_el[0])
            #logging.debug('Nearest point is {} at {}'.format(minimum.rec_id, min_el[1]))
            
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
        #logging.debug('Creating the queue thinghy')
        
        while not max_distance_exceeded and queue:
            nearest = queue.pop(-1)
            #logging.debug('Nearest point is {}'.format(nearest[2].rec_id))
            if not nearest[1] > (max_distance*1000):
                #logging.debug('adding point {}'.format(nearest[2].rec_id))
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
            #logging.debug('Nearest point is {}'.format(nearest[2].rec_id))
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


class ClusterManager():
    pass