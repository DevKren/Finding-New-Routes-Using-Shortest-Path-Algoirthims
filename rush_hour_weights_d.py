import os
import networkx as nx
import plotly.graph_objects as go
import osmnx as ox
import pandas as pd
import geopandas
import random 
import time 
# Ensure the drive is mounted correctly

df = pd.read_csv('testing_locations_4511.csv')
df.columns = df.columns.str.strip()

def add_road_type_weights(hour):
    # More detailed time-dependent adjustments
    if 7 <= hour < 8:  # Early rush hour
        return 3.0
    elif 8 <= hour < 9:  # Peak rush hour
        return 5.0
    elif 16 <= hour < 17:  # Pre-peak afternoon
        return 3.5
    elif 17 <= hour < 18:  # Peak afternoon
        return 5.0
    elif 18 <= hour < 19:  # Post-peak afternoon
        return 3.0
    else:
        return 1.5
def adjust_weights_by_road_type(roadgraph, hour):
    road_congestion_factor = {
        'motorway': 1.5,
        'trunk': 1.3,
        'primary': 1.2,
        'secondary': 1.1,
        'tertiary': 1.05,
        'unclassified': 1.0,
        'residential': 0.9,
    }
    rush_hour_factor = add_road_type_weights(hour)
    for u, v, d in roadgraph.edges(data=True):
        road_type = d.get('highway', 'unclassified')
        congestion_level = road_congestion_factor.get(road_type, 1.0) * rush_hour_factor
        d['traffic_weight'] = congestion_level


def simulate_traffic_events(roadgraph, probability_of_jam=0.05, impact_factor=3.0):
    for u, v, d in roadgraph.edges(data=True):
        if random.random() < probability_of_jam:
            d['traffic_weight'] *= impact_factor





def generate_path(origin_point, target_point, perimeter, weight='traffic_weight'): 
    start_time = time.time() 
    ox.config(log_console=True, use_cache=True)
    north = max(origin_point[0], target_point[0]) + perimeter
    south = min(origin_point[0], target_point[0]) - perimeter
    east = max(origin_point[1], target_point[1]) + perimeter
    west = min(origin_point[1], target_point[1]) - perimeter
    mode = 'drive'
    roadgraph = ox.graph_from_bbox(north, south, east, west, network_type=mode, simplify=True)
    
    # Add road type weights to edges
    hour = 17 # 5:00 PM
    print(f"Current hour: {hour}")
    for u, v, d in roadgraph.edges(data=True):
        d['weight'] = d.get(weight, 1.0) * add_road_type_weights(hour)
    
    origin_node = ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0])
    target_node = ox.nearest_nodes(roadgraph, target_point[1], target_point[0])
    route = nx.shortest_path(roadgraph, origin_node, target_node, weight='traffic_weight', method='dijkstra')

    long = [roadgraph.nodes[n]['x'] for n in route]
    lat = [roadgraph.nodes[n]['y'] for n in route]
    
    # Calculate total distance in meters
    route_gdf = ox.routing.route_to_gdf(roadgraph, route)
    total_distance_m = route_gdf['length'].sum()

    # Clean and process speed data
    def clean_speed(speed):
        if isinstance(speed, str):
            if 'mph' in speed:
                return float(speed.split(' ')[0])  # Assuming format is 'XX mph'
            elif 'kph' in speed:
                return float(speed.split(' ')[0]) / 1.60934  # Convert km/h to mph
        return None

    speeds = route_gdf['maxspeed'].apply(clean_speed).dropna()
    if not speeds.empty:
        weighted_speeds = route_gdf[route_gdf['maxspeed'].notnull()]['length'] * speeds
        average_speed_mph = weighted_speeds.sum() / route_gdf[route_gdf['maxspeed'].notnull()]['length'].sum()
    else:
        average_speed_mph = 30  # Fallback speed in mph if no valid speed data is available

    # Convert distance to miles
    total_distance_mi = total_distance_m / 1609.34  # meters to miles
    
    # Calculate travel time in hours
    travel_time_h = total_distance_mi / average_speed_mph
    
    # Convert travel time to minutes
    travel_time_min = travel_time_h * 60
    end_time = time.time()
    execution_time = end_time - start_time
    return long, lat, total_distance_mi, travel_time_min, average_speed_mph, execution_time

# Define function to plot results on a map using Plotly
def plot_map(origin_point, target_points, long, lat, total_distance, total_travel_time, average_speed):
    fig = go.Figure(go.Scattermapbox(
        name="Origin",
        mode="markers",
        lon=[origin_point[1]],
        lat=[origin_point[0]],
        marker={'size': 10, 'color': "red"}
    ))
    for i in range(len(lat)):
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=long[i],
            lat=lat[i],
            marker={'size': 5},
            line=dict(width=3, color='blue')))
    for target_point in target_points:
        fig.add_trace(go.Scattermapbox(
            mode="markers",
            lon=[target_point[1]],
            lat=[target_point[0]],
            marker={'size': 10, 'color': 'green'}))
    
    # Add text annotations for total distance, travel time, and average speed
    fig.add_annotation(
        x=0.05,
        y=0.9,
        text=f"Total Distance: {total_distance:.2f} miles",
        showarrow=False,
        bgcolor="white",
        font=dict(size=12)
    )
    fig.add_annotation(
        x=0.05,
        y=0.85,
        text=f"Total Travel Time: {total_travel_time:.2f} minutes",
        showarrow=False,
        bgcolor="white",
        font=dict(size=12)
    )
    fig.add_annotation(
        x=0.05,
        y=0.8,
        text=f"Average Speed: {average_speed:.2f} mph",
        showarrow=False,
        bgcolor="white",
        font=dict(size=12)
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=origin_point[0], lon=origin_point[1]), zoom=10),
        width=800,
        height=600,
        title="Bellman-Ford Path With Rush Hour Type Weights"
    )
    fig.show()
def plot_traffic_conditions(roadgraph):
    edge_weights = nx.get_edge_attributes(roadgraph, 'traffic_weight')
    edge_colors = ox.plot.get_edge_colors_by_attr(roadgraph, 'traffic_weight', num_bins=5, cmap='coolwarm')

# Main execution logic
origin_point = (df.at[0, 'Latitude'], df.at[0, 'Longitude'])
target_points = [(lat, lon) for lat, lon in zip(df['Latitude'], df['Longitude'])]

for target_point in target_points[1:]:
    perimeter = 0.10
    lng, lati, distance, travel_time, speed, execution_time  = generate_path(origin_point, target_point, perimeter, weight='traffic_weight')
    
    # Print the metrics for each route
    print("Route Distance (miles):", distance)
    print("Route Travel Time (minutes):", travel_time)
    print("Route Average Speed (mph):", speed)
    print("Execution Time (seconds):", execution_time)

    # Plot the map for each route
    plot_map(origin_point, [target_point], [lng], [lati], distance, travel_time, speed)
