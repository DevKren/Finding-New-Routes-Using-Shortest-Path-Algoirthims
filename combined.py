import networkx as nx
import osmnx as ox
import pandas as pd
from datetime import datetime

# Load data
df = pd.read_csv('testing_locations_4511.csv')
df.columns = df.columns.str.strip()

# Configuring OSMNX
ox.config(log_console=True, use_cache=True)

def make_chebyshev_distance(graph):
    def chebyshev_distance(u, v):
        u_x, u_y = graph.nodes[u]['x'], graph.nodes[u]['y']
        v_x, v_y = graph.nodes[v]['x'], graph.nodes[v]['y']
        return max(abs(u_x - v_x), abs(u_y - v_y))
    return chebyshev_distance

def add_road_type_weights(roadgraph):
    road_type_weights = {
        'motorway': 1.0, 'trunk': 1.2, 'primary': 1.5, 'secondary': 1.8,
        'tertiary': 2.0, 'unclassified': 2.5, 'residential': 3.0, 'other': 4.0
    }
    for u, v, d in roadgraph.edges(data=True):
        road_types = d.get('highway', 'other')
        weight = min(road_type_weights.get(rt, 4.0) for rt in road_types) if isinstance(road_types, list) else road_type_weights.get(road_types, 4.0)
        d['road_weight'] = weight  # Assign custom road weight
        d['traffic_weight'] = weight  # Initialize traffic weight

def apply_traffic_factor(roadgraph, hour):
    factor = 1.8 if 7 <= hour < 9 or 16 <= hour < 19 else 1.0
    for _, _, d in roadgraph.edges(data=True):
        d['traffic_weight'] = d['road_weight'] * factor  # Adjust traffic weight based on road weight and traffic factor

def clean_speed(speed):
    # Default speed if speed data is missing or cannot be processed
    default_speed_mph = 30  
    if isinstance(speed, str):
        try:
            speed_value = float(speed.split(' ')[0])
            if 'kph' in speed:
                return speed_value / 1.60934  # Convert from km/h to mph
            return speed_value
        except ValueError:
            return default_speed_mph
    return default_speed_mph

def generate_path(origin_point, target_point, perimeter, algorithm, weight):
    # Create the bounding box and load the road graph
    north = max(origin_point[0], target_point[0]) + perimeter
    south = min(origin_point[0], target_point[0]) - perimeter
    east = max(origin_point[1], target_point[1]) + perimeter
    west = min(origin_point[1], target_point[1]) - perimeter
    roadgraph = ox.graph_from_bbox(north, south, east, west, network_type='drive', simplify=True)
    add_road_type_weights(roadgraph)
    apply_traffic_factor(roadgraph, datetime.now().hour)
    
    origin_node = ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0])
    target_node = ox.nearest_nodes(roadgraph, target_point[1], target_point[0])

    # Set the heuristic only for A*
    heuristic_func = None
    if algorithm == 'astar':
        heuristic_func = make_chebyshev_distance(roadgraph)

    # Compute the path using the appropriate algorithm and weight
    if algorithm == 'astar':
        route = nx.astar_path(roadgraph, origin_node, target_node, weight=weight, heuristic=heuristic_func)
    else:
        route = getattr(nx, f"{algorithm}_path")(roadgraph, origin_node, target_node, weight=weight)

    # Calculate distance, time, and speed
    distance = sum(ox.utils_graph.get_route_edge_attributes(roadgraph, route, 'length')) / 1609.34  # convert meters to miles
    time_minutes = sum((ox.utils_graph.get_route_edge_attributes(roadgraph, [u, v], 'length')[0] / 1609.34) / clean_speed(roadgraph[u][v][0].get('maxspeed', '30 mph')) for u, v in zip(route[:-1], route[1:])) * 60
    average_speed = distance / (time_minutes / 60) if time_minutes > 0 else 0

    return distance, time_minutes, average_speed


# Example usage and results printing...


# Execution for 5 routes
results = []
origin_point = (df.at[0, 'Latitude'], df.at[0, 'Longitude'])
for i in range(1, 2):  # Assuming there are at least 5 destinations
    target_point = (df.at[i, 'Latitude'], df.at[i, 'Longitude'])
    for alg in ['astar', 'dijkstra', 'bellman_ford']:
        for weight in ['length', 'road_weight', 'traffic_weight']:
            length, time, speed = generate_path(origin_point, target_point, 0.10, alg, weight)
            results.append((alg, weight, 0, i, length, time, speed))

# Print results
for result in results:
    print(f"Algorithm: {result[0]}, Weight: {result[1]}, Origin Index: {result[2]}, Target Index: {result[3]}, Distance (miles): {result[4]:.2f}, Time: {result[5]:.2f} mins, Speed: {result[6]:.2f} mph")
