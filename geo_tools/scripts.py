import os, csv, logging
import pandas as pd
from .point import Point, PointGroup
from .manager import PointManager
from csv_to_geojson import create_geojson
import numpy as np
from scipy.cluster.vq import vq

logging.basicConfig(level=logging.DEBUG)

def two_step_clustering(filename, max_visits, areas, fixed_points=None):
    '''
    args: 
        filename: The file with all the partners to be analysed
        weightings: the file with the weightings of the adf-levels
        max_visits: The max amount of visits one employee can carry out.
        areas: A list of areas to be analysed, all in KMs.
    output:
        The whole file structure containing all the necessary files for mapping.
    '''
    folder = os.path.dirname(filename)
    if not folder:
        folder = os.getcwd()
    else:
        os.chdir(folder)

    equal_amount_clustering(filename, max_visits, 'employees.csv')
    highest_concentration_clustering(
        'employees.csv',  
        areas=areas,
        output_file='offices.csv',
        fixed_points=fixed_points
    )

def equal_amount_clustering(filename, max_visits, output_name):
    folder = os.path.dirname(filename)
    if not folder:
        folder = os.getcwd()
    else:
        os.chdir(folder)

    logging.info('Running first clustering...')

    partners = PointManager(pd.read_csv(filename, index_col=0))
    partners.cluster('equal_amount', max_visits=max_visits)
    partners.get_assigned_points().to_csv(filename)
    partners.get_centers().to_csv(output_name)

    logging.info('Creating partners geojson...')
    create_geojson(filename)

def highest_concentration_clustering(filename, areas, output_file, fixed_points=None, min_size=7):

    folder = os.path.dirname(filename)
    if not folder:
        folder = os.getcwd()
    else:
        os.chdir(folder)

    employees = PointManager(pd.read_csv(filename))

    for area in areas:
        os.mkdir(os.path.join(folder, str(area)+'km'))
        os.chdir(os.path.join(folder, str(area)+'km'))

        logging.info('Running subclustering for '+str(area)+' KM')

        employees.cluster('highest_concentration', max_distance=area*1000, pre_defined=fixed_points)
        employees.get_assigned_points().to_csv(filename)
        employees.get_centers(min_size=min_size).to_csv(output_file)

        create_geojson(filename)
        create_geojson(output_file)

        employees.reset()
        os.chdir(folder)

def cluster_around_points(filename, fixed_points, max_distance):
    '''
    Find the amount of points within max_distance of the points provided.
    args:
        filename: file in csv format with all the points that need to be assigned.
        fixed_points: The points in which radius we are going to count the points
        max_distance: the radius around the fixed points.
    output:
        a csv file in the same directory as the original. containing the fixed points and the amount of
        other points within the radius.
    '''

    file_output = os.path.join(os.path.dirname(filename), os.path.basename(filename).split('.')[0] + "_counted.csv")
    df = pd.read_csv(filename, index_col=0)
    manager = create_manager(df, fixed_points)

    manager.find_fixed_only(max_distance)

    with open(file_output, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['cluster_id', 'name', 'lat', 'lng', 'amount'])
        for i, c in enumerate(manager.clusters):
            writer.writerow([i, fixed_points[i].rec_id, fixed_points[i].lat, fixed_points[i].lng, len(c.points)-1])

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