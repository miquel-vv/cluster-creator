import os, csv, logging
import pandas as pd
from .geo_tools import Point, Cluster, PointManager
from .geojson_transformer import create_geojson
import numpy as np
from scipy.cluster.vq import vq

logging.basicConfig(level=logging.DEBUG)

def perform_two_step_clustering(partners_file, weightings_file, visits, areas, fixed_points=None):
    '''
    args: 
        partner_filename: The file with all the partners to be analysed
        weightings: the file with the weightings of the adf-levels
        visits: The max amount of visits one employee can carry out.
        areas: A list of areas to be analysed, all in KMs.
    output:
        The whole file structure containing all the necessary files for mapping.
    '''
    assign_weightings(partners_file, weightings_file)

    folder = os.path.dirname(partners_file)
    if not folder:
        folder = os.getcwd()

    logging.info('Creating folders...')
    for area in areas:
        os.mkdir(os.path.join(folder, str(area)+'km'))

    logging.info('Running first clustering...')
    employee_file = find_employees(partners_file, visits)
    logging.info('Creating partners geojson...')
    create_geojson(partners_file)

    find_offices_multiple_areas(folder, areas, fixed_points)

def assign_weightings(partners_file, weightings_file, weighting_name='annual_visits'):
    '''Assigns the weightings to the partner file in the annual visits column.
    args:
        partners_file: the file with all the partners in csv format. Needs to have a column labelled 'adf'
        weightings_file: csv file containing the weightings. first column is adf_label, second is the 
                        annual visits.
    output:
        No output. The partners_file has an extra column named 'annual_visits'.
    '''
    partners = pd.read_csv(partners_file, index_col=0)

    with open(weightings_file, 'r') as file:
        reader = csv.reader(file, delimiter=',')
        reader.__next__()
        weightings = {r[0]: r[1] for r in reader}
    
    weighting = []
    for _,partner in partners.iterrows():
        weighting.append(weightings[partner['adf']])
    
    kwarg = {
        weighting_name: weighting
    }
    
    partners = partners.assign(**kwarg)
    partners.to_csv(partners_file)

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

def find_employees(filename, max_visits):
    '''Reduces the amount of points filling out each cluster to the max amount if visits.
    args:
        filename: csv format file with the points.
        area: distance in KM.
        granularity: the granularity for the clustering algorithm.
        fixed_points: Any fixed points to include.
    
    output:
        a file in the same directory with the csv file of the initial dataframe with a column with cluster id.
        and a file in the same directory with the centres of the clusters.'''

    file_output = os.path.join(os.path.dirname(filename), "employees.csv")
    df = pd.read_csv(filename, index_col=0)

    manager = create_manager(df, visits=True)
    manager.find_clusters_fill(max_visits)
    df = manager.assign_clusters(df)

    manager.create_centres_csv(file_output)    #Export the centres of the clusters.
    df.to_csv(filename)    #Assign extra column to initial dataframe
    return file_output

def find_offices_multiple_areas(folder, areas, fixed_points, office_size=7):
    '''Creates a folder for each radius used to cluster employees into an office and stores
    the results there.'''

    employees = pd.read_csv('employees.csv', index_col=0)

    for area in areas:
        logging.info('Running subclustering for '+str(area)+' KM')
        os.chdir(os.path.join(folder, str(area)+'km'))
        employees.to_csv('employees.csv')
        find_offices('employees.csv', area, office_size=office_size, fixed_points=fixed_points)
        create_geojson('employees.csv')
        create_geojson('offices.csv')

def find_offices(filename, area, granularity=25, office_size=7, fixed_points=None):
    '''Reduces the amount of points from the inside out.
    args:
        filename: csv format file with the points.
        area: distance in KM.
        granularity: the granularity for the clustering algorithm.
        fixed_points: Any fixed points to include.
    
    output:
        a file in the same directory with the csv file of the initial dataframe with a column with cluster id.
        and a file in the same directory with the centres of the clusters.'''

    file_output = os.path.join(os.path.dirname(filename), "offices.csv")
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
    

def get_max_and_avg_distance(partners, column_name):
    '''
    Looks for the distance between the cluster centres.
    args:
        partners: The partner file in csv format and coordinates in the lat and lng column.
        column_name: The name of the column that identifies to which cluster a partner is assigned to.
    returns:
        a tuple: ((maximum distance, cluster id with the max distance), average distance)
    '''

    partners = pd.read_csv(partners)

    clusters = {}
    for r, val in partners.iterrows():
        point = Point(r, val['lat'], val['lng'])
        try:
            clusters[val[column_name]].points.append(point)   #Circumvents the staging process
        except KeyError:
            clusters[val[column_name]] = Cluster([point])

    averages = []
    max_dist = 0
    for c_id, c in clusters.items():
        averages.append(c.avg_distance_from_points(centre=True))
        max_dist_cluster = c.max_distance_from_points(centre=True)
        if max_dist_cluster > max_dist:
            max_dist = max_dist_cluster
            max_cluster_id = c_id
    
    return (max_dist, max_cluster_id), (sum(averages)/len(averages))


def assign_current_offices(partners_file, offices_file):
    '''
    Assigns partners to the nearest office by straight line distance
    args:
        partners_file: the partners file in csv format and coordinates in the lat and lng column.
        offices_file: the offices file in csv format and coordinates in the lat and lng column.
    returns:
        updates the partners_file with an additional column containing the id for the office they where matched to.
        The id is the order number of the office in the offices file. e.g. office_id = 1 is the second office in the
        offices_file.
    '''
    offices = pd.read_csv(offices_file,
                          index_col=0)

    office_array = np.array([[o['lat'], o['lng']] for _, o in offices.iterrows()])
    partners = pd.read_csv(partners_file,
                           index_col=0)

    lat_lng = {'lat': partners['lat'], 'lng': partners['lng']}
    lat_lng = pd.DataFrame(lat_lng, index=partners.index)
    cls,_ = vq(lat_lng, office_array)
    partners = partners.assign(current_office_id=cls)
    partners.to_csv(partners_file)