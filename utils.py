def dataframe_to_points(df, lat_name, lng_name):
    return [Point(r, val[lat_name], val[lng_name]) for r, val in df.iterrows()]