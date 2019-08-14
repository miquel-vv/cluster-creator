import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="spatial_point_manager",
    version="0.0.1",
    author="Miquel Vande Velde",
    author_email="miquel.vandevelde@gmail.com",
    description="Contains several objects for managing lat,lng points, as well as a two step clustering algo.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/miquel-vv/cluster-creator",
    packages=setuptools.find_packages(exclude=['tests']),
    install_requires=[
        'numpy',
        'pandas',
        'csv_to_geojson',
        'scikit-learn',
        'scipy',
        'sklearn'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['two_step_clustering=geo_tools.command_line:main']
    }
)