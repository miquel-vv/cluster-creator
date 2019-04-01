import math

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
    
    def __init__(self, rec_id, lat, lng, visits=0):
        self.rec_id = rec_id
        self.lat = lat
        self.lng = lng
        self.visits = visits
    
    def _haversine(self, lat2, lng2):
        '''Calculates distance between two points on a sphere'''
        
        lat1 = self.lat
        lng1 = self.lng
        
        r = 6371000 # Radius of the earth in meters.

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2-lat1)
        delta_lambda = math.radians(lng2-lng1)

        a = (math.sin(delta_phi/2)*math.sin(delta_phi/2) + 
             math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)*math.sin(delta_lambda/2))
        c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))

        return r*c
    
    def dist_to_origin(self):
        '''Doesnt use the haversine formula as the carthesian distance is prop accurate enough
        for this purpose.'''
        return ((self.lat*1000)**2 + (self.lng*1000)**2)**(1/2)
    
    def dist_to_other(self, other):
        if isinstance(other, Point):
            return self._haversine(other.lat, other.lng)
        else:
            return self._haversine(other[0], other[1])
