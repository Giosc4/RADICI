import redis
import json

# Connect to Redis server
r = redis.StrictRedis(host='localhost', port=6379, db=10)  # Change this to your Redis connection details

# Path to your GeoJSON file
geojson_file_path = '../objects_and_coordinates_29_09_2025.geojson'

def load_geojson(geojson_file_path):
    """
    Load the GeoJSON file and extract the id and coordinates from the features.
    Returns a dictionary with ids as keys and coordinates as values.
    """
    with open(geojson_file_path, 'r') as f:
        geojson_data = json.load(f)

    coordinates_data = {}
    for feature in geojson_data['features']:
        raw_id = feature['properties'].get('id')
        if raw_id:  # Ensure there is an id
            feature_id = raw_id
            coordinates = feature['geometry']['coordinates']
            coordinates_data[feature_id] = coordinates
    
    return coordinates_data

def update_redis_with_coordinates(coordinates_data):
    """
    Update the Redis database by adding the 'coordinates' field to the existing data
    where the 'id' matches the key in the Redis DB, and adding an empty field if the id doesn't match.
    """
    for key in r.scan_iter():  # Iterate through all keys in Redis
        # Check if this key exists in the coordinates_data
        feature_id = key.decode('utf-8')  # Redis keys are bytes, so decode to string
        coordinates = coordinates_data.get(feature_id, None)  # Default to None if no coordinates exist
        
        # If coordinates exist in the GeoJSON, update with those coordinates
        if coordinates is not None:
            r.hset(feature_id, 'coordinates', json.dumps(coordinates))
            print(f"Updated {feature_id} with coordinates {coordinates}")
        else:
            # If no coordinates exist for this ID, set an empty or default value
            r.hset(feature_id, 'coordinates', json.dumps([]))  # Use [] or 'null' or any placeholder
            print(f"Added empty coordinates to {feature_id}.")

def main():
    # Load GeoJSON data (id and coordinates)
    coordinates_data = load_geojson(geojson_file_path)
    
    # Update Redis with the coordinates for matching IDs and empty coordinates for missing ones
    update_redis_with_coordinates(coordinates_data)

if __name__ == "__main__":
    main()

