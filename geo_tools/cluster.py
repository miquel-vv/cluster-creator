from .point import Point, DistanceCalculator
from scipy.optimize import minimize


class Cluster():
    def __init__(self, points=[]):
        self.points = points
        self.staged_points = []
        self.centre = None
        self.staged_centre = None
        self.distance_calculator = DistanceCalculator()


    def stage_point(self, point, distance=True):
        '''Stages a point in the cluster and calculates the new centre. Returns the max
        distance to the hypothetical new centre. To put add the point to the cluster use
        the add_staged_point method or remove using the remove from staging method.
        
        args:
            The point to be tested. An instance of the Point class.
            
        output:
            The new max distance between the centre and the points.
        
        '''
        self.staged_points = self.points[:]   #Shallow copy list
        self.staged_points.append(point)
        self.distance_calculator.points = self.staged_points  
        
        self.staged_centre = self.find_centre(staged=True)
        
        if distance:
            return self.max_distance_from_points(self.staged_centre, staged=True)
        else:
            return self.get_visits(staged=True)
    

    def get_visits(self, staged=False):
        
        if not staged:
            points = self.points
        else:
            assert self.staged_points, "No point staged."
            points = self.staged_points
        
        return sum([p.visits for p in points])


    def add_staged_point(self):
        '''If a point was staged earlier, this method adds it permanently to the list.'''
        assert self.staged_points, "No point staged."
        self.points = self.staged_points[:]
        self.staged_points = None
        self.centre = self.staged_centre
        self.staged_centre = None
        return self.centre
    

    def remove_staged_point(self):
        '''If a point was staged earlier, this removes the staged point.'''
        assert self.staged_points, "No point staged."
        self.staged_points = None
        self.staged_centre = None


    def find_centre(self, staged=False):
        
        '''Looks for the centre of the cluster and returns it as a point.
        args:
            staged (optional): Indicates whether you are looking for the centre including
            the staged point. This is necessary because the function resets the 
            distance_calculator otherwise and won't save the centre as an attribute.
        output:
            the centre as an instance of the Point class.
        '''
        
        if not staged:
            assert self.points, "No points in this cluster."
            self.distance_calculator.points = self.points[:] #Shallow copy
        else:
            assert self.staged_points, "No staged points."
            self.distance_calculator.points = self.staged_points[:] #Shallow copy
        
        b_lat = (-90, 90)
        b_lng = (-180, 180)
        bnds = (b_lat, b_lng)
        
        initial_guess = [self.points[0].lat, self.points[0].lng]
        
        minimal = minimize(self.distance_calculator, 
                           initial_guess, 
                           method='L-BFGS-B', 
                           bounds=bnds)
        centre = Point('centre', minimal['x'][0], minimal['x'][1])
        
        if not staged:
            self.centre = centre
        
        return centre
    

    def distance_from_points(self, point):
        '''Calculates the distance of a given point to all points in the cluster.'''
        
        assert self.points, "No points in this cluster"
        
        self.distance_calculator.points = self.points[:] #Shallow copy of list
        
        return self.distance_calculator([point.lat, point.lng])


    def list_of_distances(self, point=None, centre=False, staged=False):
        
        if centre and not self.centre:
            self.centre = self.find_centre()

        if not staged:
            assert self.points, "No points in this cluster"
            if centre:
                distances = [p.dist_to_other(self.centre) for p in self.points]
            else:
                distances = [p.dist_to_other(point) for p in self.points]
        else:
            assert self.staged_points, "No staged point."
            if centre:
                distances = [p.dist_to_other(self.centre) for p in self.staged_points]
            else:
                distances = [p.dist_to_other(point) for p in self.staged_points]
        
        return distances


    def max_distance_from_points(self, point=None, centre=False, staged=False):
        '''Returns the distance of from the given point to the point furthest away 
        in the cluster.'''
        distances = self.list_of_distances(point, centre, staged)
        return max(distances)


    def avg_distance_from_points(self, point=None, centre=False, staged=False):
        '''Returns the distance of from the given point to the point furthest away 
        in the cluster.'''
        distances = self.list_of_distances(point, centre, staged)
        return sum(distances)/len(distances)

    
    def points_index(self):
        '''returns a set with the rec_id of all points in the cluster.
        args: /
        
        output:
            a set with all points rec_id.'''
        
        return {p.rec_id for p in self.points}
