import pandas as pd
import googlemaps
import time

# Load the CSV files
df_destinations = pd.read_csv("testing_locations_4511.csv")
df_destinations.columns = df_destinations.columns.str.strip()
df_bellman = pd.read_csv("4511 Final Project Results - Sheet1.csv")
df_bellman.columns = df_bellman.columns.str.strip()

# Clean the 'Total Time' column
df_bellman['Total Time'] = df_bellman['Unnamed: 3'].str.replace(' Minutes', '').str.strip()
df_bellman['Total Time'] = pd.to_numeric(df_bellman['Total Time'], errors='coerce')

# Initialize Google Maps Client
api_key ='AIzaSyAeqW-_p2BzQfuDEsLdnYuOT2w9WkZeURk'  # Replace with your actual API key
gmaps = googlemaps.Client(key=api_key)
origin = '1116 5th St SE, Minneapolis, MN 55414'
baseline_time = 10.0

# Function to fetch trip time from Google Maps
def run_route_google(origin, destination, api_key):
    start_time = time.time()
    try:
        directions_result = gmaps.directions(origin, destination, mode="driving")
        request_time = time.time() - start_time
        if directions_result:
            trip_time = directions_result[0]['legs'][0]['duration']['text']
            trip_time_minutes = float(trip_time.split()[0])
            print(f"Trip Time: {trip_time}, Request Time: {request_time:.2f} seconds")
            return trip_time_minutes, request_time
        else:
            print("No route found.")
            return None, request_time
    except Exception as e:
        print("Error during API request:", e)
        return None, request_time

# Loop through each route
for index, row in df_bellman.iterrows():
    if index < len(df_destinations):
        lat = df_destinations.loc[index, 'Latitude']
        lon = df_destinations.loc[index, 'Longitude']
        destination = f"{lat},{lon}"
        print(f"Calculating route from {origin} to {destination}")

        google_trip_time, google_request_time = run_route_google(origin, destination, api_key)

        if google_trip_time is not None and google_request_time is not None:
            efficiency_score = max(0, 100 * (1 - (google_request_time / baseline_time)))
            expected_trip_time = row['Total Time']
            if pd.notna(expected_trip_time):
                accuracy = 100 - abs((expected_trip_time - google_trip_time) / expected_trip_time * 100)
                print(f"Efficiency Score: {efficiency_score}, Accuracy: {accuracy}%")
            else:
                print("Missing data for accuracy calculation.")
        else:
            print("Could not calculate efficiency or accuracy.")
    else:
        print("Destination index out of range.")
