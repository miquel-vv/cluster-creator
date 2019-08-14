import os
from .scripts import two_step_clustering

def cli():
    import sys
    
    file_name = sys.argv[1]
    if not os.path.exists(file_name): 
        raise TypeError("{} was not found".format(file_name))
    
    if not os.path.isfile(file_name):
        raise TypeError("{} is not a file".format(file_name))
    
    max_visits = int(sys.argv[2])
    areas = [50, 100, 200]

    return file_name, max_visits, areas

def main():
    file_name, max_visits, areas = cli()    
    print("Starting conversion...")
    output = two_step_clustering(file_name, max_visits, areas)
    print("Geojson created at {}".format(output))

if __name__ == "__main__":
    main()