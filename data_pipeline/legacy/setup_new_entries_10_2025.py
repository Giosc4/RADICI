import os
import redis
import requests
from io import BytesIO
import torch
from PIL import Image
from torchvision import models, transforms
import numpy as np
from opencage.geocoder import OpenCageGeocode

# Initialize Redis connection (using DB 10)
r = redis.StrictRedis(host='localhost', port=6379, db=10)

# Initialize the OpenCage Geocoder (get your own API key)
OPEN_CAGE_API_KEY = 'd1b80372526b45da92d057b1654759c3'#'your_opencage_api_key'
geocoder = OpenCageGeocode(OPEN_CAGE_API_KEY)

# Load pre-trained model for extracting image embeddings (ResNet50)
model = models.resnet50(pretrained=True)
model.eval()

# Define image transformation pipeline
transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def extract_embeddings(image_path):
    """Extract embeddings from an image."""
    try:
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0)  # Add batch dimension
        with torch.no_grad():
            embeddings = model(image_tensor)
        # Return the flattened vector of embeddings
        return embeddings.flatten().numpy()
    except Exception as e:
        print(f"Error extracting embeddings from {image_path}: {e}")
        return None

def get_coordinates_from_place(place):
    """Get coordinates from a place name using OpenCage Geocoder."""
    try:
        result = geocoder.geocode(place)
        if result:
            lat, lng = result[0]['geometry']['lat'], result[0]['geometry']['lng']
            return [lat, lng]
        else:
            print(f"Could not find coordinates for place: {place}")
            return None
    except Exception as e:
        print(f"Error fetching coordinates for place {place}: {e}")
        return None

def process_entry(redis_key, entry):
    """Process each entry to update missing embeddings and coordinates."""
    # Extract existing fields
    image_path = entry.get('img_path')
    place = entry.get('place')
    embeddings = entry.get('embeddings')
    coordinates = entry.get('coordinates')

    # Check if embeddings are missing and extract if the image exists
    if not embeddings and image_path and os.path.exists(image_path):
        print(f"Extracting embeddings for image {entry['id']}...")
        embeddings = extract_embeddings(image_path)
        if embeddings is not None:
            # Save embeddings to Redis
            r.hset(redis_key, 'embeddings', embeddings.tobytes())
            print(f"Embeddings for {entry['id']} saved in Redis.")

    # Check if coordinates are missing
    if not coordinates and place:
        print(f"Fetching coordinates for place '{place}'...")
        coordinates = get_coordinates_from_place(place)
        if coordinates:
            # Save coordinates to Redis
            r.hset(redis_key, 'coordinates', coordinates)
            print(f"Coordinates for {entry['id']} saved in Redis: {coordinates}")

def safe_decode(byte_data):
    try:
        return byte_data.decode('utf-8')
    except UnicodeDecodeError:
        # Handle the error: You could skip or return a fallback value
        return f"<non-utf8: {byte_data}>"


def process_all_entries():
    """Process all entries in Redis DB 10."""
    print("Processing all entries")

    # Iterate over all keys in Redis DB 10
    for redis_key in r.scan_iter():
        # Get the hash data for each entry
        entry = r.hgetall(redis_key)    
        decoded_entry = {}
        for k, v in entry.items():
            try:
                # Decode key
                decoded_k = k.decode()

            except UnicodeDecodeError:
                print(f"Error decoding key: {k}")
                decoded_k = "<invalid_key>"

            try:
                # Decode value if it's bytes
                decoded_v = v.decode() if isinstance(v, bytes) else v
            except UnicodeDecodeError:
                print(f"Error decoding value: {v}")
                decoded_v = "<invalid_value>"
            
            # Store the decoded key-value pair in the entry dictionary
            decoded_entry[decoded_k] = decoded_v

        # Process the entry
        process_entry(redis_key, decoded_entry)


        # Decode byte data and convert to string if necessary
        #entry = {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in entry.items()}
        
        # Process the entry
        #process_entry(redis_key, entry)

if __name__ == "__main__":
    process_all_entries()
