from .errors import MaxReachedException
import math
from scipy.optimize import minimize
from sklearn.neighbors.kde import KernelDensity
import pandas as pd

class DistanceCalculator():
    """A Class to support the objective function that will need to be minimized"""
    
    def __init__(self, points=[]):
        """Accepts a list of points which will be used to calculate the distance."""
        self.points = points
        self.called = 0
        
    def __call__(self, centre_estimate):
        """Accepts a point in the form of a list [lat, lng] and calculates the distance
        to all points."""
        
        self.called += 1
        return sum([p.dist_to_other(centre_estimate) for p in self.points])
    
class Point():
    
    def __init__(self, lat, lng, **kwargs):
        if not 'rec_id' in kwargs and not 'id' in kwargs:
            raise TypeError('Please provide a id when creating points. \
                Column must be named "id".')

        self.lat = lat
        self.lng = lng
        
        for key, item in kwargs.items():
            self.__dict__[key] = item
    
    def _haversine(self, lat2, lng2):
        '''Calculates distance between two points on a sphere'''
        
        lat1 = self.lat
        lng1 = self.lng
        
        r = 6371000 # Radius of the earth in meters.

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2-lat1)
        delta_lambda = math.radians(lng2-lng1)

        a = (math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2)
        c = 2*math.asin(math.sqrt(a))

        return r*c
    
    def dist_to_origin(self):
        '''Returns the distance to point (0,0) in meters.
        args:
            none
        returns:
            The distance in meters.
        '''
        return self.dist_to_other((0,0))
    
    def dist_to_other(self, other):
        '''Returns the distance to other point in meters.
        args:
            Other point or tuple of format (latitude, longitude)
        returns:
            The distance in meters.
        '''
        if isinstance(other, Point):
            return self._haversine(other.lat, other.lng)
        else:
            return self._haversine(other[0], other[1])

class PointGroup:
    def __init__(self, points, max_distance=False, max_visits=False):

        if isinstance(points, Point):
            if isinstance(max_distance, Point):
                raise TypeError("If you want to instantiate with multiple points, pass them as a list, not as individual args.")

            self._start_point = points
            self._points = {points}
            self._center = points


        elif isinstance(points, list):
            if not all(isinstance(p, Point) for p in points):
                raise TypeError("The list can only contain Point.")

            self._points = {p for p in points}
            self._center = self.get_center()
        else:
            raise TypeError("PointGroup only takes points or a list of points.")
        
        self._max_distance = max_distance
        self._current_distance = 0
        self._max_visits = max_visits
        self._current_visits = 0

        if max_distance:
            self._current_distance = self.get_furthest()[1]
        
        if max_visits:
            self._current_visits = sum([point.visits for point in self._points])
    
    def __bool__(self):
        if len(self._points) == 0:
            return False
        return True

    def get_max_distance(self):
        return max([p.dist_to_other(self._center) for p in self._points])

    def get_visits(self):
        return sum([p.visits for p in self._points])

    def get_furthest(self, point=None, remove=False):
        '''Returns the furthest point in the group from a given point. If no point is given
        returns the furthest point from the centre of the group.
        args:
            point: A Point object to calculate the distance from.
            remove: Whether or not the furthest point needs to be removed.
        returns:
            tuple: (furthest_point, distance)'''
        
        if point:
            assert isinstance(point, Point)
            furthest = max(
                [(p, p.dist_to_other(point)) for p in self._points],
                key=lambda x: x[1]
            )
        else:
            furthest = max(
                [(p, p.dist_to_other(self._center)) for p in self._points],
                key=lambda x: x[1]
            )

        if remove==True:
            self._points.remove(furthest[0])
            
        return furthest
    
    def get_nearest(self, point, remove=False, queue=False):
        '''Looks through the unassigned points and returns the nearest one.
        args:
            point: the point from which you want to find the nearest to.
            remove: Boolean to define if the point should be taken out of the unassigned list or not.
                Does not work with queue, a queue will not be removed from the unassigned list.
            queue: Boolean to identify if only the nearest point needs to be returned or
                a list of points sorted based on distance in descending order.
        output:
            if queue is False: a tuple (point, distance) returning the index of the point in the
            unassigned list, the distance to that point and the point itself.
            If queue is True: a list of tuples as above sorted in descending order. Descending
            because that makes the pop more efficient.
        '''
        if remove and queue:
            raise TypeError("Either remove or queue must be False. A queue will not be removed from the list.")
        
        distances = [(p, point.dist_to_other(p)) for p in self._points]
        
        if not queue: 
            nearest = min(distances, key=lambda x:x[1])
            if remove:
                self._points.remove(nearest[0])

            return nearest
        else:
            distances.sort(key=lambda x:x[1])
            return distances

    def get_center(self, update=True):
        if update:
            b_lat = (-90, 90)
            b_lng = (-180, 180)
            bnds = (b_lat, b_lng)

            temp_point_list = list(self._points)
            distance_calculator = DistanceCalculator(temp_point_list)
            initial_lat = sum(p.lat for p in temp_point_list)/len(temp_point_list)
            initial_lng = sum(p.lng for p in temp_point_list)/len(temp_point_list)
            initial_guess = [initial_lat, initial_lng]
            
            minimal = minimize(distance_calculator, 
                            initial_guess, 
                            method='L-BFGS-B', 
                            bounds=bnds)
            self._center = Point(minimal['x'][0], minimal['x'][1], **{'id': 'centre'})
    
        return self._center
    
    def get_highest_concentration(self, remove=False):
        '''Returns the point in the unassigned set with the highest estimated concentration 
        using the Gaussian KDE estimator.
        args:
            remove: Boolean to define if the point should be taken out of the unassigned list or not.
        returns:
            The point with the highest concentration.    
        '''
        temp_point_list = list(self._points) #To preserve order going through kde estimation.

        lat_lng = {
            'lat': [p.lat for p in temp_point_list],
            'lng': [p.lng for p in temp_point_list]
        }

        lat_lng = pd.DataFrame(lat_lng)
        kde = KernelDensity(bandwidth=0.2, metric='haversine').fit(lat_lng)
        scored = kde.score_samples(lat_lng)
        lat_lng = lat_lng.assign(density=scored)
        highest = lat_lng['density'].idxmax()

        highest = temp_point_list[highest]

        if remove:
            self._points.remove(highest)
    
        return highest

    def add_point(self, point, update_center=False):
        '''Adds point and checks that no max is exceeded. Ignores points who dont have that attribute.
        args:
            point (Point): The point to be added.
            update_center (Boolean): Whether the center of the cluster should be recalculated before checking the distance.
        returns:
            void.'''
        assert isinstance(point, Point)

        if not self._max_distance and not self._max_visits:
            self._points.add(point)
            if update_center:
                self.get_center()
        
        if self._max_visits:
            try:
                new_visits = self._current_visits + point.visits
            except AttributeError:
                new_visits = self._current_visits

            if new_visits > self._max_visits:
                raise MaxReachedException("Number of visits exceeded.")
            
            self._current_visits = new_visits
        
        if self._max_distance:
            if update_center:
                self._points.add(point)
                self.get_center()
            
            new_distance = point.dist_to_other(self._center)
            if new_distance > self._max_distance:
                if update_center:
                    self._points.remove(point)
                raise MaxReachedException("Max distance from centre exceeded.")
            
            self._current_distance = new_distance
        
        self._points.add(point)

    def get_points(self, point):
        for point, dist in self.get_nearest(point, queue=True):
            yield point
            self._points.remove(point)
        return

    def remove_all(self):
        points = self._points
        self._points = set()
        return points