import pandas as pd
from pyproj import Proj, Transformer
import math
import numpy as np
import re


def get_preplot_coordinates(preplot_file):

    def dms_to_decimal(dms_str):
        # Check if the string ends with N, S, E, or W to determine the hemisphere
        hemisphere = dms_str[-1]

        # Remove the hemisphere letter to work with the numeric part
        dms_num = dms_str[:-1]

        # Depending on whether it's latitude or longitude, split differently
        if hemisphere in ['N', 'S']:  # Latitude
            degrees = int(dms_num[:2])  # First 2 characters for degrees
            minutes = int(dms_num[2:4])  # Next 2 characters for minutes
            seconds = float(dms_num[4:])  # The rest for seconds
        elif hemisphere in ['E', 'W']:  # Longitude
            degrees = int(dms_num[:3])  # First 3 characters for degrees
            minutes = int(dms_num[3:5])  # Next 2 characters for minutes
            seconds = float(dms_num[5:])  # The rest for seconds

        # Convert DMS to decimal degrees
        decimal_degrees = degrees + minutes / 60 + seconds / 3600

        # Adjust polarity based on hemisphere
        if hemisphere in ['S', 'W']:
            decimal_degrees *= -1

        return decimal_degrees

    if hasattr(preplot_file, 'read'):
        # It's a file-like object (like TemporaryUploadedFile)
        flines = preplot_file.read().decode('utf-8').splitlines()
    else:
        # It's a string path
        with open(preplot_file, 'r') as f:
            flines = f.readlines()

        # preplot = preplot_path
    full_lines = []

    for line in flines:

        if line[0] == 'V':
            line = line.strip('\n')
            line = line.split()
            entry = dict()
            entry['linename'] = line[0][1:]
            entry['sp'] = line[1][0:5]
            entry['lat'] = line[1][5:15]
            entry['lon'] = line[1][15:]
            entry['east'] = line[2][0:8]
            entry['north'] = line[2][8:]
            full_lines.append(entry)
    # get first SP in else condition and last SP in if condition
    data_dict = {}
    for line in full_lines:
        name = line['linename']

        if name in data_dict:  #if line name is in the data_dict,
            data_dict[f'{name}']['sp2'] = line['sp']
            data_dict[f'{name}']['lat2'] = line['lat']
            data_dict[f'{name}']['lon2'] = line['lon']
            data_dict[f'{name}']['east2'] = line['east']
            data_dict[f'{name}']['north2'] = line['north']
        else:  #if line name not exists in data_dict, get SP1
            data_dict[f'{name}'] = {}
            data_dict[f'{name}']['sp1'] = line['sp']
            data_dict[f'{name}']['lat1'] = line['lat']
            data_dict[f'{name}']['lon1'] = line['lon']
            data_dict[f'{name}']['east1'] = line['east']
            data_dict[f'{name}']['north1'] = line['north']

    df = pd.DataFrame.from_dict(data=data_dict, orient='index')
    df.reset_index(inplace=True)
    df = df.rename(columns={'index': 'linename'})

    # function to get preplot length
    def get_dy(north2, north1):
        dy = round(round(float(north2), 3) - round(float(north1), 3), 3)
        return dy

    def get_dx(east2, east1):
        dx = round(round(float(east2), 3) - round(float(east1), 3), 3)
        return dx

    def get_az(dx, dy):
        if dx > 0 and dy > 0:
            az = round(90 - math.degrees(math.atan(dy / dx)), 3)
            return az
        elif dx > 0 and dy < 0:
            dy = abs(dy)
            az = round(90 + math.degrees(math.atan(dy / dx)), 3)
            return az
        elif dx < 0 and dy < 0:
            dx = abs(dx)
            dy = abs(dy)
            az = round(270 + math.degrees(math.atan(dy / dx)), 3)
            return az
        elif dx < 0 and dy > 0:
            dx = abs(dx)
            az = round(270 + math.degrees(math.atan(dy / dx)), 3)
            return az
        elif dx == 0 and dy > 0:
            return 0.0
        elif dx == 0 and dy < 0:
            return 180.0
        elif dx > 0 and dy == 0:
            return 90.0
        elif dx < 0 and dy == 0:
            return 270.0

    def get_distance(dE, dN):
        d = (dE**2 + dN**2)**0.5
        return d

    df['dE'] = df.apply(lambda x: get_dx(x['east2'], x['east1']), axis=1)
    df['dN'] = df.apply(lambda x: get_dy(x['north2'], x['north1']), axis=1)
    df['Az'] = df.apply(lambda x: get_az(x['dE'], x['dN']), axis=1)
    df['length'] = df.apply(lambda x: get_distance(x['dE'], x['dN']), axis=1)
    df['lat1_deg'] = df['lat1'].apply(dms_to_decimal)
    df['lon1_deg'] = df['lon1'].apply(dms_to_decimal)
    df['lat2_deg'] = df['lat2'].apply(dms_to_decimal)
    df['lon2_deg'] = df['lon2'].apply(dms_to_decimal)

    return df


def get_preplot_shots(df,
                      spi=16.666666666667,
                      zone=15,
                      datum="WGS84",
                      ellps="WGS84"):

    # Number of rows in the dataframe
    numrows = len(df.index)

    # Define UTM and WGS84 projections
    utm_proj = Proj(proj="utm", zone=zone, datum=datum, ellps=ellps)
    wgs84_proj = Proj(proj="latlong", datum=datum, ellps=ellps)

    # Create a transformer object
    transformer = Transformer.from_proj(utm_proj, wgs84_proj)

    # Vectorized grid to geographic transformation
    def grid_to_geographic(easting, northing):
        return np.vectorize(transformer.transform)(easting, northing)

    df_dict = {}

    for k, v in df['linename'].items():

        d0 = df.at[k, 'length']
        e0 = df.at[k, 'east1']
        n0 = df.at[k, 'north1']
        sp0 = df.at[k, 'sp1']
        a = df.at[k, 'Az']

        segments = round(d0 / spi)
        d = np.arange(segments + 1) * spi

        # Calculate easting and northing using vectorized operations
        e = float(e0) + d * np.sin(np.radians(a))
        n = float(n0) + d * np.cos(np.radians(a))
        sp = int(sp0) + np.arange(segments + 1)

        # Get lat/lon using vectorized transformation
        lat, lon = grid_to_geographic(e, n)

        # Combine all data into a DataFrame
        data = np.column_stack([sp, e, n, lat, lon])
        df_dict[f'{v}'] = pd.DataFrame(
            data, columns=['sp', 'east', 'north', 'lat', 'lon'])

    return df_dict


def srecords_to_df(srec):

    full_lines = []

    def dms_to_dd(dms, direction):
        degrees = int(dms[:2] if direction in 'NS' else dms[:3])
        minutes = int(dms[2:4] if direction in 'NS' else dms[3:5])
        seconds = float(dms[4:] if direction in 'NS' else dms[5:])
        dd = degrees + minutes / 60 + seconds / 3600
        if direction in ['S', 'W']:
            dd = -dd
        return dd

    if hasattr(srec, 'read'):
        # It's a file-like object (like TemporaryUploadedFile)
        flines = srec.read().decode('utf-8').splitlines()
    else:
        # It's a string path
        with open(srec, 'r') as f:
            flines = f.readlines()

    for k, v in enumerate(flines):
        if v[0] == 'S':
            entry = list()
            line = v.strip('\n')
            line = line.split(',')
            entry.append(line[0][1:11])  # linename
            entry.append(int(line[0][20:25]))  # sp

            # Convert lat and long to decimal degrees
            lat = dms_to_dd(line[0][25:34], line[0][34])
            lon = dms_to_dd(line[0][35:45], line[0][45])
            entry.append(lat)
            entry.append(lon)

            entry.append(float(line[0][47:55]))  # east
            entry.append(float(line[0][55:64]))  # north
            entry.append(float(line[0][64:70]))  # depth
            entry.append(int(line[0][70:73]))  # jday
            entry.append(line[0][73:79])  # time

            # Convert Z coordinates to decimal degrees
            for z in [flines[k - 3], flines[k - 2], flines[k - 1]]:
                zline = z.strip('\n').split(',')
                zlat = dms_to_dd(zline[0][25:34], zline[0][34])
                zlon = dms_to_dd(zline[0][35:45], zline[0][45])
                entry.append(zlat)
                entry.append(zlon)

            full_lines.append(entry)

    def ave_x(x1, x2, x3):
        meanx = (float(x1) + float(x2) + float(x3)) / 3
        return meanx

    df = pd.DataFrame(data=full_lines,
                      columns=[
                          'linename',
                          'sp',
                          'lat',
                          'long',
                          'east',
                          'north',
                          'depth',
                          'jday',
                          'time',
                          'zlat1',
                          'zlon1',
                          'zlat2',
                          'zlon2',
                          'zlat3',
                          'zlon3',
                      ])
    df['mean lat'] = df.apply(
        lambda x: ave_x(x['zlat1'], x['zlat2'], x['zlat3']), axis=1)
    df['mean lon'] = df.apply(
        lambda x: ave_x(x['zlon1'], x['zlon2'], x['zlon3']), axis=1)
    return df


def get_4d_preplot(fourd_preplot_file):

    # Read the file into a pandas DataFrame, assuming each line is a new record
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Initialize an empty list to hold the parsed data
    data_list = []

    # Loop through each line and extract the data using string slicing
    for line in lines:
        # Skip lines that don't start with 'S' (as those are the data lines we care about)
        if not line.startswith('S'):
            continue

        # Preplot line (e.g., 5007)
        preplot_line = line[1:5]

        # Shotpoint (e.g., 5950273017.60N)
        shotpoint = line[21:25].strip()

        # Latitude (degrees, minutes, seconds, N/S)
        lat_deg = int(line[25:27])
        lat_min = int(line[27:29])
        lat_sec = float(line[29:34])
        lat_hemisphere = line[34]

        # Longitude (degrees, minutes, seconds, E/W)
        lon_deg = int(line[35:38])
        lon_min = int(line[38:40])
        lon_sec = float(line[40:45])
        lon_hemisphere = line[45]

        # Easting and Northing
        easting = float(line[47:55].strip())
        northing = float(line[55:64].strip())

        # Convert latitude and longitude to decimal degrees
        latitude = lat_deg + lat_min / 60 + lat_sec / 3600
        longitude = lon_deg + lon_min / 60 + lon_sec / 3600

        # Apply hemisphere adjustments
        if lat_hemisphere == 'S':
            latitude = -latitude
        if lon_hemisphere == 'W':
            longitude = -longitude

        # Append the extracted values to the list
        data_list.append({
            "preplot_line": preplot_line,
            "shotpoint": shotpoint,
            "latitude": latitude,
            "longitude": longitude,
            "easting": easting,
            "northing": northing,
        })

    # Convert the list of data dictionaries to a pandas DataFrame
    df = pd.DataFrame(data_list)
    return df


def get_4d_preplot_endpoints(fourd_preplot_df):
    # Sort the DataFrame by 'preplot_line' and 'shotpoint' for sequential order
    df = fourd_preplot_df.sort_values(by=['preplot_line', 'shotpoint'])

    # Initialize a list to store processed data
    processed_data = []

    # Group by each preplot_line to get the first and last points
    for preplot_line, group in df.groupby('preplot_line'):
        # Get first and last rows of each group
        first = group.iloc[0]
        last = group.iloc[-1]

        # Extract values for first point
        shotpoint1 = first['shotpoint']
        eastings1 = first['easting']
        northings1 = first['northing']
        latitude1 = first['latitude']
        longitude1 = first['longitude']

        # Extract values for last point
        shotpoint2 = last['shotpoint']
        eastings2 = last['easting']
        northings2 = last['northing']
        latitude2 = last['latitude']
        longitude2 = last['longitude']

        # Calculate radial distance (Euclidean distance)
        length = np.sqrt((eastings2 - eastings1)**2 +
                         (northings2 - northings1)**2)

        # Calculate azimuth (angle in degrees from north)
        delta_east = eastings2 - eastings1
        delta_north = northings2 - northings1
        azimuth = np.degrees(np.arctan2(delta_east, delta_north)) % 360

        # Append the processed row to the list
        processed_data.append({
            "linename": preplot_line,
            "sp1": shotpoint1,
            "east1": eastings1,
            "north1": northings1,
            "lat1_deg": latitude1,
            "lon1_deg": longitude1,
            "sp2": shotpoint2,
            "east2": eastings2,
            "north2": northings2,
            "lat2_deg": latitude2,
            "lon2_deg": longitude2,
            "length": length,
            "azimuth": azimuth
        })

    # Create a new DataFrame from the processed data
    result_df = pd.DataFrame(processed_data)
    return result_df
