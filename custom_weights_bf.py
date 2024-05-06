import os
import random
import networkx as nx
import plotly.graph_objects as go
import osmnx as ox
import pandas as pd
import geopandas as gpd



# Ensure the drive is mounted correctly


df = pd.read_csv('testing_locations_4511.csv')
df.columns = df.columns.str.strip()


## Custom Weigths for Bellman-Ford

def add_custom_weights(roadgraph, factor=1.5):
    for u, v, key, data in roadgraph.edges(data=True, keys=True):
        # Assume the original weight is based on length (this is typical in OSMnx)
        original_weight = data['length']
        # Add a congestion factor that randomly increases the weight
        congestion_multiplier = random.uniform(1, factor)
        data['congestion_weight'] = original_weight * congestion_multiplier
def generate_path(origin_point, target_point, perimeter, weight='congestition_weight'):
    ox.config(log_console=True, use_cache=True)
    north = max(origin_point[0], target_point[0]) + perimeter
    south = min(origin_point[0], target_point[0]) - perimeter
    east = max(origin_point[1], target_point[1]) + perimeter
    west = min(origin_point[1], target_point[1]) - perimeter
    mode = 'drive'
    roadgraph = ox.graph_from_bbox(north, south, east, west, network_type=mode,simplify=True, truncate_by_edge=True, clean_periphery=True)

    # Add custom weights
    add_custom_weights(roadgraph, factor=1.5)  # Adjust factor as needed

    origin_node = ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0])
    target_node = ox.nearest_nodes(roadgraph, target_point[1], target_point[0])
    route = nx.shortest_path(roadgraph, origin_node, target_node, weight=weight, method='bellman-ford')
    long = [roadgraph.nodes[n]['x'] for n in route]
    lat = [roadgraph.nodes[n]['y'] for n in route]
    return long, lat, roadgraph, origin_node, target_node

# Main execution logic
origin_point = (df.at[0, 'Latitude'], df.at[0, 'Longitude'])
target_points = [(lat, lon) for lat, lon in zip(df['Latitude'], df['Longitude'])]
perimeter = 0.01

def plot_map(origin_point, target_points, long, lat):
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
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=origin_point[0], lon=origin_point[1]), zoom=10),
        width=800,
        height=600,
        title="Paths Visualization"
    )
    fig.show()
while True:  # Loop indefinitely for continuous runs
    long, lat = [], []  # Clear lists for each run

    #Custom Weights
    for target_point in target_points[1:]:
        lng, lati, roadgraph, origin_node, target_node = generate_path(origin_point, target_point, perimeter, weight='congestion_weight')
        long.append(lng)
        lat.append(lati)
   
    plot_map(origin_point, target_points[1:],long, lat)