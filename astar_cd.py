import os
import networkx as nx
import plotly.graph_objects as go
import osmnx as ox
import pandas as pd
import math
import time 
# Load data
df = pd.read_csv("testing_locations_4511.csv")
df.columns = df.columns.str.strip()

origin_point = (df.at[0, 'Latitude'], df.at[0, 'Longitude'])
target_points = [(lat, lon) for lat, lon in zip(df['Latitude'], df['Longitude'])]

# Chebyshev distance heuristic function
def chebyshev_distance(u, v, graph):
    u_x, u_y = graph.nodes[u]['x'], graph.nodes[u]['y']
    v_x, v_y = graph.nodes[v]['x'], graph.nodes[v]['y']
    return max(abs(u_x - v_x), abs(u_y - v_y))

def generate_path(origin_point, target_point, perimeter, mode='drive'):
    start_time = time.time()
    ox.config(log_console=True, use_cache=True)
    north = max(origin_point[0], target_point[0]) + perimeter
    south = min(origin_point[0], target_point[0]) - perimeter
    east = max(origin_point[1], target_point[1]) + perimeter
    west = min(origin_point[1], target_point[1]) - perimeter
    mode = 'drive'
    roadgraph = ox.graph_from_bbox(north, south, east, west, network_type=mode, simplify=True)
    origin_node = ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0])
    target_node = ox.nearest_nodes(roadgraph, target_point[1], target_point[0])
    route = nx.astar_path(roadgraph, origin_node, target_node,heuristic=lambda u, v: chebyshev_distance(u, v, roadgraph))

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
        title="A* Chebyshev Distance Heuristic Visualization"
    )
    fig.show()

# Main execution logic
origin_point = (df.at[0, 'Latitude'], df.at[0, 'Longitude'])
target_points = [(lat, lon) for lat, lon in zip(df['Latitude'], df['Longitude'])]

for target_point in target_points[1:]:
    perimeter = 0.10
    # Generate the road graph
    
    lng, lati, distance, travel_time, speed, execution_time = generate_path(origin_point, target_point, perimeter)
    
    # Print the metrics for each route
    print("Route Distance (miles):", distance)
    print("Route Travel Time (minutes):", travel_time)
    print("Route Average Speed (mph):", speed)
    print("Execution Time (seconds):", execution_time)

    # Plot the map for each route
    plot_map(origin_point, [target_point], [lng], [lati], distance, travel_time, speed)
