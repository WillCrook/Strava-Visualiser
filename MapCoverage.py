import os, gzip
import gpxpy
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point
from fitparse import FitFile


# Load UK shapefile
world = gpd.read_file("ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp")
uk = world[world['ADMIN'] == 'United Kingdom'].to_crs(epsg=27700)


# Parse all GPX runs from folder
folder = './Strava Data/activities'
runs = []

# Parse all GPX runs from folder
folder = './Strava Data/activities'
runs = []
valid_files = 0

for file in os.listdir(folder):
    path = os.path.join(folder, file)
    
    if file.endswith('.gpx'):
        with open(path, 'r') as f:
            gpx = gpxpy.parse(f)
    
    elif file.endswith('.gpx.gz'):
        with gzip.open(path, 'rt') as f:
            gpx = gpxpy.parse(f)

    elif file.endswith('.fit.gz'):
        try:
            with gzip.open(path, 'rb') as f:
                fitfile = FitFile(f)
                points = []
                for record in fitfile.get_messages('record'):
                    lat = None
                    lon = None
                    for data in record:
                        if data.name == 'position_lat' and data.value is not None:
                            lat = data.value * (180 / 2**31)
                        elif data.name == 'position_long' and data.value is not None:
                            lon = data.value * (180 / 2**31)
                    if lat is not None and lon is not None:
                        runs.append(Point(lon, lat))
                        points.append((lat, lon))
                if points:
                    valid_files += 1
        except Exception as e:
            print(f"Failed to parse {file}: {e}")
        continue

    else:
        continue  # skip non-supported files

    file_has_points = False
    for track in gpx.tracks:
        for segment in track.segments:
            if segment.points:
                file_has_points = True
                for point in segment.points:
                    runs.append(Point(point.longitude, point.latitude))
    if file_has_points:
        valid_files += 1

print(f"Valid activities parsed: {valid_files}")

# Ensure runs list is populated
print(f"Number of GPS points extracted: {len(runs)}")

# Convert to GeoDataFrame and reproject
if len(runs) > 0:
    gdf = gpd.GeoDataFrame(geometry=runs, crs='EPSG:4326').to_crs(epsg=27700)
    print("GeoDataFrame created successfully.")
else:
    print("No GPS points were extracted. Check your GPX files.")

# If GeoDataFrame has data, proceed with buffering and plotting
if not gdf.empty:
    print("Proceeding with buffering and plot...")  # Debugging line
    buffered = gdf.buffer(20)

    # Check if buffered geometries are valid
    print(f"Buffered geometries valid: {all(buffer.is_valid for buffer in buffered)}")

    # Check if any buffered geometries intersect with the UK
    intersects_uk = [buffer.intersects(uk.geometry.iloc[0]) for buffer in buffered]
    print(f"Geometries that intersect the UK: {sum(intersects_uk)} / {len(buffered)}")

    covered_union = buffered.union_all()  # Create a single geometry from all buffered areas
    uk_area = uk.geometry.area.iloc[0]
    covered_area = covered_union.area
    percent = (covered_area / uk_area) * 100

    print(f"Coverage Percentage: {percent:.4f}%")

    # Plot and save as PNG
    fig, ax = plt.subplots(figsize=(10, 12))
    uk.plot(ax=ax, color='lightgrey', edgecolor='black')
    gdf.plot(ax=ax, color='blue', linewidth=1)
    gpd.GeoSeries(covered_union).plot(ax=ax, color='red', alpha=0.3)

    # Add text
    plt.title("UK Running Coverage Map", fontsize=16)
    plt.text(0.05, 0.05, f"UK covered: {percent:.4f}%", transform=ax.transAxes,
             fontsize=12, bbox=dict(facecolor='white', alpha=0.7))

    plt.axis('off')
    plt.tight_layout()
    plt.savefig("uk_run_coverage.svg", dpi=300, format='svg')

    # Check if the image file is saved
    if os.path.exists("uk_run_coverage.svg"):
        print("Plot saved successfully as 'uk_run_coverage.svg'.")
    else:
        print("Failed to save the plot.")
else:
    print("GeoDataFrame is empty. No map was created.")