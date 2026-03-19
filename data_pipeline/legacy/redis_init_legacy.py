import csv
import redis

# Connect to Redis server (ensure Redis is running locally or on a given host/port)
try:
    r = redis.StrictRedis(host='137.204.195.17', port=6379, db=10)
    r.ping()
    r.flushdb()
except redis.ConnectionError as e:
    print(f"Redis connection failed: {e}")

# Path to your CSV file
csv_file_path = '../dataset_with_embeddings_29_09_2025.csv'

def load_csv_to_redis(csv_file_path):
    # Open and read the CSV file
    with open(csv_file_path, mode='r') as file:
        reader = csv.reader(file)

        # Skip header row if it exists
        headers = next(reader)

        for row in reader:
            # Assuming the first column is a unique ID (key)
            key = row[0]

            # Create a dictionary of the other columns (without the first one)
            # The header gives you the column names, excluding the first one (ID)
            data = {headers[i]: row[i] for i in range(1, len(row))}

            # Store the row data as a Redis hash with the key
            r.hmset(key, data)  # `hmset` is deprecated in Redis-py 4.0, but still works.
            print(f"Set {key} -> {data} in Redis.")

if __name__ == "__main__":
    load_csv_to_redis(csv_file_path)

