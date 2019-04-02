import os, csv
import pandas as pd
from .point import Point
from .cluster import Cluster
from .managers import PointManager

def cluster_around_points(filename, fixed_points, max_distance):
    '''Find the amount of points within max_distance of the points provided.
    args:
        filename: file in csv format with all the points that need to be assigned.
        fixed_points: The points in which radius we are going to count the points
        max_distance: the radius around the fixed points.
    output:
        a csv file in the same directory as the original. containing the fixed points and the amount of
        other points within the radius.'''
    file_output = os.path.join(os.path.dirname(filename), os.path.basename(filename).split('.')[0] + "_counted.csv")
    df = pd.read_csv(filename, index_col=0)
    manager = create_manager(df, fixed_points)

    manager.find_fixed_only(max_distance)

    with open(file_output, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['cluster_id', 'name', 'lat', 'lng', 'amount'])
        for i, c in enumerate(manager.clusters):
            writer.writerow([i, fixed_points[i].rec_id, fixed_points[i].lat, fixed_points[i].lng, len(c.points)-1])

def from_file(filename, area, granularity=25, office_size=10, fixed_points=None):
    '''Reduces the amount of points from the inside out.
    args:
        filename: csv format file with the points.
        area: distance in KM.
        granularity: the granularity for the clustering algorithm.
        fixed_points: Any fixed points to include.
    
    output:
        a file in the same directory with the csv file of the initial dataframe with a column with cluster id.
        and a file in the same directory with the centres of the clusters.'''

    file_output = os.path.join(os.path.dirname(filename), os.path.basename(filename).split('.')[0] + "_reduced.csv")
    df = pd.read_csv(filename, index_col=0)

    manager = create_manager(df, fixed_points)
    manager.find_clusters_inside_out(area, granularity)
    df = manager.assign_clusters(df)

    manager.create_centres_csv(file_output, office_size)    #Export the centres of the clusters.
    df.to_csv(filename)    #Assign extra column to initial dataframe

def create_manager(df, fixed_points=None, visits=False):
    if isinstance(df, str):
        df = pd.read_csv(df, index_col=0)

    if not visits:
        points = [Point(r, v['lat'], v['lng']) for r, v in df.iterrows()]
    else:
        points = [Point(r, v['lat'], v['lng'], v['annual_visits']) for r, v in df.iterrows()]

    manager = PointManager(points)
    if fixed_points:
        manager.pre_defined = fixed_points
    
    return manager
    

def get_max_and_avg_distance(partners):
    partners = pd.read_csv(partners)
    
    clusters = {}
    for r, val in partners.iterrows():
        point = Point(r, val['lat'], val['lng'])
        try:
            clusters[val['cluster']].points.append(point)   #Circumvents the staging process
        except KeyError:
            clusters[val['cluster']] = Cluster([point])

    averages = []
    max_dist = 0
    for c_id, c in clusters.items():
        averages.append(c.avg_distance_from_points(centre=True))
        max_dist_cluster = c.max_distance_from_points(centre=True)
        if max_dist_cluster > max_dist:
            max_dist = max_dist_cluster
            max_cluster_id = c_id
    
    return (max_dist, max_cluster_id), (sum(averages)/len(averages))