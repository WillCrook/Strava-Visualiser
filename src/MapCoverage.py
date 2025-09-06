import os, gzip
import gpxpy
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, box
from fitparse import FitFile
import matplotlib as mpl
import contextily as ctx

# Configure matplotlib for better output
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 0.0001

# Load world shapefile
world = gpd.read_file("ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp")
uk = world[world['ADMIN'] == 'United Kingdom']

# Function to get region GeoDataFrame
def get_region_gdf(region_name):
    if region_name == 'UK':
        return uk.to_crs(epsg=27700)
    elif region_name == 'Sheffield':
        # Create a proper polygon for Sheffield
        sheffield_bbox = box(-1.55, 53.32, -1.35, 53.48)
        sheffield_poly = gpd.GeoDataFrame(
            geometry=[sheffield_bbox], 
            crs="EPSG:4326"
        ).to_crs(epsg=3857)  # Web Mercator for basemap compatibility
        return sheffield_poly
    elif region_name == 'Buckinghamshire':
        # Create a proper polygon for Buckinghamshire
        bucks_bbox = box(-1.02, 51.48, -0.47, 52.08)
        bucks_poly = gpd.GeoDataFrame(
            geometry=[bucks_bbox], 
            crs="EPSG:4326"
        ).to_crs(epsg=3857)  # Web Mercator for basemap compatibility
        return bucks_poly
    elif region_name == 'World':
        # Simplify world geometry to improve performance
        simplified_world = world.copy()
        simplified_world['geometry'] = simplified_world['geometry'].simplify(0.1)
        return simplified_world

# Parse all GPX runs from folder
folder = './Strava Data/activities'
runs = []
valid_files = 0

# Sample points (reduce file size)
sample_rate = 5  # Keep every 5th point

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
                point_count = 0
                for record in fitfile.get_messages('record'):
                    point_count += 1
                    if point_count % sample_rate != 0:
                        continue
                    
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
    point_count = 0
    
    for track in gpx.tracks:
        for segment in track.segments:
            if segment.points:
                file_has_points = True
                for point in segment.points:
                    point_count += 1
                    if point_count % sample_rate != 0:
                        continue
                    runs.append(Point(point.longitude, point.latitude))
    if file_has_points:
        valid_files += 1

print(f"Valid activities parsed: {valid_files}")
print(f"Number of GPS points extracted: {len(runs)}")

# Convert to GeoDataFrame
if len(runs) > 0:
    gdf = gpd.GeoDataFrame(geometry=runs, crs='EPSG:4326')
    print("GeoDataFrame created successfully.")
else:
    print("No GPS points were extracted. Check your GPX files.")
    exit()

# Define a list of regions to process
regions = ['World', 'UK', 'Sheffield', 'Buckinghamshire']

for region_name in regions:
    print(f"\nProcessing {region_name} view...")
    
    # Get the region geometry
    region_gdf = get_region_gdf(region_name)
    
    # Handle different projections
    if region_name == 'World':
        gdf_for_region = gdf.copy()  # Keep in WGS84 for world map
        buffer_distance = 0.02  # About 2km at equator
    elif region_name == 'UK':
        # For UK, use British National Grid
        gdf_for_region = gdf.to_crs(epsg=27700)
        buffer_distance = 100  # Meters
    else:
        # For Sheffield and Buckinghamshire, use Web Mercator for basemap compatibility
        gdf_for_region = gdf.to_crs(epsg=3857)
        buffer_distance = 200  # Meters in Web Mercator
    
    # Filter points to only include those within the selected region
    if region_name == 'World':
        # For world, we'll keep all points
        region_gdf_filtered = gdf_for_region
    else:
        # Get the region geometry
        region_geom = region_gdf.geometry.iloc[0]
        
        # Filter points within the region
        region_gdf_filtered = gpd.sjoin(
            gdf_for_region, 
            region_gdf, 
            how="inner", 
            predicate="within"
        )
        
        if region_gdf_filtered.empty:
            print(f"No points found within {region_name}. Trying with intersects instead...")
            # Fallback to intersects if within returns empty
            region_gdf_filtered = gpd.sjoin(
                gdf_for_region, 
                region_gdf, 
                how="inner", 
                predicate="intersects"
            )
    
    print(f"Points in {region_name}: {len(region_gdf_filtered)}")
    
    if region_gdf_filtered.empty:
        print(f"No points found in {region_name}. Skipping.")
        continue
        
    # Buffer the filtered points
    buffered = region_gdf_filtered.geometry.buffer(buffer_distance)
    covered_union = buffered.unary_union  # More efficient than union_all
    
    # Simplify the union for better display
    if region_name == 'World':
        covered_union = covered_union.simplify(0.001)
    else:
        simplify_tolerance = 10 if region_name == 'UK' else 30
        covered_union = covered_union.simplify(simplify_tolerance)
    
    # Calculate coverage
    if region_name == 'World':
        # For world, we'll just show the points without calculating coverage
        percent = None
    else:
        region_area = region_gdf.geometry.area.iloc[0]
        covered_area = covered_union.area
        percent = (covered_area / region_area) * 100
        print(f"Coverage Percentage: {percent:.4f}%")
    
    # Set up plot
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Different plotting based on region
    if region_name == 'World':
        # For world, use a different approach
        world.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.2)
        gdf.plot(ax=ax, markersize=0.5, color='blue', alpha=0.5)
        
        # No buffer display for world (would be too cluttered)
        # plt.title("Global Running Activities", fontsize=16)
        
    elif region_name == 'UK':
        # Plot the UK
        region_gdf.plot(ax=ax, color='lightgrey', edgecolor='black')
        
        # Plot the coverage
        gpd.GeoSeries([covered_union], crs=region_gdf.crs).plot(
            ax=ax, color='blue', alpha=0.3
        )
        
        # Plot the filtered points
        region_gdf_filtered.plot(ax=ax, markersize=1, color='blue')
        
        # Set the title and coverage text
        # plt.title(f"{region_name} Running Coverage", fontsize=16)
        # if percent is not None:
        #     plt.text(0.05, 0.05, f"Coverage: {percent:.2f}%", transform=ax.transAxes,
        #             fontsize=12, bbox=dict(facecolor='white', alpha=0.7))
        
        # Zoom to the region extent
        ax.set_xlim(region_gdf.total_bounds[0], region_gdf.total_bounds[2])
        ax.set_ylim(region_gdf.total_bounds[1], region_gdf.total_bounds[3])
    
    else:  # Sheffield or Buckinghamshire
        # For local regions, add a basemap
        # Plot the coverage area first
        coverage_gdf = gpd.GeoDataFrame(geometry=[covered_union], crs=region_gdf.crs)
        # coverage_gdf.plot(ax=ax, color='blue', alpha=0.4)
        
        # Plot the points on top
        region_gdf_filtered.plot(ax=ax, markersize=2, color='blue', alpha=0.7)
        
        # Add a basemap (OpenStreetMap)
        ctx.add_basemap(
            ax, 
            source=ctx.providers.OpenStreetMap.Mapnik,
            zoom=12 if region_name == 'Sheffield' else 10
        )
        
        # Add title and coverage info
        # plt.title(f"{region_name} Running Coverage", fontsize=16)
        # if percent is not None:
        #     plt.text(0.05, 0.05, f"Coverage: {percent:.2f}%", transform=ax.transAxes,
        #             fontsize=12, bbox=dict(facecolor='white', alpha=0.7))
        
        # Zoom to the region extent with a small buffer
        minx, miny, maxx, maxy = region_gdf.total_bounds
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
    
    plt.axis('off')
    plt.tight_layout()
    
    # Save as high-quality PNG
    output_file = f"{region_name.lower()}_run_coverage.png"
    plt.savefig(output_file, dpi=600, bbox_inches='tight')
    print(f"Plot saved successfully as '{output_file}'.")
    
    plt.close()  # Close the figure to free memory

print("\nAll regions processed successfully!")