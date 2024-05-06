import pandas as pd
import random
import networkx as nx
import osmnx as ox
import geopandas as gpd

class RouteOptimizer:
    def __init__(self, data_file):
        self.df = pd.read_csv(data_file)
        self.df.columns = self.df.columns.str.strip()
        ox.config(log_console=True, use_cache=True)
    
    @staticmethod
    def clean_speed(speed):
        if isinstance(speed, str):
            if 'mph' in speed:
                return float(speed.split(' ')[0])  # Assuming format is 'XX mph'
            elif 'kph' in speed:
                return float(speed.split(' ')[0]) / 1.60934  # Convert km/h to mph
        return None

    def generate_path(self, origin_point, target_point, perimeter, weight='length'):
        ox.config(log_console=True, use_cache=True)
        north = max(origin_point[0], target_point[0]) + perimeter
        south = min(origin_point[0], target_point[0]) - perimeter
        east = max(origin_point[1], target_point[1]) + perimeter
        west = min(origin_point[1], target_point[1]) - perimeter
        mode = 'drive'
        roadgraph = ox.graph_from_bbox(north=north, south=south, east=east, west=west, network_type=mode, simplify=True)
        
        # Add road type weights to edges
        self.add_road_type_weights(roadgraph)
        
        origin_node = ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0])
        target_node = ox.nearest_nodes(roadgraph, target_point[1], target_point[0])
        route = nx.shortest_path(roadgraph, origin_node, target_node, weight=weight, method="dijkstra")

        # Calculate total distance in meters
        total_distance_m = sum(roadgraph[u][v][0]['length'] for u, v in zip(route[:-1], route[1:]))

        # Clean and process speed data
        total_travel_time_minutes = 0
        for u, v in zip(route[:-1], route[1:]):
            segment_length = roadgraph[u][v][0].get(weight, roadgraph[u][v][0]['length'])
            print("f Segment Length: {segment_length}")
            speed_limit = roadgraph[u][v][0].get('maxspeed', '30 mph')  # Default to 30 mph if no speed limit is specified
            speed = self.clean_speed(speed_limit)
            if speed:
                segment_time_hours = segment_length / speed / 1609.34  # Convert length to miles and divide by speed
                total_travel_time_minutes += segment_time_hours * 60  # Convert hours to minutes
        
        total_distance_mi = total_distance_m / 1609.34  # Convert meters to miles
        average_speed_mph = total_distance_mi / (total_travel_time_minutes / 60) 
      
        
        return total_distance_mi, total_travel_time_minutes, average_speed_mph

    def generate_graph(self, origin_point, target_point, perimeter, mode='drive'):
        north, south, east, west = self._get_bbox(origin_point, target_point, perimeter)
        roadgraph = ox.graph_from_bbox(north=north, south=south, east=east, west=west, network_type=mode, simplify=True)
        return roadgraph, ox.nearest_nodes(roadgraph, origin_point[1], origin_point[0]), ox.nearest_nodes(roadgraph, target_point[1], target_point[0])

    def _get_bbox(self, origin, target, perimeter):
        return (max(origin[0], target[0]) + perimeter, min(origin[0], target[0]) - perimeter,
                max(origin[1], target[1]) + perimeter, min(origin[1], target[1]) - perimeter)

    def add_custom_weights(self, roadgraph, factor=1.5):
        for u, v, d in roadgraph.edges(data=True):
            base_weight = d.get('type_weight', d['length'])
            congestion_multiplier = random.uniform(1, factor)
            d['congestion_weight'] = base_weight * congestion_multiplier

    @staticmethod
    def chebyshev_distance(u, v, graph):
        u_x, u_y = graph.nodes[u]['x'], graph.nodes[u]['y']
        v_x, v_y = graph.nodes[v]['x'], graph.nodes[v]['y']
        return max(abs(u_x - v_x), abs(u_y - v_y))

    def add_road_type_weights(self, roadgraph):
        road_weight = {
            ('motorway',): 1.0, ('trunk',): 1.2, ('primary',): 1.5,
            ('secondary',): 1.8, ('tertiary',): 2.0, ('unclassified',): 2.5,
            ('residential',): 3.0, 'other': 4.0
        }
        for u, v, d in roadgraph.edges(data=True):
            road_type = d.get('highway', 'unclassified')
            if isinstance(road_type, list):
                road_type = tuple(sorted(road_type))  # Convert list to a sorted tuple
            d['type_weight'] = road_weight.get(road_type, 4.0)

    def add_traffic_weight(self, roadgraph, hour):
        traffic_factor = 1.8 if 7 <= hour < 9 or 16 <= hour < 19 else 1.0
        for u, v, d in roadgraph.edges(data=True):
            if 'type_weight' in d:
                d['type_weight'] *= traffic_factor
            else:
                d['type_weight'] = traffic_factor * 2.5
    def find_path(self, roadgraph, origin_node, target_node, algorithm='astar', weight='length', heuristic=None):
        if algorithm == 'astar':
            
            return nx.astar_path(roadgraph, origin_node, target_node, weight=weight, heuristic=chebyshev_distance if heuristic else None)
        elif algorithm == 'dijkstra':
            return nx.dijkstra_path(roadgraph, origin_node, target_node, weight=weight)
        elif algorithm == 'bellman_ford':
            return nx.bellman_ford_path(roadgraph, origin_node, target_node, weight=weight)
        else:
            raise ValueError("Unsupported algorithm")


    def run_all_routes(self):
        origin_point = (self.df.at[0, 'Latitude'], self.df.at[0, 'Longitude'])
        target_points = [(lat, lon) for lat, lon in zip(self.df['Latitude'], self.df['Longitude']) if (lat, lon) != origin_point]

        algorithms = ['astar', 'dijkstra', 'bellman_ford']  # All algorithms

        # Specify the weight types you want to test
        weight_types = ['length', 'type_weight', 'congestion_weight']

        # Specify different heuristics if needed
        heuristics = [None, lambda u, v: self.chebyshev_distance(u, v, roadgraph)]

        # Define roadgraph outside the loop
        roadgraph = None
        
        # Iterate over target points, algorithms, weight types, and heuristics
        for target_point in target_points:
            roadgraph, origin_node, target_node = self.generate_graph(origin_point, target_point, perimeter=0.10)
            
            for algorithm in algorithms:
                for weight_type in weight_types:
                    for heuristic in heuristics:
                        try:
                            route = self.find_path(roadgraph, origin_node, target_node, algorithm=algorithm, weight=weight_type, heuristic=heuristic)
                            total_distance_mi, total_travel_time_minutes, average_speed_mph = self.generate_path(origin_point, target_point, perimeter=0.10, weight=weight_type)
                            
                            print(f"Algorithm: {algorithm}, Weight: {weight_type}, Heuristic: {heuristic}, Origin: {origin_point}, Destination: {target_point}")
                            print(f"Total Distance: {total_distance_mi:.2f} mi, Total Travel Time: {total_travel_time_minutes:.2f} min, Average Speed: {average_speed_mph:.2f} mph\n")
                        except Exception as e:
                            print(f"Error running {algorithm} with {weight_type} and heuristic {heuristic} from {origin_point} to {target_point}: {str(e)}")

# Usage
optimizer = RouteOptimizer('testing_locations_4511.csv')
optimizer.run_all_routes()

